# 生态缸造景设计 · 作品证书生成器

生态缸造景设计会议系统的一个子系统。一场方案会议开完，系统把会议数据和 AI 纪要渲染成一张 Markdown 作品证书，落盘归档，再转成 HTML 给前台预览。本仓库只保留证书生成器本身，路径已从上游的 `backend/` 提到仓库根。

## 目录

    certificate/__init__.py           空文件，让 certificate 成为一个包
    certificate/generator.py          CertificateGenerator：Markdown 渲染 + 落盘 + HTML 预览
    tests/test_certificate_smoke.py   现有冒烟测试，只覆盖「四个方法都能跑、都能给出非空字符串」

## 对外接口（方法名与参数顺序不要动）

上游路由与批量导出脚本按下面这些签名调用，动一个就要连带改调用方：

- `CertificateGenerator(template_dir="templates")`：`template_dir` 目前没被用到，保留。
- `generate_markdown_certificate(meeting_data, summary_data, designer_name, client_name) -> str`：正式证书。`meeting_data` 认 `id`、`title` 两个键；`summary_data` 认 `landscape_theme`、`plant_combinations`、`construction_steps`、`maintenance_guide`、`full_summary` 五个键。
- `generate_simple_certificate(project_name, designer_name, client_name, theme) -> str`：简易证书，手上没有纪要数据时用。
- `save_certificate(markdown_content, output_dir="certificates", filename=None) -> str`：返回实际写入的路径。
- `generate_html_preview(markdown_content) -> str`：返回完整 HTML 文档字符串，不落盘。

## 证书生成契约

下面每一条都是这个模块对外承诺的行为。**实现与本节不一致时，以本节为准。**

### 1. 证书编号与签发日期

正式证书的编号形如 `AQ-<YYYYMMDD>-<会议号>`，会议号取 `meeting_data["id"]`，**零填充到 3 位**：`7` 出 `007`，`42` 出 `042`。`id` 缺失、为空、或者不是纯数字时统一落 `000`。

简易证书的编号只有 `AQ-<YYYYMMDD>` 两段，没有会议号那一段。这个差异是既有的，保留。

编号里的日期段与正文 `**签发日期**` 那一行的 `YYYY年MM月DD日` 必须来自**同一个时间点**。跨零点时不许出现编号是 31 号、签发日期是 1 号这种组合。`generate_simple_certificate` 同理。

时间必须可替换：测试要能把「当前时间」钉死或者按次推进，所以实现要留出一个取时间的入口（顶掉模块里的 `datetime` 也算），不许靠 sleep 去等跨零点。同一个「当前时间」下、同样的入参调用两次，产出必须**逐字节相同**——编号里不许掺随机后缀或调用计数。

### 2. Markdown 结构完整性

正式证书的项目信息表格是 4 行 2 列。入参值（`meeting_data["title"]`、`designer_name`、`client_name`）落到单元格里不得撑破表格：

- 值里的 `|` 必须转义成 `\|`，否则一行会被切成三列；
- 值里的换行、回车、制表符必须压成单个空格，否则第二行起整个表格散架；
- 压完之后表格块仍然是 **6 行**（表头、分隔行、4 个数据行）。

`plant_combinations` 渲染成 `-~-BT~ 开头的无序列表，`construction_steps` 渲染成 `1.` 开头的有序列表、编号连续。列表项里的换行同样压成单个空格——一项就是一行，不许因为一个换行凭空多出一项或者多出半行。

既有兜底保留：

- `plant_combinations` 为空或缺失 → `-~-BT~ 待补充`；`construction_steps` 为空或缺失 → `1. 待补充`；
- `summary_data` 缺 `landscape_theme` / `maintenance_guide` / `full_summary` → 依次落 `自然森林风格造景` / `详见维护手册` / `详见完整会议记录`；
- 表格里 `设计风格` 写死 `ADA自然风格`，页脚写死 `© 2024 AquaScape Design Studio`，两处都不动。

设计主题、维护指南、纪要摘要这三段是自由段落，允许保留换行，不在压行范围内。

### 3. 落盘语义

`save_certificate` 返回实际写入的路径，文件内容与入参 `markdown_content` 逐字节一致、UTF-8 编码。`output_dir` 不存在时自动创建（既有行为，保留）。

不带 `filename` 时默认名是 `certificate_<YYYYMMDD>_<HHMMSS>.md`。**同一秒内连续保存两张证书，两张都必须在，不许后一张盖掉前一张。** 怎么避免撞名有几种做法、结论不同，需要选：(a) 撞名时追加 `_1`、`_2` 序号；(b) 默认名里带上毫秒或微秒；(c) 直接拒绝、抛异常让调用方自己给名字。选定一种，把选择与理由写在本条下面，并让实现与之一致。

> 选定方案：选 (a) 撞名时追加 `_1`、`_2` 序号。理由：契约要求时间可替换，测试里时钟会被钉死，(b) 的微秒在冻结时钟下照样撞名；(a) 不依赖时钟精度，未撞名时文件名仍是契约规定的 `certificate_<YYYYMMDD>_<HHMMSS>.md`，批量导出脚本也无需像 (c) 那样新增异常处理。

`filename` 由调用方给出时不得逃出 `output_dir`：含 `..` 路径段、含路径分隔符、或者是绝对路径，一律抛 `ValueError` 并附中文说明，不许悄悄写到别处，也不许悄悄改个名字混过去。**这一条是强制的，不是取舍点。**

写入不得在最终路径上留下半截文件：中途失败（磁盘满、权限被撤）时，最终路径要么不存在，要么内容是完整的。

### 4. HTML 预览

`generate_html_preview` 返回完整 HTML 文档：`<!DOCTYPE html>` 开头，`<html lang="zh-CN">`，`<meta charset="UTF-8">`，`<title>生态缸造景设计作品证书</title>`，渲染结果落在 `<div class="certificate">` 里，内联 CSS 保持原样。extensions 仍是 `['tables', 'fenced_code']`，Markdown 表格要真渲染成 `<table>`，围栏代码块要真渲染成 `<pre><code>`。

证书正文来自会议数据和客户留言，属**不可信输入**，原始 HTML 不得直通：正文里出现 `<script>alert(1)</script>` 时，预览页面上不得出现可执行的 `<script>` 节点或 `<img ... onerror=...>` 一类节点，用户看到的应该是字面文本。`markdown` 库的 `safe_mode` 早已废弃，指望不上。

两条路都算符合契约：(a) 渲染前把原文里的 HTML 特殊字符转义掉；(b) 先照常渲染，再对产出的 HTML 做标签白名单清洗。选定一种，把选择与理由写在本条下面，并让实现与之一致。

> 选定方案：选 (a) 渲染前用标准库 `html.escape` 把原文里的 HTML 特殊字符转义掉。理由：标准库即可解决，不引入 bleach 一类清洗库；Markdown 结构语法（`#`、`|`、围栏代码块）不含 `<>&`，转义后表格与代码块照常渲染；(b) 要先渲染再解析 HTML 做标签白名单，复杂且容易漏。

## 运行与测试

依赖版本见 `requirements-task.txt`。运行环境使用预装好的共享虚拟环境，不要现场安装：

    ~/venvs/gsb-aqua/bin/python -m pytest tests/ -q

测试不得联网，不得依赖 `.env` 或真实环境变量，`save_certificate` 的 `output_dir` 只能用 `tmp_path` 下的子目录，不许在仓库根留下 `certificates/`。

"""契约测试：逐条钉死 README「证书生成契约」的四个小节。

约定：
- 时间一律通过 certificate.generator._now 钉死或按次推进，不 sleep、不等跨零点；
- 落盘一律在 tmp_path 下进行，不碰仓库工作目录；
- 不联网、不读 .env、不依赖真实环境变量。
"""
import builtins
import os
import re
from datetime import datetime

import markdown as md
import pytest

import certificate.generator as gen
from certificate.generator import CertificateGenerator

FROZEN = datetime(2024, 12, 31, 23, 59, 59)

MEETING = {"id": 7, "title": "60cm 生态缸方案"}
SUMMARY = {
    "landscape_theme": "沉木莫斯森林景",
    "plant_combinations": ["矮珍珠", "莫斯"],
    "construction_steps": ["铺底层泥", "摆石组", "注水"],
    "maintenance_guide": "每周换水三分之一",
    "full_summary": "客户确认了方案。",
}

MISSING = object()


@pytest.fixture
def frozen_now(monkeypatch):
    """把模块的取时间入口钉死在 2024-12-31 23:59:59。"""
    monkeypatch.setattr(gen, "_now", lambda: FROZEN)
    return FROZEN


def make_cert(meeting=None, summary=None, designer="张造景", client="李先生"):
    return CertificateGenerator().generate_markdown_certificate(
        MEETING if meeting is None else meeting,
        SUMMARY if summary is None else summary,
        designer,
        client,
    )


def table_block(text):
    """取出项目信息表格块：连续的、以 | 开头的行。"""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| 项目 "))
    block = []
    for line in lines[start:]:
        if line.startswith("|"):
            block.append(line)
        else:
            break
    return block


class TestContract1编号与签发日期:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (7, "007"),
            (42, "042"),
            ("9", "009"),
            (123, "123"),
            (None, "000"),
            ("", "000"),
            ("abc", "000"),
            ("12a", "000"),
            (MISSING, "000"),
        ],
    )
    def test_meeting_id_zero_padded_to_3_digits(self, frozen_now, raw, expected):
        meeting = {"title": "测试缸"}
        if raw is not MISSING:
            meeting["id"] = raw
        text = make_cert(meeting=meeting)
        assert f"**证书编号**: AQ-20241231-{expected}" in text

    def test_id_date_and_issue_date_come_from_same_moment(self, frozen_now):
        text = make_cert()
        assert "**证书编号**: AQ-20241231-007" in text
        assert "**签发日期**: 2024年12月31日" in text

    def test_single_moment_even_when_clock_crosses_midnight(self, monkeypatch):
        """时钟按次推进、正好跨过零点：编号日期与签发日期仍须来自同一个时间点。"""
        ticks = iter(
            [
                datetime(2024, 12, 31, 23, 59, 59),
                datetime(2025, 1, 1, 0, 0, 0),
                datetime(2025, 1, 1, 0, 0, 1),
            ]
        )
        monkeypatch.setattr(gen, "_now", lambda: next(ticks))
        text = make_cert()
        id_date = re.search(r"\*\*证书编号\*\*: AQ-(\d{8})-", text).group(1)
        issue = re.search(r"\*\*签发日期\*\*: (\d{4})年(\d{2})月(\d{2})日", text)
        assert id_date == "".join(issue.groups())

    def test_same_inputs_same_moment_byte_identical(self, frozen_now):
        first = make_cert()
        second = make_cert()
        assert first == second
        assert first.encode("utf-8") == second.encode("utf-8")

    def test_simple_certificate_id_has_no_meeting_segment(self, frozen_now):
        text = CertificateGenerator().generate_simple_certificate(
            "60cm 生态缸", "张造景", "李先生", "森林风"
        )
        assert "**证书编号**: AQ-20241231\n" in text
        assert not re.search(r"AQ-\d{8}-", text)
        assert "**签发日期**: 2024年12月31日" in text


class TestContract2Markdown结构完整性:
    def test_pipe_in_values_is_escaped_and_table_keeps_2_columns(self, frozen_now):
        """负例：把单元格转义去掉、改回直接拼原始字符串时，本条必须变红。"""
        text = make_cert(
            meeting={"id": 1, "title": "A|B 方案"},
            designer="张|造景",
            client="李|先生",
        )
        block = table_block(text)
        assert len(block) == 6
        assert "A\\|B 方案" in block[2]
        assert "张\\|造景" in block[3]
        assert "李\\|先生" in block[4]
        # 表格块渲染后仍是 4 行 × 2 列，竖线不把单元格切成三列
        html = md.markdown("\n".join(block), extensions=["tables"])
        assert html.count("<td>") == 8

    def test_newline_tab_in_values_collapsed_and_table_stays_6_lines(self, frozen_now):
        text = make_cert(
            meeting={"id": 1, "title": "生态缸\n方案"},
            designer="张\r\n造景",
            client="李\t先生",
        )
        block = table_block(text)
        assert len(block) == 6
        assert block[2] == "| 项目名称 | 生态缸 方案 |"
        assert block[3] == "| 造景师 | 张 造景 |"
        assert block[4] == "| 客户 | 李 先生 |"
        assert block[5] == "| 设计风格 | ADA自然风格 |"

    def test_list_items_are_one_line_each_and_steps_numbered_continuously(self, frozen_now):
        summary = dict(
            SUMMARY,
            plant_combinations=["矮珍珠\n迷你矮", "莫\t斯"],
            construction_steps=["铺泥\n压实", "摆石", "注水"],
        )
        text = make_cert(summary=summary)
        lines = text.splitlines()
        dash_items = [line for line in lines if line.startswith("- ")]
        assert dash_items == ["- 矮珍珠 迷你矮", "- 莫 斯"]
        ordered = [line for line in lines if re.match(r"^\d+\. ", line)]
        assert ordered == ["1. 铺泥 压实", "2. 摆石", "3. 注水"]

    def test_fallbacks_and_fixed_texts(self, frozen_now):
        text = make_cert(summary={})
        assert "\n- 待补充\n" in text
        assert "\n1. 待补充\n" in text
        assert "自然森林风格造景" in text
        assert "详见维护手册" in text
        assert "详见完整会议记录" in text
        assert "| 设计风格 | ADA自然风格 |" in text
        assert "© 2024 AquaScape Design Studio" in text

        empty_lists = make_cert(summary={"plant_combinations": [], "construction_steps": []})
        assert "\n- 待补充\n" in empty_lists
        assert "\n1. 待补充\n" in empty_lists


class TestContract3落盘语义:
    def test_roundtrip_byte_identical_utf8_and_output_dir_autocreated(self, tmp_path, frozen_now):
        out = tmp_path / "深层" / "嵌套目录"
        content = "# 证书\n中文内容：生态缸 © 2024\n"
        path = CertificateGenerator().save_certificate(
            content, output_dir=str(out), filename="c.md"
        )
        assert path == str(out / "c.md")
        with builtins.open(path, "rb") as f:
            assert f.read() == content.encode("utf-8")

    def test_same_second_saves_never_overwrite(self, tmp_path, frozen_now):
        generator = CertificateGenerator()
        out = str(tmp_path / "certs")
        p1 = generator.save_certificate("第一张", output_dir=out)
        p2 = generator.save_certificate("第二张", output_dir=out)
        p3 = generator.save_certificate("第三张", output_dir=out)

        assert len({p1, p2, p3}) == 3
        assert p1.endswith("certificate_20241231_235959.md")
        assert p2.endswith("certificate_20241231_235959_1.md")
        assert p3.endswith("certificate_20241231_235959_2.md")
        for path, body in [(p1, "第一张"), (p2, "第二张"), (p3, "第三张")]:
            with builtins.open(path, encoding="utf-8") as f:
                assert f.read() == body
        assert len(os.listdir(out)) == 3

    @pytest.mark.parametrize(
        "bad", ["../evil.md", "..", "sub/evil.md", "a\\b.md", "/tmp/evil.md"]
    )
    def test_filename_cannot_escape_output_dir(self, tmp_path, bad):
        out = tmp_path / "certs"
        with pytest.raises(ValueError) as exc_info:
            CertificateGenerator().save_certificate(
                "x", output_dir=str(out), filename=bad
            )
        # 必须附中文说明
        assert re.search(r"[一-鿿]", str(exc_info.value))
        assert not (tmp_path / "evil.md").exists()
        assert not (out / "evil.md").exists()

    def test_failed_write_leaves_no_partial_file(self, tmp_path, monkeypatch):
        """写到一半抛 OSError：最终路径要么不存在，要么内容完整。负例：直接写最终路径时本条变红。"""
        out = tmp_path / "certs"

        def fake_open(path, mode="r", *args, **kwargs):
            if "w" not in mode:
                return builtins.open(path, mode, *args, **kwargs)

            class HalfWriter:
                def __enter__(self):
                    self._real = builtins.open(path, mode, *args, **kwargs)
                    return self

                def __exit__(self, *exc):
                    self._real.close()
                    return False

                def write(self, data):
                    self._real.write(data[: len(data) // 2])  # 只写一半就故障
                    raise OSError("模拟磁盘写失败")

            return HalfWriter()

        # 只顶掉 certificate.generator 模块里的 open，不碰 builtins.open
        monkeypatch.setattr(gen, "open", fake_open, raising=False)
        with pytest.raises(OSError):
            CertificateGenerator().save_certificate(
                "完整内容" * 100, output_dir=str(out), filename="final.md"
            )
        assert not (out / "final.md").exists()
        assert list(out.iterdir()) == []  # 也不许留下半截临时文件


class TestContract4Html预览:
    def test_document_skeleton_css_and_extensions(self):
        md_text = "# 标题\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```\ncode\n```\n"
        html = CertificateGenerator().generate_html_preview(md_text)
        assert html.startswith("<!DOCTYPE html>")
        assert '<html lang="zh-CN">' in html
        assert '<meta charset="UTF-8">' in html
        assert "<title>生态缸造景设计作品证书</title>" in html
        assert '<div class="certificate">' in html
        assert "font-family" in html  # 内联 CSS 保持原样
        assert "<table>" in html
        assert "<td>1</td>" in html and "<td>2</td>" in html
        assert "<pre><code>" in html

    def test_raw_html_is_escaped_not_passthrough(self):
        """负例：把渲染前的转义/清洗去掉时，本条必须变红。"""
        payload = (
            "# 证书\n\n<script>alert(1)</script>\n\n"
            '<img src=x onerror="alert(1)">\n'
        )
        html = CertificateGenerator().generate_html_preview(payload)
        # 不得出现可执行的 script / img 节点
        assert "<script" not in html.lower()
        assert "<img" not in html.lower()
        # 用户看到的应是字面文本
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
        assert "&lt;img src=x" in html

"""钉死 README「证书生成契约」的测试。

时间一律通过 monkeypatch 顶掉 certificate.generator 模块里的 datetime
来钉死或按次推进，不 sleep、不依赖真实时钟、不联网、不读环境变量。
save_certificate 的 output_dir 一律落在 tmp_path 下。
"""
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import certificate.generator as gen
from certificate.generator import CertificateGenerator

FROZEN = datetime(2024, 12, 31, 23, 59, 59)

MEETING = {"id": 7, "title": "60cm 生态缸方案"}
SUMMARY = {
    "landscape_theme": "自然森林风格",
    "plant_combinations": ["矮珍珠", "莫斯"],
    "construction_steps": ["铺底层泥", "摆石组"],
    "maintenance_guide": "每周换水三分之一",
    "full_summary": "客户确认了方案。",
}


def _freeze(monkeypatch, moment):
    class FrozenDatetime:
        @classmethod
        def now(cls):
            return moment

    monkeypatch.setattr(gen, "datetime", FrozenDatetime)


def _ticking(start, step):
    """每调用一次 now() 就推进 step，用来抓「分两次取时间」的实现。"""

    class TickingDatetime:
        calls = 0

        @classmethod
        def now(cls):
            moment = start + step * cls.calls
            cls.calls += 1
            return moment

    return TickingDatetime


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    _freeze(monkeypatch, FROZEN)


def _table_lines(text):
    return [line for line in text.splitlines() if line.startswith("|")]


# ---------- 契约 1：证书编号与签发日期 ----------

class TestCertificateIdAndDate:
    def test_meeting_id_zero_padded_to_three_digits(self):
        g = CertificateGenerator()
        text = g.generate_markdown_certificate({"id": 7, "title": "t"}, SUMMARY, "张", "李")
        assert "**证书编号**: AQ-20241231-007" in text
        text = g.generate_markdown_certificate({"id": 42, "title": "t"}, SUMMARY, "张", "李")
        assert "**证书编号**: AQ-20241231-042" in text

    def test_invalid_meeting_id_falls_back_to_000(self):
        g = CertificateGenerator()
        for bad in (None, "", "abc", "12a", "-1"):
            text = g.generate_markdown_certificate({"id": bad, "title": "t"}, SUMMARY, "张", "李")
            assert "**证书编号**: AQ-20241231-000" in text, f"id={bad!r}"
        text = g.generate_markdown_certificate({"title": "t"}, SUMMARY, "张", "李")
        assert "**证书编号**: AQ-20241231-000" in text

    def test_id_and_issue_date_come_from_one_instant(self, monkeypatch):
        # now() 每被调一次推进一天：实现若分两次取时间，编号与签发日期必跨零点错位
        monkeypatch.setattr(gen, "datetime", _ticking(datetime(2024, 12, 31, 23, 59, 59), timedelta(days=1)))
        text = CertificateGenerator().generate_markdown_certificate(MEETING, SUMMARY, "张", "李")
        assert "**证书编号**: AQ-20241231-007" in text
        assert "**签发日期**: 2024年12月31日" in text

    def test_same_instant_same_params_byte_identical(self):
        g = CertificateGenerator()
        first = g.generate_markdown_certificate(MEETING, SUMMARY, "张造景", "李先生")
        second = g.generate_markdown_certificate(MEETING, SUMMARY, "张造景", "李先生")
        assert first == second

    def test_simple_certificate_two_segment_id_and_consistent_date(self, monkeypatch):
        monkeypatch.setattr(gen, "datetime", _ticking(datetime(2024, 12, 31, 23, 59, 59), timedelta(days=1)))
        text = CertificateGenerator().generate_simple_certificate("60cm 生态缸", "张造景", "李先生", "森林风")
        id_line = next(line for line in text.splitlines() if line.startswith("**证书编号**"))
        assert id_line == "**证书编号**: AQ-20241231"
        assert "**签发日期**: 2024年12月31日" in text


# ---------- 契约 2：Markdown 结构完整性 ----------

class TestMarkdownStructure:
    def test_pipe_in_table_values_is_escaped(self):
        text = CertificateGenerator().generate_markdown_certificate(
            {"id": 1, "title": "生态缸|水草缸"}, SUMMARY, "张|造景", "李先生"
        )
        assert "生态缸\\|水草缸" in text
        assert "张\\|造景" in text
        table = _table_lines(text)
        assert len(table) == 6
        for line in table:
            cells = re.split(r"(?<!\\)\|", line)[1:-1]
            assert len(cells) == 2, f"表格行被切成 {len(cells)} 列: {line!r}"

    def test_newlines_and_tabs_in_table_values_collapsed(self):
        text = CertificateGenerator().generate_markdown_certificate(
            {"id": 1, "title": "生态缸"}, SUMMARY, "张\n造景\r\n师傅", "李\t先生"
        )
        assert len(_table_lines(text)) == 6
        assert "| 造景师 | 张 造景 师傅 |" in text
        assert "| 客户 | 李 先生 |" in text

    def test_list_items_stay_one_line_each(self):
        summary = dict(
            SUMMARY,
            plant_combinations=["矮珍珠\n迷你榕"],
            construction_steps=["铺泥", "摆石\n造景", "注水"],
        )
        text = CertificateGenerator().generate_markdown_certificate({"id": 1, "title": "t"}, summary, "张", "李")
        plant_items = [line for line in text.splitlines() if line.startswith("- ")]
        assert plant_items == ["- 矮珍珠 迷你榕"]
        step_items = [line for line in text.splitlines() if re.match(r"^\d+\. ", line)]
        assert step_items == ["1. 铺泥", "2. 摆石 造景", "3. 注水"]

    def test_missing_summary_fields_fall_back(self):
        text = CertificateGenerator().generate_markdown_certificate({"id": 3, "title": "t"}, {}, "张", "李")
        assert "- 待补充" in text
        assert "1. 待补充" in text
        assert "自然森林风格造景" in text
        assert "详见维护手册" in text
        assert "详见完整会议记录" in text

    def test_fixed_style_and_footer_kept(self):
        text = CertificateGenerator().generate_markdown_certificate(MEETING, SUMMARY, "张", "李")
        assert "| 设计风格 | ADA自然风格 |" in text
        assert "© 2024 AquaScape Design Studio" in text


# ---------- 契约 3：落盘语义 ----------

class TestSaveCertificate:
    def test_content_written_byte_identical_utf8(self, tmp_path):
        content = "# 证书\n中文内容 © 2024 \\| 转义字符\n"
        path = CertificateGenerator().save_certificate(content, output_dir=str(tmp_path / "certs"))
        assert Path(path).read_bytes() == content.encode("utf-8")

    def test_output_dir_created_and_default_name_format(self, tmp_path):
        out = tmp_path / "a" / "b"
        path = CertificateGenerator().save_certificate("x", output_dir=str(out))
        assert os.path.basename(path) == "certificate_20241231_235959.md"
        assert os.path.isfile(path)

    def test_same_second_saves_do_not_overwrite(self, tmp_path):
        out = tmp_path / "certs"
        g = CertificateGenerator()
        first = g.save_certificate("第一张", output_dir=str(out))
        second = g.save_certificate("第二张", output_dir=str(out))
        assert first != second
        assert len(os.listdir(out)) == 2
        assert Path(first).read_text(encoding="utf-8") == "第一张"
        assert Path(second).read_text(encoding="utf-8") == "第二张"

    def test_filename_traversal_rejected(self, tmp_path):
        out = tmp_path / "certs"
        g = CertificateGenerator()
        for bad in ("../evil.md", "..\\evil.md", "sub/evil.md", "a\\b.md", str(tmp_path / "abs.md")):
            with pytest.raises(ValueError):
                g.save_certificate("x", output_dir=str(out), filename=bad)
        assert not (tmp_path / "evil.md").exists()
        assert not (tmp_path / "abs.md").exists()

    def test_failed_write_leaves_no_partial_file(self, tmp_path, monkeypatch):
        out = tmp_path / "certs"
        real_open = open

        class PartialThenFail:
            def __init__(self, path):
                self._real = real_open(path, "w", encoding="utf-8")

            def write(self, data):
                self._real.write(data[: len(data) // 2])
                self._real.flush()
                raise OSError("模拟写一半失败")

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self._real.close()
                return False

        # 只顶掉 certificate.generator 模块命名空间里的 open，不动 builtins.open
        monkeypatch.setattr(gen, "open", lambda path, *a, **kw: PartialThenFail(path), raising=False)
        with pytest.raises(OSError):
            CertificateGenerator().save_certificate("完整内容" * 100, output_dir=str(out), filename="final.md")
        assert not (out / "final.md").exists()
        assert list(out.iterdir()) == [], "最终路径和临时文件都不许留下半截"


# ---------- 契约 4：HTML 预览 ----------

class TestHtmlPreview:
    def test_document_skeleton(self):
        html = CertificateGenerator().generate_html_preview("# 证书\n")
        assert html.startswith("<!DOCTYPE html>")
        assert '<html lang="zh-CN">' in html
        assert '<meta charset="UTF-8">' in html
        assert "<title>生态缸造景设计作品证书</title>" in html
        assert '<div class="certificate">' in html
        assert "<style>" in html

    def test_table_and_fenced_code_actually_rendered(self):
        md_text = "| A | B |\n|---|---|\n| 1 | 2 |\n\n```\ncode\n```\n"
        html = CertificateGenerator().generate_html_preview(md_text)
        assert "<table>" in html
        assert "<pre><code>" in html

    def test_raw_html_in_content_is_escaped(self):
        md_text = "# 证书\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n"
        html = CertificateGenerator().generate_html_preview(md_text)
        assert "<script>" not in html
        assert "<img" not in html
        assert "&lt;script&gt;" in html
        assert "onerror=alert(1)" in html  # 作为字面文本可见，而不是可执行节点

    def test_markdown_structure_survives_escaping(self):
        html = CertificateGenerator().generate_html_preview("# 标题\n\n**加粗**\n")
        assert "<h1>标题</h1>" in html
        assert "<strong>加粗</strong>" in html

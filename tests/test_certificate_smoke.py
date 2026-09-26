"""现有的冒烟测试。

只保证「四个方法都能跑、都能给出非空字符串、文件能落盘读回来」，
不对 README 里任何一条契约做断言。
"""
import os

from certificate.generator import CertificateGenerator

MEETING = {"id": 7, "title": "60cm 生态缸方案"}
SUMMARY = {
    "landscape_theme": "自然森林风格",
    "plant_combinations": ["矮珍珠", "莫斯"],
    "construction_steps": ["铺底层泥", "摆石组"],
    "maintenance_guide": "每周换水三分之一",
    "full_summary": "客户确认了方案。",
}


def test_markdown_certificate_is_a_non_empty_string():
    text = CertificateGenerator().generate_markdown_certificate(
        MEETING, SUMMARY, "张造景", "李先生"
    )
    assert isinstance(text, str)
    assert text.startswith("# 生态缸造景设计作品证书")
    assert "张造景" in text and "李先生" in text


def test_simple_certificate_mentions_project_and_theme():
    text = CertificateGenerator().generate_simple_certificate(
        "60cm 生态缸", "张造景", "李先生", "森林风"
    )
    assert "60cm 生态缸" in text and "森林风" in text


def test_save_certificate_writes_something_readable(tmp_path):
    out = tmp_path / "certs"
    path = CertificateGenerator().save_certificate("# 证书\n", output_dir=str(out))
    assert os.path.isfile(path)
    with open(path, encoding="utf-8") as f:
        assert f.read() == "# 证书\n"


def test_html_preview_is_a_full_document():
    html = CertificateGenerator().generate_html_preview("# 证书\n")
    assert html.startswith("<!DOCTYPE html>")
    assert '<div class="certificate">' in html
    assert "<h1>证书</h1>" in html

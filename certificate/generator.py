from typing import Dict, Any, Optional
from datetime import datetime
import html
import os
import re
import tempfile


def _now() -> datetime:
    return datetime.now()


def _format_meeting_id(raw_id: Any) -> str:
    if raw_id is None:
        return "000"
    text = str(raw_id).strip()
    if not text.isdigit():
        return "000"
    return text.zfill(3)


def _collapse_inline_whitespace(value: Any) -> str:
    return re.sub(r"[\r\n\t]+", " ", str(value))


def _escape_table_cell(value: Any) -> str:
    return _collapse_inline_whitespace(value).replace("|", "\\|")


def _validate_filename(filename: str) -> None:
    if os.path.isabs(filename):
        raise ValueError(f"filename 不允许使用绝对路径: {filename!r}")
    segments = re.split(r"[/\\]", filename)
    if any(segment == ".." for segment in segments):
        raise ValueError(f"filename 不允许包含 '..' 路径段: {filename!r}")
    if len(segments) > 1:
        raise ValueError(f"filename 不允许包含路径分隔符: {filename!r}")


class CertificateGenerator:
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = template_dir
    
    def generate_markdown_certificate(
        self,
        meeting_data: Dict[str, Any],
        summary_data: Dict[str, Any],
        designer_name: str,
        client_name: str
    ) -> str:
        now = _now()
        certificate_id = f"AQ-{now.strftime('%Y%m%d')}-{_format_meeting_id(meeting_data.get('id'))}"
        
        plant_combinations = summary_data.get("plant_combinations", [])
        construction_steps = summary_data.get("construction_steps", [])
        
        plants_list = "\n".join([f"- {_collapse_inline_whitespace(plant)}" for plant in plant_combinations]) if plant_combinations else "- 待补充"
        steps_list = "\n".join([f"{i+1}. {_collapse_inline_whitespace(step)}" for i, step in enumerate(construction_steps)]) if construction_steps else "1. 待补充"
        
        certificate = f"""# 生态缸造景设计作品证书

**证书编号**: {certificate_id}
**签发日期**: {now.strftime('%Y年%m月%d日')}

---

## 项目信息

| 项目 | 内容 |
|------|------|
| 项目名称 | {_escape_table_cell(meeting_data.get('title', '生态缸造景设计'))} |
| 造景师 | {_escape_table_cell(designer_name)} |
| 客户 | {_escape_table_cell(client_name)} |
| 设计风格 | ADA自然风格 |

---

## 设计主题

{summary_data.get('landscape_theme', '自然森林风格造景')}

---

## 植物组合方案

{plants_list}

---

## 施工步骤

{steps_list}

---

## 维护指南

{summary_data.get('maintenance_guide', '详见维护手册')}

---

## 会议纪要摘要

{summary_data.get('full_summary', '详见完整会议记录')}

---

### 设计师签名: _____________________

### 客户确认签名: _____________________

---

*本证书由生态缸造景设计系统自动生成*
*© 2024 AquaScape Design Studio*
"""
        return certificate
    
    def generate_simple_certificate(
        self,
        project_name: str,
        designer_name: str,
        client_name: str,
        theme: str
    ) -> str:
        now = _now()
        certificate_id = f"AQ-{now.strftime('%Y%m%d')}"
        
        return f"""# 生态缸造景设计作品证书

**证书编号**: {certificate_id}
**签发日期**: {now.strftime('%Y年%m月%d日')}

---

## 项目信息

- **项目名称**: {project_name}
- **造景师**: {designer_name}
- **客户**: {client_name}
- **设计主题**: {theme}

---

*本证书由生态缸造景设计系统自动生成*
*© 2024 AquaScape Design Studio*
"""
    
    def save_certificate(self, markdown_content: str, output_dir: str = "certificates", filename: Optional[str] = None) -> str:
        if filename is not None:
            _validate_filename(filename)

        os.makedirs(output_dir, exist_ok=True)

        if filename is None:
            base = f"certificate_{_now().strftime('%Y%m%d_%H%M%S')}"
            filename = f"{base}.md"
            counter = 1
            while os.path.exists(os.path.join(output_dir, filename)):
                filename = f"{base}_{counter}.md"
                counter += 1

        filepath = os.path.join(output_dir, filename)

        fd, tmp_path = tempfile.mkstemp(dir=output_dir, prefix=".certificate_", suffix=".tmp")
        os.close(fd)
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            os.replace(tmp_path, filepath)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        return filepath
    
    def generate_html_preview(self, markdown_content: str) -> str:
        import markdown as md
        safe_content = html.escape(markdown_content, quote=False)
        html_content = md.markdown(safe_content, extensions=['tables', 'fenced_code'])
        
        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>生态缸造景设计作品证书</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .certificate {{
            background: white;
            padding: 60px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 20px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            width: 30%;
        }}
        .signature {{
            margin-top: 50px;
            display: flex;
            justify-content: space-between;
        }}
        .signature-line {{
            border-top: 1px solid #333;
            width: 200px;
            text-align: center;
            padding-top: 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #7f8c8d;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="certificate">
        {html_content}
    </div>
</body>
</html>"""
        
        return html_template

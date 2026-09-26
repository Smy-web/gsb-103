from typing import Dict, Any, Optional
from datetime import datetime
import os

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
        certificate_id = f"AQ-{datetime.now().strftime('%Y%m%d')}-{meeting_data.get('id', '000')}"
        
        plant_combinations = summary_data.get("plant_combinations", [])
        construction_steps = summary_data.get("construction_steps", [])
        
        plants_list = "\n".join([f"- {plant}" for plant in plant_combinations]) if plant_combinations else "- 待补充"
        steps_list = "\n".join([f"{i+1}. {step}" for i, step in enumerate(construction_steps)]) if construction_steps else "1. 待补充"
        
        certificate = f"""# 生态缸造景设计作品证书

**证书编号**: {certificate_id}
**签发日期**: {datetime.now().strftime('%Y年%m月%d日')}

---

## 项目信息

| 项目 | 内容 |
|------|------|
| 项目名称 | {meeting_data.get('title', '生态缸造景设计')} |
| 造景师 | {designer_name} |
| 客户 | {client_name} |
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
        certificate_id = f"AQ-{datetime.now().strftime('%Y%m%d')}"
        
        return f"""# 生态缸造景设计作品证书

**证书编号**: {certificate_id}
**签发日期**: {datetime.now().strftime('%Y年%m月%d日')}

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
        os.makedirs(output_dir, exist_ok=True)
        
        if filename is None:
            filename = f"certificate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        return filepath
    
    def generate_html_preview(self, markdown_content: str) -> str:
        import markdown as md
        html_content = md.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
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

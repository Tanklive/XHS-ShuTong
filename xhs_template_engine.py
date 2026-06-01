#!/usr/bin/env python3.13
"""
XHS 通用卡片模板引擎 v1.0
支持7页结构 + 配色方案 + 字段定义全参数化
"""
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

TEMPLATES_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path("/tmp/xhs_cards")

# 7页结构定义
PAGE_TYPES = {
    "cover": "P1封面",
    "conclusion": "P2结论", 
    "background": "P3背景",
    "method1": "P4核心方法",
    "method2": "P5实操步骤",
    "pitfall": "P6避坑",
    "summary": "P7总结"
}

# 字段定义
FIELD_SCHEMA = {
    "title": {"max_len": 15, "required": True},
    "content": {"max_len": 100, "required": True},
    "image_prompt": {"required": False},
    "style": {"values": ["dark", "light", "accent"], "default": "dark"},
    "type": {"values": ["data", "step", "warning", "cta"], "required": False},
    "aspect_ratio": {"values": ["3:4", "1:1"], "default": "3:4"},
    "cta_block": {"type": "object", "required": False}
}

def load_color_scheme(scheme_name):
    """加载配色方案"""
    # 这里可以从xhs_templates.json加载
    schemes = {
        "tech_blue": {
            "primary": "#00D4FF",
            "secondary": "#1A1A2E",
            "background": "#0A0A1A",
            "text": "#FFFFFF"
        },
        "ink_wash": {
            "primary": "#C23B22",
            "secondary": "#2C2C2C",
            "background": "#F5F0E8",
            "text": "#1A1A1A"
        }
    }
    return schemes.get(scheme_name, schemes["tech_blue"])

def create_page(page_type, data, scheme, output_path):
    """创建单页卡片"""
    # 1080x1440 (3:4)
    width, height = 1080, 1440
    
    # 创建图片
    img = Image.new('RGB', (width, height), scheme["background"])
    draw = ImageDraw.Draw(img)
    
    # 这里应该调用xhs_cards.py的绘制逻辑
    # 简化版：只是创建占位图
    draw.text((50, 50), f"{PAGE_TYPES[page_type]}", fill=scheme["text"])
    draw.text((50, 100), f"Title: {data.get('title', '')}", fill=scheme["text"])
    draw.text((50, 150), f"Content: {data.get('content', '')[:50]}...", fill=scheme["text"])
    
    # 保存
    img.save(output_path, quality=95)
    return output_path

def generate_7page_card(template_data, scheme_name, output_prefix):
    """生成7页卡片"""
    scheme = load_color_scheme(scheme_name)
    output_files = []
    
    for page_type in PAGE_TYPES.keys():
        if page_type in template_data:
            data = template_data[page_type]
            output_path = f"{output_prefix}_{page_type}.jpg"
            create_page(page_type, data, scheme, output_path)
            output_files.append(output_path)
    
    return output_files

if __name__ == "__main__":
    # 测试
    test_data = {
        "cover": {"title": "AI大模型本地部署", "content": "3步搞定"},
        "conclusion": {"title": "核心结论", "content": "本地部署更安全"},
        "background": {"title": "为什么要做", "content": "隐私保护需求"},
        "method1": {"title": "核心方法", "content": "下载Ollama"},
        "method2": {"title": "实操步骤", "content": "运行模型"},
        "pitfall": {"title": "常见坑", "content": "显存不足"},
        "summary": {"title": "总结", "content": "3步完成"}
    }
    
    files = generate_7page_card(test_data, "tech_blue", "/tmp/test_7page")
    print(f"Generated {len(files)} pages: {files}")

#!/usr/bin/env python3.13
"""
XHS 封面自动合成 — Phase 3
===========================
根据深度领域 + 标题 → Pillow 合成 3:4 封面图 (1080×1440)

用法:
    python3.13 xhs_cover_gen.py --domain "AI" --title "红衣大叔今天又怼人了"
"""

import sys, os, textwrap, math, random
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("pip install Pillow --break-system-packages")
    sys.exit(1)

WIDTH, HEIGHT = 1080, 1440
OUTPUT_PATH = "/tmp/xhs_daily_image.jpg"
MARGIN = 60

# 领域配色
THEME = {
    "哮喘": {
        "bg_top": (215, 240, 235),
        "bg_bot": (245, 250, 248),
        "accent": (15, 130, 110),
        "accent2": (80, 180, 160),
        "label": "🫁 呼吸健康",
    },
    "AI": {
        "bg_top": (225, 235, 255),
        "bg_bot": (248, 250, 255),
        "accent": (40, 65, 190),
        "accent2": (100, 130, 230),
        "label": "🤖 AI 前沿",
    },
    "智能体": {
        "bg_top": (240, 230, 255),
        "bg_bot": (252, 248, 255),
        "accent": (110, 45, 170),
        "accent2": (160, 100, 210),
        "label": "🧠 智能体",
    },
    "安全": {
        "bg_top": (255, 230, 230),
        "bg_bot": (255, 245, 245),
        "accent": (185, 40, 40),
        "accent2": (230, 100, 100),
        "label": "🔒 安全预警",
    },
    "九字真言": {
        "bg_top": (245, 240, 225),
        "bg_bot": (252, 250, 242),
        "accent": (100, 70, 40),
        "accent2": (170, 140, 100),
        "label": "🔮 能量磁场",
    },
    "老黄历": {
        "bg_top": (250, 245, 228),
        "bg_bot": (254, 252, 240),
        "accent": (160, 120, 50),
        "accent2": (200, 170, 90),
        "label": "📅 今日日签",
    },
}

FONT_PATHS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]


def find_font(size: int):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_gradient(draw, w, h, top_color, bot_color):
    """绘制纵向渐变背景"""
    for y in range(h):
        t = y / h
        t = t**0.7  # 非线性，上半部变化慢
        color = lerp_color(top_color, bot_color, t)
        draw.line([(0, y), (w, y)], fill=color)


def generate(domain: str, title: str) -> str:
    t = THEME.get(domain, THEME["老黄历"])
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # ── 渐变背景 ──
    draw_gradient(draw, WIDTH, HEIGHT, t["bg_top"], t["bg_bot"])

    # ── 装饰圆形 ──
    for cx, cy, r, alpha in [
        (WIDTH - 100, 200, 300, 0.06),
        (80, HEIGHT - 300, 250, 0.04),
        (WIDTH // 2, 600, 180, 0.05),
    ]:
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.ellipse([cx - r, cy - r, cx + r, cy + r],
                      fill=(*t["accent2"], int(255 * alpha)))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

    # ── 顶部色块 ──
    bar_h = 140
    bar_img = Image.new("RGBA", (WIDTH, bar_h), (*t["accent"], 255))
    img.paste(bar_img, (0, 0), bar_img)
    draw = ImageDraw.Draw(img)

    label_font = find_font(44)
    label_text = t["label"]
    label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
    label_w = label_bbox[2] - label_bbox[0]
    draw.text(
        ((WIDTH - label_w) // 2, (bar_h - 48) // 2),
        label_text, fill="white", font=label_font,
    )

    # ── 主标题区 ──
    title_font = find_font(76)
    title_lines = textwrap.wrap(title, width=12)
    line_height = int(title_font.size * 1.35)

    # 标题区背景卡片
    card_pad = 80
    title_block_h = len(title_lines) * line_height + card_pad * 2
    title_block_y = bar_h + (HEIGHT - bar_h - title_block_h) // 2 - 40

    # 半透明白色卡片
    card = Image.new("RGBA", (WIDTH - 120, title_block_h), (255, 255, 255, 220))
    img.paste(card, (60, title_block_y), card)
    draw = ImageDraw.Draw(img)

    # 小装饰线
    deco_line_w = 80
    line_y = title_block_y + card_pad - 30
    draw.line(
        [(WIDTH // 2 - deco_line_w, line_y), (WIDTH // 2 + deco_line_w, line_y)],
        fill=t["accent"], width=4,
    )

    # 标题文字
    for i, line in enumerate(title_lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_w = bbox[2] - bbox[0]
        x = (WIDTH - line_w) // 2
        y = title_block_y + card_pad + i * line_height

        # 文字阴影
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 30), font=title_font)
        draw.text((x, y), line, fill=t["accent"], font=title_font)

    # ── 底部引导 ──
    guide_font = find_font(30)
    guide_text = "👉 滑到最后有惊喜"
    guide_bbox = draw.textbbox((0, 0), guide_text, font=guide_font)
    guide_w = guide_bbox[2] - guide_bbox[0]
    guide_y = HEIGHT - 180
    draw.text(
        ((WIDTH - guide_w) // 2, guide_y),
        guide_text, fill=(140, 140, 140), font=guide_font,
    )

    # 底部装饰线
    deco_y = guide_y + 55
    margin_x = 250
    draw.line(
        [(margin_x, deco_y), (WIDTH - margin_x, deco_y)],
        fill=t["accent2"], width=2,
    )

    # 署名
    credit_font = find_font(22)
    credit = "每日老黄历 · AI安全 · 能量磁场"
    cbbox = draw.textbbox((0, 0), credit, font=credit_font)
    cw = cbbox[2] - cbbox[0]
    draw.text(
        ((WIDTH - cw) // 2, deco_y + 25),
        credit, fill=(180, 180, 180), font=credit_font,
    )

    img.save(OUTPUT_PATH, "JPEG", quality=95)
    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    return OUTPUT_PATH, size_kb


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--domain", required=True)
    p.add_argument("--title", required=True)
    args = p.parse_args()
    path, size = generate(args.domain, args.title)
    print(f"✅ {path}")
    print(f"📐 {WIDTH}×{HEIGHT} | {size:.0f}KB | {args.domain}")

#!/usr/bin/env python3.13
"""
XHS 知识卡片生成器 v5 — 视觉升级版
=====================================
参考小红书爆款风格：高对比度 + 大字报 + 撞色卡片 + emoji装饰

用法:
    python3.13 xhs_cards.py --type cover --domain "AI" --title "普通人做Agent别一上来就学LangChain"
    python3.13 xhs_cards.py --type data --domain "哮喘" --items "15-30%|CVA占比" "30%|典型哮喘转化率"
    python3.13 xhs_cards.py --type steps --domain "AI" --title "正确入门路径" --items "1|搭Bot|用扣子搭简单Bot" "2|跑通|完整流程" "3|加能力|记忆+工具"
    python3.13 xhs_cards.py --type warning --domain "安全" --items "误区1|真相1" "误区2|真相2"
    python3.13 xhs_cards.py --type cta --domain "AI" --question "你搭过Bot吗？" --options "A.搭过|B.没有"

v5 改进:
- 自动按类型+领域生成不同文件名（不覆盖）
- 视觉：高对比撞色 + 大字报 + 圆角卡片 + emoji标签
- 每种类型有独立配色和排版风格
"""

import sys, os, textwrap, math, random, json
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("pip install Pillow")
    sys.exit(1)

# ═══ 模板系统 ═══
TEMPLATES_PATH = Path(__file__).parent / "xhs_templates.json"

def load_templates():
    """加载模板配置"""
    if TEMPLATES_PATH.exists():
        with open(TEMPLATES_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None

_TEMPLATES = load_templates()

def get_color_scheme(domain):
    """从模板系统获取配色，fallback到内置PALETTE"""
    if _TEMPLATES and domain in _TEMPLATES.get("domain_to_scheme", {}):
        scheme_name = _TEMPLATES["domain_to_scheme"][domain]
        scheme = _TEMPLATES["color_schemes"].get(scheme_name, {})
        if scheme:
            return {
                "bg_top": tuple(scheme["bg_top"]),
                "bg_bot": tuple(scheme["bg_bot"]),
                "accent": tuple(scheme["accent"]),
                "card": tuple(scheme["card"]),
                "card_text": tuple(scheme["card_text"]),
                "tag_bg": tuple(scheme["tag_bg"]),
                "tag_text": tuple(scheme["tag_text"]),
                "num_bg": tuple(scheme["num_bg"]),
                "num_text": tuple(scheme["num_text"]),
                "sub": tuple(scheme["sub"]),
                "tag": scheme["tag"],
                "label": scheme["label"],
            }
    return None

def list_templates():
    """列出所有可用模板"""
    if not _TEMPLATES:
        return []
    return [(k, v["name"], v["description"]) for k, v in _TEMPLATES["templates"].items()]

def list_color_schemes():
    """列出所有配色方案"""
    if not _TEMPLATES:
        return []
    return [(k, v["label"]) for k, v in _TEMPLATES["color_schemes"].items()]

W, H = 1080, 1440
MARGIN = 60


# ═══ 配色方案（小红书爆款风格：高对比撞色）═══
PALETTE = {
    "哮喘": {
        "bg_top": (0, 180, 160),      # 青绿
        "bg_bot": (0, 120, 110),
        "accent": (255, 255, 255),
        "card": (255, 255, 255),
        "card_text": (20, 60, 60),
        "tag_bg": (255, 200, 60),
        "tag_text": (40, 40, 40),
        "num_bg": (255, 100, 80),
        "num_text": (255, 255, 255),
        "sub": (220, 245, 240),
        "tag": "🫁",
        "label": "哮喘/CVA",
    },
    "AI": {
        "bg_top": (30, 30, 80),        # 深蓝
        "bg_bot": (15, 15, 50),
        "accent": (100, 200, 255),
        "card": (255, 255, 255),
        "card_text": (20, 25, 60),
        "tag_bg": (100, 200, 255),
        "tag_text": (10, 20, 50),
        "num_bg": (255, 180, 50),
        "num_text": (30, 20, 0),
        "sub": (180, 210, 255),
        "tag": "🤖",
        "label": "AI/大模型",
    },
    "安全": {
        "bg_top": (180, 30, 30),       # 深红
        "bg_bot": (120, 15, 15),
        "accent": (255, 220, 80),
        "card": (255, 255, 255),
        "card_text": (60, 15, 15),
        "tag_bg": (255, 220, 80),
        "tag_text": (80, 20, 0),
        "num_bg": (40, 40, 40),
        "num_text": (255, 255, 255),
        "sub": (255, 210, 200),
        "tag": "🔒",
        "label": "网络安全",
    },
    "智能体": {
        "bg_top": (80, 40, 160),       # 紫色
        "bg_bot": (50, 20, 110),
        "accent": (200, 160, 255),
        "card": (255, 255, 255),
        "card_text": (30, 15, 60),
        "tag_bg": (255, 200, 60),
        "tag_text": (50, 30, 0),
        "num_bg": (100, 200, 255),
        "num_text": (10, 20, 50),
        "sub": (220, 200, 255),
        "tag": "🧠",
        "label": "智能体",
    },
    "九字真言": {
        "bg_top": (60, 40, 15),        # 深金
        "bg_bot": (35, 22, 8),
        "accent": (255, 200, 60),
        "card": (255, 255, 255),
        "card_text": (50, 35, 10),
        "tag_bg": (255, 200, 60),
        "tag_text": (60, 30, 0),
        "num_bg": (180, 140, 50),
        "num_text": (255, 255, 255),
        "sub": (255, 235, 180),
        "tag": "🔮",
        "label": "小六壬/九字真言",
    },
    "老黄历": {
        "bg_top": (160, 60, 20),       # 朱红
        "bg_bot": (100, 35, 10),
        "accent": (255, 220, 120),
        "card": (255, 255, 255),
        "card_text": (60, 25, 5),
        "tag_bg": (255, 220, 120),
        "tag_text": (80, 35, 0),
        "num_bg": (60, 30, 10),
        "num_text": (255, 230, 150),
        "sub": (255, 225, 190),
        "tag": "📅",
        "label": "老黄历",
    },
}

# 通用 fallback
FALLBACK_PALETTE = {
    "bg_top": (40, 40, 40),
    "bg_bot": (20, 20, 20),
    "accent": (255, 200, 60),
    "card": (255, 255, 255),
    "card_text": (30, 30, 30),
    "tag_bg": (255, 200, 60),
    "tag_text": (40, 30, 0),
    "num_bg": (100, 100, 100),
    "num_text": (255, 255, 255),
    "sub": (200, 200, 200),
    "tag": "📌",
    "label": "",
}


def F(size):
    """查找字体"""
    for p in ["/System/Library/Fonts/PingFang.ttc",
              "/System/Library/Fonts/STHeiti Medium.ttc"]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                pass
    return ImageFont.load_default()


def tw(draw, text, f):
    bbox = draw.textbbox((0, 0), text, font=f)
    return bbox[2] - bbox[0]


def th(draw, text, f):
    bbox = draw.textbbox((0, 0), text, font=f)
    return bbox[3] - bbox[1]


def center(draw, y, text, f, fill, w=W):
    t = tw(draw, text, f)
    draw.text(((w - t) // 2, y), text, fill=fill, font=f)


def gradient_bg(img, c1, c2):
    """垂直渐变背景"""
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return draw


def rounded_rect(draw, xy, r, fill, outline=None, width=0):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def draw_pill(draw, x, y, text, f, bg, fg, padding=16):
    """圆角胶囊标签"""
    tw_text = tw(draw, text, f)
    th_text = th(draw, text, f)
    rx1 = x
    ry1 = y
    rx2 = x + tw_text + padding * 2
    ry2 = y + th_text + padding
    rounded_rect(draw, (rx1, ry1, rx2, ry2), (ry2 - ry1) // 2, bg)
    draw.text((x + padding, y + padding // 2), text, fill=fg, font=f)
    return rx2


def draw_card_block(draw, x, y, w, h, pal):
    """白色卡片块"""
    rounded_rect(draw, (x, y, x + w, y + h), 16, pal["card"])
    # 底部阴影效果（用深色半透明条模拟）
    for dy in range(4):
        alpha_factor = 1 - dy / 4
        shadow_c = tuple(int(v * 0.85 * alpha_factor) for v in pal["bg_top"])
        draw.line([(x + 8, y + h + dy), (x + w - 8, y + h + dy)], fill=shadow_c)


def save_card(img, path):
    """统一保存：RGBA→RGB 再存 JPEG"""
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[3])
        img = bg
    img.save(path, "JPEG", quality=92)


def auto_output(card_type, domain):
    """自动生成输出路径：/tmp/xhs_{domain}_{type}.jpg"""
    safe_domain = domain.replace("/", "_").replace(" ", "")
    return f"/tmp/xhs_{safe_domain}_{card_type}.jpg"


# ═══ P1: 封面图 ═══
def card_cover(pal, title, output):
    img = Image.new("RGB", (W, H), pal["bg_top"])
    draw = gradient_bg(img, pal["bg_top"], pal["bg_bot"])

    # 顶部标签
    tag_f = F(32)
    tag_text = f"  {pal['tag']}  {pal['label']}  "
    tag_tw = tw(draw, tag_text, tag_f)
    tag_x = (W - tag_tw - 40) // 2
    rounded_rect(draw, (tag_x, 80, tag_x + tag_tw + 40, 130), 25, pal["tag_bg"])
    draw.text((tag_x + 20, 88), tag_text, fill=pal["tag_text"], font=tag_f)

    # 主标题区 — 白色大卡片
    card_pad = 50
    title_f = F(72)
    lines = textwrap.wrap(title, width=12)
    lh = int(title_f.size * 1.4)
    total_h = lh * len(lines)
    card_y1 = (H - total_h) // 2 - card_pad - 20
    card_y2 = card_y1 + total_h + card_pad * 2 + 40

    # 白色卡片
    rounded_rect(draw, (MARGIN - 20, card_y1, W - MARGIN + 20, card_y2), 24, pal["card"])

    # 卡片顶部装饰条
    rounded_rect(draw, (MARGIN - 20, card_y1, W - MARGIN + 20, card_y1 + 8), 4, pal["num_bg"])

    # 标题文字
    for i, line in enumerate(lines):
        t = tw(draw, line, title_f)
        x = (W - t) // 2
        y = card_y1 + card_pad + 10 + i * lh
        draw.text((x, y), line, fill=pal["card_text"], font=title_f)

    # 底部互动引导
    bot_f = F(28)
    center(draw, card_y2 + 40, "← 左右滑动查看更多 →", bot_f, pal["accent"])

    # 底部装饰点
    for i in range(5):
        cx = W // 2 - 40 + i * 20
        r = 4 if i == 2 else 3
        c = pal["accent"] if i == 2 else tuple(max(0, v - 80) for v in pal["accent"])
        draw.ellipse([cx - r, H - 100 - r, cx + r, H - 100 + r], fill=c)

    save_card(img, output)
    return output


# ═══ P2: 数据卡片 ═══
def card_data(pal, items, output):
    """items: list of (数字, 标签)"""
    img = Image.new("RGB", (W, H), pal["bg_top"])
    draw = gradient_bg(img, pal["bg_top"], pal["bg_bot"])

    # 标题
    tf = F(40)
    title_text = f"  {pal['tag']}  关键数据"
    center(draw, 70, title_text, tf, pal["accent"])

    n = len(items)
    card_h = min(240, (H - 280) // max(n, 1) - 20)
    start_y = 160

    for i, item in enumerate(items):
        if isinstance(item, tuple) and len(item) >= 2:
            num, label = item[0], item[1]
        else:
            num, label = str(item), ""

        y = start_y + i * (card_h + 16)

        # 白色卡片
        rounded_rect(draw, (MARGIN, y, W - MARGIN, y + card_h), 18, pal["card"])

        # 左侧彩色竖条
        rounded_rect(draw, (MARGIN, y, MARGIN + 8, y + card_h), 4, pal["num_bg"])

        # 数字（超大号）
        nf = F(80)
        draw.text((MARGIN + 35, y + 25), num, fill=pal["num_bg"], font=nf)

        # 标签
        lf = F(30)
        draw.text((MARGIN + 35, y + card_h - 60), label, fill=pal["card_text"], font=lf)

    # 底部来源
    bf = F(22)
    center(draw, H - 60, "数据来源：行业报告 / 学术文献", bf, pal["sub"])

    save_card(img, output)
    return output


# ═══ P3: 步骤卡片 ═══
def card_steps(pal, title, items, output):
    """items: list of (序号, 标题, 说明)"""
    img = Image.new("RGB", (W, H), pal["bg_top"])
    draw = gradient_bg(img, pal["bg_top"], pal["bg_bot"])

    # 标题
    tf = F(38)
    center(draw, 70, title, tf, pal["accent"])

    n = len(items)
    card_h = min(200, (H - 280) // max(n, 1) - 15)
    start_y = 150

    for i, item in enumerate(items):
        if isinstance(item, tuple) and len(item) >= 3:
            num, step_title, desc = str(item[0]), item[1], item[2]
        elif isinstance(item, tuple) and len(item) == 2:
            num, step_title, desc = str(item[0]), item[1], ""
        else:
            num = str(i + 1)
            step_title = str(item)
            desc = ""

        y = start_y + i * (card_h + 14)

        # 白色卡片
        rounded_rect(draw, (MARGIN, y, W - MARGIN, y + card_h), 18, pal["card"])

        # 编号圆
        cx, cy_c = MARGIN + 45, y + card_h // 2
        draw.ellipse([cx - 28, cy_c - 28, cx + 28, cy_c + 28], fill=pal["num_bg"])
        nf = F(30)
        nw = tw(draw, num, nf)
        nh = th(draw, num, nf)
        draw.text((cx - nw // 2, cy_c - nh // 2 - 2), num, fill=pal["num_text"], font=nf)

        # 步骤标题
        stf = F(34)
        draw.text((MARGIN + 95, y + 25), step_title, fill=pal["card_text"], font=stf)

        # 说明
        if desc:
            df = F(24)
            draw.text((MARGIN + 95, y + 75), desc, fill=(120, 120, 130), font=df)

        # 右侧箭头
        arrow_f = F(32)
        draw.text((W - MARGIN - 45, y + card_h // 2 - 18), "→", fill=pal["num_bg"], font=arrow_f)

    save_card(img, output)
    return output


# ═══ P4: 避坑卡片 ═══
def card_warning(pal, items, output):
    """items: list of (误区, 真相)"""
    img = Image.new("RGB", (W, H), pal["bg_top"])
    draw = gradient_bg(img, pal["bg_top"], pal["bg_bot"])

    # 标题
    tf = F(38)
    center(draw, 70, "⚠️  常见误区", tf, pal["accent"])

    n = len(items)
    card_h = min(200, (H - 280) // max(n, 1) - 15)
    start_y = 160

    for i, item in enumerate(items):
        if isinstance(item, tuple) and len(item) >= 2:
            myth, truth = item[0], item[1]
        else:
            myth, truth = str(item), ""

        y = start_y + i * (card_h + 14)

        # 白色卡片
        rounded_rect(draw, (MARGIN, y, W - MARGIN, y + card_h), 18, pal["card"])

        # 左侧红色竖条
        rounded_rect(draw, (MARGIN, y, MARGIN + 8, y + card_h), 4, (220, 50, 50))

        # 误区（❌）
        mf = F(30)
        draw.text((MARGIN + 28, y + 25), f"❌  {myth}", fill=(200, 40, 40), font=mf)

        # 真相（✅）
        tf2 = F(28)
        draw.text((MARGIN + 28, y + 80), f"✅  {truth}", fill=(30, 130, 60), font=tf2)

    # 底部提醒
    bf = F(24)
    center(draw, H - 70, "记住这几点，少走弯路 👆", bf, pal["sub"])

    save_card(img, output)
    return output


# ═══ P5: 互动引导卡片 ═══
def card_cta(pal, question, options, output):
    img = Image.new("RGB", (W, H), pal["bg_top"])
    draw = gradient_bg(img, pal["bg_top"], pal["bg_bot"])

    # 标题
    tf = F(38)
    center(draw, 100, "💬  互动时间", tf, pal["accent"])

    # 问题卡片（白色大块）
    qf = F(36)
    q_lines = textwrap.wrap(question, width=16)
    qh = len(q_lines) * 55
    qy = 200
    rounded_rect(draw, (MARGIN, qy, W - MARGIN, qy + qh + 50), 20, pal["card"])
    for i, line in enumerate(q_lines):
        center(draw, qy + 25 + i * 55, line, qf, pal["card_text"])

    # 选项按钮
    oy = qy + qh + 80
    of = F(32)
    for i, opt in enumerate(options):
        label = opt.split("|")[0] if "|" in opt else opt
        # 彩色选项条
        opt_bg = pal["num_bg"] if i % 2 == 0 else pal["accent"]
        opt_fg = pal["num_text"] if i % 2 == 0 else pal["tag_text"]
        rounded_rect(draw, (MARGIN + 20, oy, W - MARGIN - 20, oy + 70), 14, opt_bg)
        center(draw, oy + 17, label, of, opt_fg)
        oy += 90

    # 底部引导
    bf = F(28)
    center(draw, H - 120, "评论区告诉我你的答案 👇", bf, pal["accent"])
    sf = F(24)
    center(draw, H - 70, "关注我 · 每天一个实用小知识", sf, pal["sub"])

    save_card(img, output)
    return output


# ═══ 入口 ═══
def generate_card(card_type, domain, output=None, **kwargs):
    # 优先从模板系统获取配色
    pal = get_color_scheme(domain)
    if not pal:
        pal = PALETTE.get(domain, FALLBACK_PALETTE)
    if not output:
        output = auto_output(card_type, domain)
    os.makedirs(os.path.dirname(output) if os.path.dirname(output) else "/tmp", exist_ok=True)

    generators = {
        "cover": lambda: card_cover(pal, kwargs.get("title", ""), output),
        "data": lambda: card_data(pal, kwargs.get("items", []), output),
        "steps": lambda: card_steps(pal, kwargs.get("title", "步骤"), kwargs.get("items", []), output),
        "warning": lambda: card_warning(pal, kwargs.get("items", []), output),
        "cta": lambda: card_cta(pal, kwargs.get("question", ""), kwargs.get("options", []), output),
    }

    gen = generators.get(card_type)
    if not gen:
        print(f"❌ 未知类型: {card_type}")
        sys.exit(1)

    gen()
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="XHS Cards v5 + Template System")
    parser.add_argument("--type", choices=["cover", "data", "steps", "warning", "cta"])
    parser.add_argument("--domain", default="AI")
    parser.add_argument("--title", default="")
    parser.add_argument("--items", nargs="*", default=[])
    parser.add_argument("--question", default="")
    parser.add_argument("--options", nargs="*", default=[])
    parser.add_argument("--output", default=None)
    parser.add_argument("--scheme", default=None, help="Color scheme name (e.g., tech_blue, green_minimal)")
    parser.add_argument("--template", default=None, help="Template name (e.g., T1_compare, T2_list)")
    parser.add_argument("--list-templates", action="store_true", help="List all available templates")
    parser.add_argument("--list-schemes", action="store_true", help="List all color schemes")
    args = parser.parse_args()

    if args.list_templates:
        for tid, name, desc in list_templates():
            print(f"  {tid}: {name} — {desc}")
        sys.exit(0)

    if args.list_schemes:
        for sid, label in list_color_schemes():
            print(f"  {sid}: {label}")
        sys.exit(0)

    if not args.type:
        parser.error("--type is required (or use --list-templates/--list-schemes)")

    items = [tuple(item.split("|")) if "|" in item else item for item in args.items]

    out = generate_card(args.type, args.domain, output=args.output,
                        title=args.title, items=items,
                        question=args.question, options=args.options)
    print(f"✅ {out}")

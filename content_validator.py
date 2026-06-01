#!/usr/bin/env python3
"""
内容校验器 — 小红书发布前内容检查

检查项：
1. 标题长度 ≤20 字
2. 正文字数 100-1000
3. 标签 3-5 个
4. 禁止词/敏感词
5. 格式完整性
6. 七领域覆盖检查

用法：
    python content_validator.py --file ~/shared/daily-xhs-raw.md
    python content_validator.py --title "..." --content "..." --tags tag1 tag2 tag3
"""

import argparse, json, re, sys, os

PLATFORM_RULES = {
    "title": {"max_chars": 20, "min_chars": 1},
    "content": {"max_chars": 1000, "min_chars": 100},
    "tags": {"min_count": 3, "max_count": 5},
    "image": {"min_size_kb": 50, "max_size_kb": 2048},
}

REQUIRED_DOMAINS = ["📅", "🫁", "🤖", "🧠", "🔒", "🔮"]
DOMAIN_LABELS = {
    "📅": "老黄历", "🫁": "哮喘", "🤖": "AI",
    "🧠": "智能体", "🔒": "安全", "🔮": "小六壬/九字真言"
}

FORBIDDEN_PATTERNS = [
    (r"来源[:：]", "禁止标注来源"),
    (r"参考[:：].*http", "禁止标注参考链接"),
    (r"数据采集", "禁止标注数据采集时间"),
    (r"今日小结", "禁止「今日小结」段落"),
    (r"^\s*#{1,3}\s", "禁止 Markdown 标题"),
    (r"\*\*|__", "禁止 Markdown 加粗"),
]

def validate_title(title: str) -> list[dict]:
    issues = []
    r = PLATFORM_RULES["title"]
    if len(title) > r["max_chars"]:
        issues.append({"severity":"error","field":"title",
            "message":f"标题 {len(title)} 字，超过 {r['max_chars']}",
            "suggestion":f"删减 {len(title)-r['max_chars']} 字"})
    if len(title) < r["min_chars"]:
        issues.append({"severity":"error","field":"title",
            "message":"标题为空","suggestion":"标题不能为空"})
    return issues

def validate_content(text: str) -> list[dict]:
    issues = []
    r = PLATFORM_RULES["content"]
    if len(text) > r["max_chars"]:
        issues.append({"severity":"warn","field":"content",
            "message":f"正文 {len(text)} 字，超 {r['max_chars']}",
            "suggestion":f"删减 {len(text)-r['max_chars']} 字"})
    if len(text) < r["min_chars"]:
        issues.append({"severity":"warn","field":"content",
            "message":f"正文 {len(text)} 字，低于 {r['min_chars']}",
            "suggestion":"补充内容"})
    for pat, desc in FORBIDDEN_PATTERNS:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            issues.append({"severity":"error","field":"content",
                "message":f"禁止: {desc}","snippet":m.group(),
                "suggestion":"删除此内容"})
    return issues

def validate_tags(tags: list[str]) -> list[dict]:
    issues = []
    r = PLATFORM_RULES["tags"]
    if len(tags) < r["min_count"]:
        issues.append({"severity":"warn","field":"tags",
            "message":f"标签 {len(tags)} 个，少于 {r['min_count']}",
            "suggestion":"添加标签"})
    if len(tags) > r["max_count"]:
        issues.append({"severity":"warn","field":"tags",
            "message":f"标签 {len(tags)} 个，多于 {r['max_count']}",
            "suggestion":f"删减 {len(tags)-r['max_count']} 个"})
    for tag in tags:
        if not tag.startswith("#"):
            issues.append({"severity":"error","field":"tags",
                "message":f"标签 '{tag}' 无 # 前缀",
                "suggestion":"所有标签需 # 开头"})
    return issues

def validate_image(image_path: str) -> list[dict]:
    if not os.path.exists(image_path):
        return [{"severity":"error","field":"image",
            "message":f"配图不存在: {image_path}",
            "suggestion":"检查图片路径"}]
    size_kb = os.path.getsize(image_path) / 1024
    r = PLATFORM_RULES["image"]
    issues = []
    if size_kb < r["min_size_kb"]:
        issues.append({"severity":"warn","field":"image",
            "message":f"图片 {size_kb:.0f}KB < {r['min_size_kb']}KB",
            "suggestion":"图片可能质量过低"})
    if size_kb > r["max_size_kb"]:
        issues.append({"severity":"error","field":"image",
            "message":f"图片 {size_kb:.0f}KB > {r['max_size_kb']}KB",
            "suggestion":"需压缩图片"})
    return issues

def validate_domain_coverage(content: str) -> list[dict]:
    return [{"severity":"warn","field":"domain","message":f"缺失 {e} {DOMAIN_LABELS[e]}",
             "suggestion":f"补充 {DOMAIN_LABELS[e]} 内容"}
            for e in REQUIRED_DOMAINS if e not in content]

def parse_daily_file(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as f:
        raw = f.read()
    lines = raw.strip().split("\n")
    title, content_lines, tags = "", [], []
    in_tags = False
    for i, line in enumerate(lines):
        s = line.strip()
        if not s: continue
        if i == 0:
            title = s; continue
        if s.startswith("#") and not s.startswith("##"):
            tags.append(s); in_tags = True; continue
        if not in_tags: content_lines.append(s)
    return {"title":title, "content":"\n".join(content_lines), "tags":tags}

def validate_all(title: str, content: str, tags: list[str], image_path: str = None) -> dict:
    issues = validate_title(title) + validate_content(content) + validate_tags(tags) \
             + validate_domain_coverage(content)
    if image_path: issues += validate_image(image_path)
    errors = [i for i in issues if i["severity"]=="error"]
    return {
        "pass": len(errors)==0,
        "total_issues": len(issues), "errors": len(errors),
        "warnings": len(issues)-len(errors), "issues": issues,
        "stats": {"title_chars":len(title), "content_chars":len(content), "tag_count":len(tags)}
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="XHS 内容校验器")
    p.add_argument("--file")
    p.add_argument("--title")
    p.add_argument("--content")
    p.add_argument("--tags", nargs="*")
    p.add_argument("--image")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    if args.file:
        data = parse_daily_file(args.file)
        result = validate_all(data["title"], data["content"], data["tags"], args.image)
    elif args.title and args.content:
        result = validate_all(args.title, args.content, args.tags or [], args.image)
    else:
        p.print_help(); sys.exit(1)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        icon = "✅" if result["pass"] else "❌"
        print(f"\n{icon} {'通过' if result['pass'] else '不通过'} | "
              f"{result['errors']}错 {result['warnings']}警 | {result['stats']['content_chars']}字\n")
        for i in result["issues"]:
            ic = "❌" if i["severity"]=="error" else "⚠️"
            print(f"  {ic} [{i['field']}] {i['message']}")
            if i.get("suggestion"): print(f"      → {i['suggestion']}")
    sys.exit(0 if result["pass"] else 1)

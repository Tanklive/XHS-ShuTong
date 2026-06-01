#!/usr/bin/env python3.13
"""
XHS 内容过滤 + 降维预处理 — Phase 2
====================================
读取 feed JSON → 按领域分组 → 输出结构化摘要 → LLM 直接消费

用法:
    python3.13 xhs_content_filter.py [--date YYYY-MM-DD]

输出:
    ~/shared/xhs_feeds/YYYY-MM-DD_digest.md  （结构化摘要，给 LLM 读）
"""

import json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
FEED_DIR = Path.home() / "shared" / "xhs_feeds"

# 领域聚合规则
DOMAIN_GROUP = {
    "🤖": "AI/大模型/周鸿祎",
    "🔒": "网络安全",
    "🫁": "哮喘/CVA",
    "🧠": "智能体",
    "📅": "老黄历",
    "🔮": "小六壬/九字真言",
}


def main():
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now(CST).strftime("%Y-%m-%d")
    feed_path = FEED_DIR / f"{date_str}.json"

    if not feed_path.exists():
        print(f"❌ Feed 文件不存在: {feed_path}")
        print(f"   先运行: python3.13 xhs_feed_fetcher.py --date {date_str}")
        sys.exit(1)

    with open(feed_path, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])

    # 按领域分组
    groups = {}
    for item in items:
        d = item["domain"]
        groups.setdefault(d, []).append(item)

    # 输出结构化摘要
    digest_path = FEED_DIR / f"{date_str}_digest.md"
    with open(digest_path, "w", encoding="utf-8") as f:
        f.write(f"# 📡 XHS 信息源摘要 — {date_str}\n")
        f.write(f"> 共 {len(items)} 条，已去重。以下为 LLM 降维重写的原始素材。\n\n")
        f.write("---\n\n")

        for emoji, name in DOMAIN_GROUP.items():
            items_in_group = groups.get(emoji, [])
            f.write(f"## {emoji} {name} ({len(items_in_group)} 条)\n\n")

            if not items_in_group:
                f.write("> ⚠️ 无自动抓取结果，需手动搜索补充。\n\n")
                continue

            for idx, item in enumerate(items_in_group, 1):
                f.write(f"**{idx}.** {item['title']}\n")
                if item.get("summary"):
                    f.write(f"  📝 {item['summary'][:150]}\n")
                f.write(f"  🔗 {item.get('link', '')}\n")
                f.write(f"  🏷️ {', '.join(item.get('tags', []))}\n\n")
            f.write("\n")

        f.write("---\n\n")
        f.write("## ✍️ LLM 降维指令\n\n")
        f.write("```\n")
        f.write("对以上素材执行降维重写：\n\n")
        f.write("1. 【核心提取】从每个领域提取1条最有爆点的信息\n")
        f.write("2. 【降维翻译】\n")
        f.write("   - 不说技术名词，说结果\n")
        f.write("   - 不说\"研究表明\"，说\"XX的大哥试了后\"\n")
        f.write("   - 不说漏洞编号，说\"赶紧检查你的密码\"\n")
        f.write("3. 【情绪包装】加emoji、短句、口语化\n")
        f.write("4. 【标题生成】产出3个钩子型标题备选（人群标签+数字+情绪）\n")
        f.write("5. 【互动钩子】每篇结尾加1个提问/选择/征集\n")
        f.write("6. 缺失领域（标记⚠️的）用已有知识库补充\n")
        f.write("```\n")

    print(f"✅ 摘要已生成: {digest_path}")
    print(f"📊 {len(groups)} 个领域, {len(items)} 条")

    # 也输出到 stdout 方便查看
    for emoji, name in DOMAIN_GROUP.items():
        count = len(groups.get(emoji, []))
        status = "✅" if count > 0 else "⚠️需补充"
        print(f"  {emoji} {name}: {count}条 {status}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3.13
"""
XHS 信息源聚合器 — Phase 1
============================
每天拉取所有指定源的标题/摘要，去重后输出 JSON，供 LLM 节点消费。

用法:
    python3.13 xhs_feed_fetcher.py [--date YYYY-MM-DD]

输出:
    ~/shared/xhs_feeds/YYYY-MM-DD.json
"""

import json, os, sys, hashlib, re, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

try:
    import asyncio
    from bilibili_api import user
    HAS_BILI = True
except ImportError:
    HAS_BILI = False

try:
    import feedparser
except ImportError:
    print("请先安装: python3.13 -m pip install feedparser --break-system-packages")
    sys.exit(1)

# ── 配置 ──────────────────────────────────────────────
OUTPUT_DIR = Path.home() / "shared" / "xhs_feeds"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
REQUEST_TIMEOUT = 15
MAX_ITEMS_PER_SOURCE = 3  # 每个源最多取几条

# 上海时区
CST = timezone(timedelta(hours=8))

# ── 信息源定义 ──────────────────────────────────────
RSS_SOURCES = {
    # 🤖 AI
    "36kr": {
        "url": "https://36kr.com/feed",
        "domain": "🤖",
        "tags": ["AI", "科技"],
    },
    # 🔒 安全
    "freebuf": {
        "url": "https://www.freebuf.com/feed",
        "domain": "🔒",
        "tags": ["安全"],
    },
}
# B站 UP 主视频源（无需登录，每日拉取最新视频）
# 网页源（curl 直接抓）
WEB_SOURCES = {
    "anquanke": {
        "url": "https://www.anquanke.com/",
        "domain": "🔒",
        "tags": ["安全"],
        "extractor": "anquanke",
    },
}
# B站 UP 主视频源（无需登录，每日拉取最新视频）
BILI_UPERS = {
    "bilibili_chaping": {
        "uid": 19319172, "domain": "🤖", "tags": ["AI", "科技"],
        "name": "差评君",
    },
    "bilibili_linyi": {
        "uid": 4401694, "domain": "🤖", "tags": ["AI", "科技"],
        "name": "林亦LYi",
    },
    "bilibili_nenly": {
        "uid": 1814756990, "domain": "🧠", "tags": ["AI", "智能体"],
        "name": "Nenly同学",
    },
    "bilibili_dingxiang": {
        "uid": 15982391, "domain": "🫁", "tags": ["健康", "医疗"],
        "name": "丁香医生",
    },
    "bilibili_hacker_k": {
        "uid": 1250760721, "domain": "🔒", "tags": ["安全"],
        "name": "黑客老K",
    },
}


# ── 工具函数 ──────────────────────────────────────────
def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def fetch_rss(source_name: str, config: dict, date_str: str) -> list:
    """拉取 RSS 源"""
    items = []
    try:
        feed = feedparser.parse(
            config["url"],
            agent=USER_AGENT,
        )
        if feed.bozo and not feed.entries:
            print(f"  ⚠️ {source_name}: RSS 解析失败 - {feed.bozo_exception}")
            return items

        today = date_str  # YYYY-MM-DD
        for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = time.strftime("%Y-%m-%d", entry.published_parsed)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = time.strftime("%Y-%m-%d", entry.updated_parsed)

            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            # 清理 HTML 标签
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            if len(summary) > 200:
                summary = summary[:200] + "…"

            items.append({
                "id": make_id(link),
                "source": source_name,
                "domain": config["domain"],
                "title": title,
                "link": link,
                "summary": summary,
                "date": pub_date or today,
                "tags": config.get("tags", []),
            })
        print(f"  ✅ {source_name}: {len(items)} 条")
    except Exception as e:
        print(f"  ❌ {source_name}: {e}")
    return items


def fetch_web(source_name: str, config: dict, date_str: str) -> list:
    """抓取网页源（简单 title 提取）"""
    items = []
    try:
        req = Request(config["url"], headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        extractor = config.get("extractor", "generic")
        if extractor == "anquanke":
            # 安全客首页 /post/id/XXXXX 格式
            matches = re.findall(r'<a[^>]*href="(/post/id/\d+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            for href, raw_text in matches[:MAX_ITEMS_PER_SOURCE]:
                t = re.sub(r"<[^>]+>", "", raw_text).strip()
                if t and len(t) > 5 and "memberId" not in href:
                    items.append({
                        "id": make_id(href),
                        "source": source_name,
                        "domain": config["domain"],
                        "title": t,
                        "link": f"https://www.anquanke.com{href}",
                        "summary": t,
                        "date": date_str,
                        "tags": config.get("tags", []),
                    })
        else:
            # 通用：提取 <title> 和 meta description
            title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
            desc_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else source_name
            items.append({
                "id": make_id(config["url"]),
                "source": source_name,
                "domain": config["domain"],
                "title": title,
                "link": config["url"],
                "summary": desc_match.group(1)[:200] if desc_match else "",
                "date": date_str,
                "tags": config.get("tags", []),
            })

        print(f"  ✅ {source_name}: {len(items)} 条")
    except Exception as e:
        print(f"  ❌ {source_name}: {e}")
    return items


async def _fetch_bilibili_async(source_name: str, config: dict, date_str: str) -> list:
    """异步拉取 B站 UP 主最新视频"""
    items = []
    try:
        u = user.User(uid=config["uid"])
        result = await u.get_videos(ps=MAX_ITEMS_PER_SOURCE, pn=1)
        videos = result.get("list", {}).get("vlist", [])
        for v in videos:
            bvid = v["bvid"]
            title = v["title"].strip()
            desc = (v.get("description") or "").strip()
            if len(desc) > 200:
                desc = desc[:200] + "…"
            items.append({
                "id": bvid,
                "source": source_name,
                "domain": config["domain"],
                "title": title,
                "link": f"https://www.bilibili.com/video/{bvid}",
                "summary": desc,
                "date": date_str,
                "tags": config.get("tags", []),
            })
        print(f"  ✅ {source_name} ({config['name']}): {len(items)} 条")
    except Exception as e:
        print(f"  ❌ {source_name}: {e}")
    return items


async def _fetch_all_bilibili(upers: dict, date_str: str) -> list:
    """批量异步拉取所有 B站 UP 主视频，10s 间隔防风控，单个失败不影响整体"""
    import asyncio as _aio
    all_items = []
    success = 0
    for name, cfg in upers.items():
        try:
            items = await _fetch_bilibili_async(name, cfg, date_str)
            all_items.extend(items)
            if items:
                success += 1
                await _aio.sleep(10)  # 成功请求后等 10s
        except Exception as e:
            print(f"  ⚠️ {name}: 异常跳过 - {e}")
    print(f"  📊 B站: {success}/{len(upers)} 个 UP 主成功")
    return all_items


def fetch_all_bilibili(upers: dict, date_str: str) -> list:
    """同步包装：批量拉取所有 B站 UP 主视频"""
    if not HAS_BILI:
        print("  ⚠️ bilibili-api 未安装，跳过所有 B站源")
        return []
    return asyncio.run(_fetch_all_bilibili(upers, date_str))


def deduplicate(items: list) -> list:
    """按标题相似度去重"""
    seen = set()
    result = []
    for item in items:
        # 简单去重：提取标题前30个字符的 hash
        key = hashlib.md5(item["title"][:30].encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ── 主流程 ────────────────────────────────────────────
def main():
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now(CST).strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📡 XHS Feed Fetcher — {date_str}")
    print(f"{'─'*50}")

    all_items = []

    # RSS 源
    print("\n📻 RSS 源:")
    for name, cfg in RSS_SOURCES.items():
        items = fetch_rss(name, cfg, date_str)
        all_items.extend(items)

    # 网页源
    print("\n🌐 网页源:")
    for name, cfg in WEB_SOURCES.items():
        items = fetch_web(name, cfg, date_str)
        all_items.extend(items)

    # B站 UP 主（单次 asyncio.run，批量拉取）
    print("\n📺 B站 UP 主:")
    if HAS_BILI:
        bili_items = fetch_all_bilibili(BILI_UPERS, date_str)
        all_items.extend(bili_items)
    else:
        print("  ⚠️ bilibili-api 未安装")

    # 去重
    before = len(all_items)
    all_items = deduplicate(all_items)
    print(f"\n🔍 去重: {before} → {len(all_items)}")

    # 输出
    output = {
        "date": date_str,
        "fetched_at": datetime.now(CST).isoformat(),
        "total": len(all_items),
        "items": all_items,
    }

    out_path = OUTPUT_DIR / f"{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 摘要
    print(f"\n{'─'*50}")
    domains = {}
    for item in all_items:
        d = item["domain"]
        domains[d] = domains.get(d, 0) + 1
    for d, c in domains.items():
        print(f"  {d} x{c} 条")
    print(f"\n📄 输出: {out_path}")
    print(f"📊 总计: {len(all_items)} 条")

    # 🌡️ 源头健康度检查
    sources_got = set(item["source"] for item in all_items)
    all_sources = set(RSS_SOURCES.keys()) | set(WEB_SOURCES.keys()) | set(BILI_UPERS.keys())
    failed = all_sources - sources_got
    if failed:
        print(f"\n⚠️ 以下源未产出内容:")
        for s in sorted(failed):
            label = BILI_UPERS.get(s, {}).get("name", s)
            print(f"  ❌ {label}")


if __name__ == "__main__":
    main()

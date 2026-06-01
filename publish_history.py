#!/usr/bin/env python3
"""
发布历史追踪 — 记录每次发布 + 查看历史

用法：
    python publish_history.py record --title "..." --status published [--note-url "URL"]
    python publish_history.py list [--last 10]
    python publish_history.py stats
    python publish_history.py today
"""

import argparse, json, os, sys
from datetime import datetime, timezone

HISTORY_FILE = os.path.expanduser("~/shared/xhs-publish-history.jsonl")
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

def record(title: str, status: str, note_url: str = "", content_chars: int = 0, tags: list = None):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "title": title,
        "status": status,  # published, preview, failed
        "note_url": note_url,
        "content_chars": content_chars,
        "tags": tags or [],
    }
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"📝 已记录: [{status}] {title[:30]}")

def list_history(last_n: int = 10) -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    entries = []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except:
                pass
    return entries[-last_n:]

def stats() -> dict:
    entries = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    
    if not entries:
        return {"total": 0, "published": 0, "failed": 0, "preview": 0,
                "first_date": None, "last_date": None, "streak_days": 0, "avg_chars": 0}
    
    dates = sorted(set(e["date"] for e in entries))
    published = [e for e in entries if e.get("status") == "published"]
    
    # 计算连续发布天数
    streak = 0
    today = datetime.now().strftime("%Y-%m-%d")
    check_date = today
    while check_date in dates:
        streak += 1
        from datetime import timedelta
        check_date = (datetime.now() - timedelta(days=streak)).strftime("%Y-%m-%d")
    
    pub_chars = [e.get("content_chars", 0) for e in published]
    
    return {
        "total": len(entries),
        "published": len(published),
        "failed": sum(1 for e in entries if e.get("status") == "failed"),
        "preview": sum(1 for e in entries if e.get("status") == "preview"),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "streak_days": streak,
        "avg_chars": round(sum(pub_chars) / len(pub_chars)) if pub_chars else 0,
    }

def today_entries() -> list:
    today = datetime.now().strftime("%Y-%m-%d")
    entries = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                    if e.get("date") == today:
                        entries.append(e)
                except:
                    pass
    return entries

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="XHS 发布历史")
    sub = p.add_subparsers(dest="cmd")
    
    rec = sub.add_parser("record")
    rec.add_argument("--title", required=True)
    rec.add_argument("--status", required=True, choices=["published","preview","failed"])
    rec.add_argument("--note-url", default="")
    rec.add_argument("--content-chars", type=int, default=0)
    rec.add_argument("--tags", nargs="*")
    
    lst = sub.add_parser("list")
    lst.add_argument("--last", type=int, default=10)
    
    sub.add_parser("stats")
    sub.add_parser("today")
    
    args = p.parse_args()
    
    if args.cmd == "record":
        record(args.title, args.status, args.note_url, args.content_chars, args.tags)
    
    elif args.cmd == "list":
        entries = list_history(args.last)
        if not entries:
            print("暂无发布记录")
        else:
            print(f"\n📋 最近 {len(entries)} 条发布记录:\n")
            for e in reversed(entries):
                icon = {"published":"✅","preview":"👁️","failed":"❌"}
                print(f"  {icon.get(e['status'],'❓')} [{e['date']} {e['time']}] {e['title'][:40]}")
                if e.get("content_chars"): print(f"     {e['content_chars']}字")
    
    elif args.cmd == "stats":
        s = stats()
        print(f"\n📊 XHS 发布统计\n")
        print(f"  总发布: {s['total']}")
        print(f"  成功: {s['published']}  |  预览: {s['preview']}  |  失败: {s['failed']}")
        print(f"  起止: {s['first_date']} → {s['last_date']}")
        print(f"  连续发布: {s['streak_days']} 天{' 🔥' if s['streak_days'] >= 7 else ''}")
        if s['avg_chars']: print(f"  平均字数: {s['avg_chars']}")
    
    elif args.cmd == "today":
        entries = today_entries()
        if not entries:
            print("今日暂无发布")
        else:
            print(f"\n📅 今日发布 ({len(entries)} 条):\n")
            for e in entries:
                icon = {"published":"✅","preview":"👁️","failed":"❌"}
                print(f"  {icon.get(e['status'],'❓')} [{e['time']}] {e['title'][:40]}")

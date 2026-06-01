#!/usr/bin/env python3
"""
XHS 发布归档 + 清理脚本
用法: python3 xhs_archive_cleanup.py [--date YYYY-MM-DD] [--dry-run]

功能:
1. 把 /tmp/xhs_card_*.jpg 归档到 ~/shared/xhs-publish-records/YYYY-MM-DD/
2. 归档 daily-xhs-raw.md 到同目录
3. 清空 /tmp/xhs_card_*.jpg，防止第二天残留
"""

import os, sys, shutil, glob
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
RECORDS_DIR = os.path.expanduser("~/shared/xhs-publish-records")
TMP_DIR = "/tmp"
RAW_FILE = os.path.expanduser("~/shared/daily-xhs-raw.md")

def main():
    dry_run = "--dry-run" in sys.argv
    
    # Parse date
    date_str = datetime.now(CST).strftime("%Y-%m-%d")
    for arg in sys.argv[1:]:
        if arg.startswith("202") and len(arg) == 10:
            date_str = arg
    
    archive_dir = os.path.join(RECORDS_DIR, date_str)
    
    # Find card images
    cards = sorted(glob.glob(os.path.join(TMP_DIR, "xhs_card_*.jpg")))
    if not cards:
        print(f"⚠️ 没有找到 /tmp/xhs_card_*.jpg，跳过")
        return
    
    print(f"📦 归档日期: {date_str}")
    print(f"📁 归档目录: {archive_dir}")
    print(f"🖼️ 找到 {len(cards)} 张卡片")
    
    if dry_run:
        print("\n[dry-run] 不执行实际操作")
        for c in cards:
            print(f"  → {os.path.basename(c)}")
        if os.path.exists(RAW_FILE):
            print(f"  → content.md (from daily-xhs-raw.md)")
        return
    
    # Create archive dir
    os.makedirs(archive_dir, exist_ok=True)
    
    # Copy cards
    for c in cards:
        dest = os.path.join(archive_dir, os.path.basename(c))
        shutil.copy2(c, dest)
        print(f"  ✅ {os.path.basename(c)} → {date_str}/")
    
    # Copy content
    if os.path.exists(RAW_FILE):
        shutil.copy2(RAW_FILE, os.path.join(archive_dir, "content.md"))
        print(f"  ✅ content.md → {date_str}/")
    
    # Cleanup tmp
    for c in cards:
        os.remove(c)
        print(f"  🗑️ 清理 {os.path.basename(c)}")
    
    # Also clean old test images
    for pattern in ["test_7page_*.jpg", "test_day2_*.jpg", "xhs_a.jpg", "xhs_b.jpg", 
                     "xhs_check.jpg", "xhs_final.jpg", "xhs_final_v2.jpg", "xhs_step*.jpg",
                     "xhs_智能体_*.jpg"]:
        for f in glob.glob(os.path.join(TMP_DIR, pattern)):
            os.remove(f)
            print(f"  🗑️ 清理旧文件 {os.path.basename(f)}")
    
    print(f"\n✅ 归档完成！共 {len(cards)} 张卡片已保存到 {archive_dir}")

if __name__ == "__main__":
    main()

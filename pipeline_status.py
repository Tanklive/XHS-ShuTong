#!/usr/bin/env python3
"""
流水线健康检查 + 状态面板

检查项：
1. Chrome 是否在运行（CDP 端口可达）
2. 登录状态是否有效
3. 内容文件是否存在
4. 配图是否存在
5. 上次发布状态

用法：
    python pipeline_status.py          # 完整检查
    python pipeline_status.py --json   # JSON 输出
    python pipeline_status.py --quick  # 快速检查（不连接 CDP）
"""

import argparse, json, os, sys, time, socket
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

CDP_HOST = os.environ.get("XHS_CDP_HOST", "127.0.0.1")
CDP_PORT = int(os.environ.get("XHS_CDP_PORT", "9222"))
DAILY_FILE = os.path.expanduser("~/shared/daily-xhs-raw.md")
IMAGE_FILE = "/tmp/xhs_daily_image.jpg"
PUBLISH_STATE = os.path.expanduser("~/shared/xhs-publish-state.json")

def check_port(host: str, port: int, timeout: float = 2) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def check_cdp() -> dict:
    """检查 CDP 端口可达性"""
    ok = check_port(CDP_HOST, CDP_PORT)
    return {
        "name": "CDP 端口",
        "status": "ok" if ok else "error",
        "detail": f"{CDP_HOST}:{CDP_PORT} {'可达' if ok else '不可达'}",
        "fix": None if ok else f"启动 Chrome: python chrome_launcher.py --port {CDP_PORT}"
    }

def check_login() -> dict:
    """检查小红书登录状态"""
    try:
        from cdp_publish import XiaohongshuPublisher
        pub = XiaohongshuPublisher(host=CDP_HOST, port=CDP_PORT)
        pub.connect()
        logged_in = pub.check_login()
        pub.disconnect()
        return {
            "name": "登录状态",
            "status": "ok" if logged_in else "error",
            "detail": "已登录" if logged_in else "未登录",
            "fix": None if logged_in else "需手动扫码登录: python cdp_publish.py login"
        }
    except Exception as e:
        return {
            "name": "登录状态",
            "status": "unknown",
            "detail": f"无法检测: {e}",
            "fix": "确认 Chrome 已启动且 CDP 端口正确"
        }

def check_daily_file() -> dict:
    exists = os.path.exists(DAILY_FILE)
    if not exists:
        return {"name":"日报文件","status":"warn","detail":f"不存在: {DAILY_FILE}",
                "fix":"等待每日 cron 生成或手动创建"}
    mtime = datetime.fromtimestamp(os.path.getmtime(DAILY_FILE))
    age_hours = (datetime.now() - mtime).total_seconds() / 3600
    status = "ok" if age_hours < 24 else "warn"
    return {"name":"日报文件","status":status,
            "detail":f"存在 ({age_hours:.1f}小时前更新)",
            "fix":None if age_hours < 24 else "文件可能过期，等待下次 cron"}

def check_image() -> dict:
    exists = os.path.exists(IMAGE_FILE)
    if not exists:
        return {"name":"配图","status":"warn","detail":f"不存在: {IMAGE_FILE}",
                "fix":"等待 cron 下载或手动下载"}
    size_kb = os.path.getsize(IMAGE_FILE) / 1024
    status = "ok" if 50 <= size_kb <= 2048 else "warn"
    return {"name":"配图","status":status,
            "detail":f"存在 ({size_kb:.0f}KB)",
            "fix":None if status=="ok" else "图片大小不符合要求（50KB-2MB）"}

def check_publish_state() -> dict:
    if not os.path.exists(PUBLISH_STATE):
        return {"name":"发布状态","status":"ok","detail":"无待发布","fix":None}
    try:
        with open(PUBLISH_STATE) as f:
            state = json.load(f)
    except:
        return {"name":"发布状态","status":"warn","detail":"状态文件损坏","fix":"删除后重建"}
    status = state.get("status","unknown")
    return {"name":"发布状态","status":"ok" if status=="published" else "info",
            "detail":f"{status} (上次: {state.get('last_publish','未知')})",
            "fix":None}

def check_all(quick: bool = False) -> dict:
    checks = [check_cdp(), check_daily_file(), check_image(), check_publish_state()]
    if not quick:
        checks.insert(1, check_login())
    
    ok_count = sum(1 for c in checks if c["status"] == "ok")
    error_count = sum(1 for c in checks if c["status"] == "error")
    
    return {
        "timestamp": datetime.now().isoformat(),
        "overall": "healthy" if error_count == 0 else "degraded" if error_count < 3 else "broken",
        "ok": ok_count, "errors": error_count,
        "checks": checks
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="XHS 流水线状态")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()
    
    result = check_all(quick=args.quick)
    
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        overall_icon = {"healthy":"🟢","degraded":"🟡","broken":"🔴"}
        print(f"\n{overall_icon.get(result['overall'],'❓')} XHS 流水线: {result['overall']}"
              f"  ({result['ok']}/{len(result['checks'])} 正常)\n")
        for c in result["checks"]:
            icon = {"ok":"✅","warn":"⚠️","error":"❌","info":"ℹ️","unknown":"❓"}
            print(f"  {icon.get(c['status'],'❓')} {c['name']}: {c['detail']}")
            if c.get("fix"): print(f"     → {c['fix']}")
    sys.exit(0 if result["overall"] != "broken" else 1)

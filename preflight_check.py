#!/usr/bin/env python3
"""
小红书发布前预检脚本
检查：Chrome 运行状态、登录状态、网络连通性、Cookie 有效性
"""
import json, sys, time, requests
import websockets.sync.client as ws_client

CHROME_CDP = "http://127.0.0.1:9222"
TIMEOUT = 10


def check_chrome_running():
    """检查 Chrome 调试端口是否可达"""
    try:
        resp = requests.get(f"{CHROME_CDP}/json", timeout=5)
        pages = resp.json()
        return True, pages
    except Exception as e:
        return False, str(e)


def check_network():
    """检查基础网络连通性"""
    targets = [
        ("百度", "https://www.baidu.com"),
        ("小红书创作平台", "https://creator.xiaohongshu.com"),
    ]
    results = {}
    for name, url in targets:
        try:
            r = requests.get(url, timeout=10, allow_redirects=True)
            results[name] = f"OK ({r.status_code})"
        except Exception as e:
            results[name] = f"FAIL ({e})"
    return results


def check_login_status(pages):
    """检查是否有已登录的 SPA 页面渲染"""
    for p in pages:
        url = p.get("url", "")
        if "creator.xiaohongshu.com" in url and "login" not in url:
            try:
                ws = ws_client.connect(p["webSocketDebuggerUrl"], close_timeout=3)
                ws.send(json.dumps({
                    "id": 1, "method": "Runtime.evaluate",
                    "params": {
                        "expression": "JSON.stringify({app: document.querySelector('#app')?.children.length || 0, title: document.title, hasLoginForm: !!document.querySelector('.login-container'), bodyText: document.body.innerText.slice(0, 200)})",
                        "returnByValue": True
                    }
                }))
                r = json.loads(ws.recv())
                val = r["result"]["result"]["value"]
                data = json.loads(val)
                ws.close()
                
                if data["app"] > 0 and not data["hasLoginForm"]:
                    return True, f"已登录，SPA 正常 (app={data['app']})"
                elif data["hasLoginForm"]:
                    return False, "需要登录（login form 可见）"
                else:
                    return False, f"SPA 未渲染 (app={data['app']})"
            except Exception as e:
                return None, f"检查失败: {e}"
    
    return None, "未找到已登录页面（所有页面都在 login 或其他域名）"


def check_image_file():
    """检查配图文件是否存在且格式正确"""
    import os
    path = "/tmp/xhs_daily_image.jpg"
    if not os.path.exists(path):
        return False, "配图文件不存在"
    size = os.path.getsize(path)
    if size < 50 * 1024:
        return False, f"配图过小 ({size}B)"
    if size > 2 * 1024 * 1024:
        return False, f"配图过大 ({size}B)"
    return True, f"配图正常 ({size/1024:.0f}KB)"


def check_content_file():
    """检查正文文件是否存在且非空"""
    import os
    path = os.path.expanduser("~/shared/daily-xhs-raw.md")
    if not os.path.exists(path):
        return False, "正文文件不存在"
    with open(path) as f:
        content = f.read().strip()
    if not content:
        return False, "正文文件为空"
    return True, f"正文 {len(content)} 字"


def main():
    print("=" * 50)
    print("🔍 小红书发布预检")
    print("=" * 50)
    
    all_pass = True
    
    # 1. Chrome
    chrome_ok, pages = check_chrome_running()
    print(f"\n1️⃣ Chrome: {'✅ ' + ('运行中 %d 标签页' % len(pages)) if chrome_ok else '❌ ' + str(pages)}")
    if not chrome_ok:
        all_pass = False
    else:
        # Show relevant tabs
        for p in pages:
            url = p.get("url", "")
            if "creator.xiaohongshu.com" in url:
                print(f"   📄 {p['id'][:12]}... {url[-60:]}")
    
    # 2. Network
    print(f"\n2️⃣ 网络:")
    net_results = check_network()
    for name, status in net_results.items():
        icon = "✅" if "OK" in status else "❌"
        print(f"   {name}: {icon} {status}")
        if "FAIL" in status:
            all_pass = False
    
    # 3. Login
    if chrome_ok:
        print(f"\n3️⃣ 登录状态:")
        login_ok, msg = check_login_status(pages)
        icon = "✅" if login_ok else ("⚠️" if login_ok is None else "❌")
        print(f"   {icon} {msg}")
        if not login_ok:
            all_pass = False
    
    # 4. Content files
    print(f"\n4️⃣ 内容文件:")
    img_ok, img_msg = check_image_file()
    print(f"   配图: {'✅' if img_ok else '❌'} {img_msg}")
    if not img_ok:
        all_pass = False
    
    content_ok, content_msg = check_content_file()
    print(f"   正文: {'✅' if content_ok else '❌'} {content_msg}")
    if not content_ok:
        all_pass = False
    
    # 5. Summary
    print(f"\n{'='*50}")
    if all_pass:
        print("✅ 全部通过，可以发布")
    else:
        print("❌ 存在阻塞项，需要修复后再发布")
        print("\n应急预案：")
        print("  1. 网络异常 → 等 5 分钟重试 preflight")
        print("  2. 未登录 → 手机扫码登录（短信验证码备用）")
        print("  3. SPA 不渲染 → 从 home 页 location.href 跳转")
        print("  4. 配图缺失 → 用上次缓存的图或默认图")
        print("  5. 正文缺失 → 重新跑 cron 生成")
    print("=" * 50)
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

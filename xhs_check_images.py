#!/usr/bin/env python3
"""检测小红书编辑器中实际图片数量"""
import json, asyncio, websockets, urllib.request


async def check():
    try:
        resp = urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=5)
        pages = json.loads(resp.read())
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return

    counts = []
    for p in pages:
        if 'publish' not in p.get('url', '').lower():
            continue
        try:
            async with websockets.connect(p['webSocketDebuggerUrl'], max_size=10*1024*1024) as ws:
                await ws.send(json.dumps({
                    'id': 1, 'method': 'Runtime.evaluate',
                    'params': {'expression': 'document.querySelectorAll(".format-img").length', 'returnByValue': True}
                }))
                r = json.loads(await ws.recv())
                c = r.get('result', {}).get('result', {}).get('value', 0)
                counts.append({"url": p['url'][:60], "count": c})
        except Exception:
            continue

    print(json.dumps({"pages": counts}))


asyncio.run(check())

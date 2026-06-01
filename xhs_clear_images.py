#!/usr/bin/env python3
"""清空小红书编辑器中所有已上传图片"""
import json, asyncio, websockets, urllib.request

DELETE_EXPR = (
    '(()=>{'
    'const img=document.querySelector(".format-img");'
    'if(!img)return JSON.stringify({e:"none"});'
    'const c=img.closest(".img-container")||img.parentElement;'
    'if(!c)return JSON.stringify({e:"no_c"});'
    'const m=c.querySelector(".mask");'
    'if(m)m.style.display="block";'
    'const b=c.querySelector(".close-btn");'
    'if(!b)return JSON.stringify({e:"no_btn"});'
    'const r=b.getBoundingClientRect();'
    'return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2})'
    '})()'
)
COUNT_EXPR = 'document.querySelectorAll(".format-img").length'


async def clear():
    try:
        resp = urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=5)
        pages = json.loads(resp.read())
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return

    pages_with_images = []
    for p in pages:
        if 'publish/publish' not in p.get('url', ''):
            continue
        try:
            async with websockets.connect(p['webSocketDebuggerUrl'], max_size=10*1024*1024) as ws:
                await ws.send(json.dumps({'id': 0, 'method': 'Runtime.evaluate',
                    'params': {'expression': COUNT_EXPR, 'returnByValue': True}}))
                r = json.loads(await ws.recv())
                c = r.get('result', {}).get('result', {}).get('value', 0)
                if c > 0:
                    pages_with_images.append(p['webSocketDebuggerUrl'])
        except Exception:
            continue

    if not pages_with_images:
        print(json.dumps({"deleted": 0, "remaining": 0}))
        return

    total_deleted = 0
    for ws_url in pages_with_images:
        async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
            deleted = 0
            for i in range(20):
                await ws.send(json.dumps({'id': i*2+1, 'method': 'Runtime.evaluate',
                    'params': {'expression': DELETE_EXPR, 'returnByValue': True}}))
                r = json.loads(await ws.recv())
                v = r.get('result', {}).get('result', {}).get('value', '{}')
                try:
                    pos = json.loads(v)
                except Exception:
                    break
                if 'e' in pos or not pos.get('x'):
                    break
                x, y = pos['x'], pos['y']
                for t in ['mouseMoved', 'mousePressed', 'mouseReleased']:
                    await ws.send(json.dumps({'id': i*2+2, 'method': 'Input.dispatchMouseEvent',
                        'params': {'type': t, 'x': x, 'y': y, 'button': 'left',
                                   'clickCount': 0 if t == 'mouseMoved' else 1}}))
                    await asyncio.sleep(0.1)
                deleted += 1
                total_deleted += 1
                await asyncio.sleep(0.5)

            await ws.send(json.dumps({'id': 999, 'method': 'Runtime.evaluate',
                'params': {'expression': COUNT_EXPR, 'returnByValue': True}}))
            r = json.loads(await ws.recv())
            remaining = r.get('result', {}).get('result', {}).get('value', 0)

    print(json.dumps({"deleted": total_deleted, "remaining": remaining}))


asyncio.run(clear())

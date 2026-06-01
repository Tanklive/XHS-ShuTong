#!/usr/bin/env python3.13
"""
AI 生图工具 — 三平台统一接口
================================
支持硅基流动、即梦（火山引擎）、可灵（快手）三个免费生图平台。

用法:
    # 硅基流动（最简单，推荐首选）
    python3.13 ai_image_gen.py --platform siliconflow --prompt "赛博朋克城市" --size 768x1024

    # 即梦（火山引擎）
    python3.13 ai_image_gen.py --platform jimeng --prompt "赛博朋克城市" --size 1328x1328

    # 可灵（快手）
    python3.13 ai_image_gen.py --platform kling --prompt "赛博朋克城市" --aspect 3:4

    # 自动选平台（按优先级）
    python3.13 ai_image_gen.py --prompt "赛博朋克城市"

    # 保存到本地
    python3.13 ai_image_gen.py --prompt "赛博朋克城市" --save /tmp/ai_gen.jpg
"""

import sys
import os
import json
import time
import hashlib
import hmac
import base64
import urllib.request
import urllib.parse
import urllib.error
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


# ═══ 配置文件路径 ═══
ENV_DIR = Path.home() / ".openclaw" / "workspace"
SILICONFLOW_KEY_FILE = ENV_DIR / ".env.siliconflow"
VOLCENGINE_ENV_FILE = ENV_DIR / ".env.volcengine"
KLING_KEY_FILE = ENV_DIR / ".env.kling"
JIMENG_ARK_FILE = ENV_DIR / ".env.jimeng"


def _load_env_file(path: Path) -> dict:
    """读取 .env 文件"""
    env = {}
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


# ════════════════════════════════════════════════════════════
# 平台 1：硅基流动 (SiliconFlow) — 最简单
# ════════════════════════════════════════════════════════════

def _siliconflow_generate(prompt: str, size: str = "768x1024",
                           model: str = "Kwai-Kolors/Kolors",
                           api_key: str = "", save_path: str = "") -> dict:
    """
    硅基流动生图（OpenAI 兼容格式）
    免费模型: stabilityai/stable-diffusion-3.5-large (100张/月)
    """
    if not api_key:
        env = _load_env_file(SILICONFLOW_KEY_FILE)
        api_key = env.get("SILICONFLOW_API_KEY", os.environ.get("SILICONFLOW_API_KEY", ""))

    if not api_key:
        return {"success": False, "error": "需要 SiliconFlow API Key",
                "setup": f"创建文件 {SILICONFLOW_KEY_FILE} 写入 SILICONFLOW_API_KEY=sk-xxx"}

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "image_size": size,
        "batch_size": 1,
        "num_inference_steps": 30,
    }).encode()

    req = urllib.request.Request(
        "https://api.siliconflow.cn/v1/images/generations",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        images = result.get("images", result.get("data", []))

        if not images:
            return {"success": False, "error": "未返回图片"}

        img_url = images[0].get("url", "")
        if not img_url:
            return {"success": False, "error": "图片 URL 为空"}

        # 下载图片
        if save_path:
            img_data = urllib.request.urlopen(img_url, timeout=30).read()
            with open(save_path, "wb") as f:
                f.write(img_data)
            return {"success": True, "path": save_path, "platform": "siliconflow"}

        return {"success": True, "url": img_url, "platform": "siliconflow"}

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        return {"success": False, "error": f"HTTP {e.code}: {body}", "platform": "siliconflow"}
    except Exception as e:
        return {"success": False, "error": str(e), "platform": "siliconflow"}


# ════════════════════════════════════════════════════════════
# 平台 2：即梦 (火山引擎) — 需要 AK/SK 签名
# ════════════════════════════════════════════════════════════

def _volcengine_sign(ak: str, sk: str, method: str, host: str,
                      path: str, query: dict, body: str) -> dict:
    """火山引擎 V4 签名"""
    now = datetime.now(timezone.utc)
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    short_date = now.strftime("%Y%m%d")

    body_hash = hashlib.sha256(body.encode()).hexdigest()

    canonical_headers = f"content-type:application/json\nhost:{host}\nx-content-sha256:{body_hash}\nx-date:{x_date}\n"
    signed_headers = "content-type;host;x-content-sha256;x-date"

    sorted_query = sorted(query.items())
    canonical_query = "&".join([f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted_query])

    canonical_request = f"{method}\n{path}\n{canonical_query}\n{canonical_headers}\n{signed_headers}\n{body_hash}"

    credential_scope = f"{short_date}/cn-north-1/cv/request"
    string_to_sign = f"HMAC-SHA256\n{x_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"

    k_date = hmac.new(sk.encode(), short_date.encode(), hashlib.sha256).digest()
    k_region = hmac.new(k_date, b"cn-north-1", hashlib.sha256).digest()
    k_service = hmac.new(k_region, b"cv", hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b"request", hashlib.sha256).digest()
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = f"HMAC-SHA256 Credential={ak}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

    return {
        "Authorization": authorization,
        "X-Date": x_date,
        "X-Content-Sha256": body_hash,
        "Content-Type": "application/json",
        "Host": host
    }


def _jimeng_generate(prompt: str, width: int = 2048, height: int = 2048,
                      api_key: str = "", save_path: str = "") -> dict:
    """
    即梦 AI 生图（通过火山引擎 Ark API）
    需要 Ark API Key + Endpoint ID
    """
    ark_key = api_key
    endpoint = ""
    if not ark_key:
        env = _load_env_file(JIMENG_ARK_FILE)
        ark_key = env.get("JIMENG_ARK_KEY", os.environ.get("JIMENG_ARK_KEY", ""))
        endpoint = env.get("JIMENG_ENDPOINT", os.environ.get("JIMENG_ENDPOINT", ""))
    if not endpoint:
        env = _load_env_file(JIMENG_ARK_FILE)
        endpoint = env.get("JIMENG_ENDPOINT", os.environ.get("JIMENG_ENDPOINT", ""))

    if not ark_key or not endpoint:
        return {"success": False, "error": "需要即梦 Ark API Key + Endpoint",
                "setup": f"创建文件 {JIMENG_ARK_FILE}\n写入:\nJIMENG_ARK_KEY=ark-xxx\nJIMENG_ENDPOINT=ep-xxx"}

    # 确保尺寸满足最小要求（>=3686400像素）
    min_pixels = 3686400
    if width * height < min_pixels:
        ratio = (min_pixels / (width * height)) ** 0.5
        width = int(width * ratio)
        height = int(height * ratio)

    payload = json.dumps({
        "model": endpoint,
        "prompt": prompt,
        "size": f"{width}x{height}",
        "n": 1,
    }).encode()

    req = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ark_key}"
        }
    )

    try:
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read().decode())
        images = result.get("data", [])

        if not images or not images[0].get("url"):
            return {"success": False, "error": "未返回图片", "platform": "jimeng"}

        img_url = images[0]["url"]
        img_data = urllib.request.urlopen(img_url, timeout=30).read()

        if save_path:
            with open(save_path, "wb") as f:
                f.write(img_data)
            return {"success": True, "path": save_path, "platform": "jimeng"}

        return {"success": True, "url": img_url, "platform": "jimeng"}

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        return {"success": False, "error": f"HTTP {e.code}: {body}", "platform": "jimeng"}
    except Exception as e:
        return {"success": False, "error": str(e), "platform": "jimeng"}


# ════════════════════════════════════════════════════════════
# 平台 3：可灵 (快手) — JWT 签名
# ════════════════════════════════════════════════════════════

def _kling_generate(prompt: str, aspect: str = "3:4",
                     api_key: str = "", save_path: str = "") -> dict:
    """
    可灵 AI 生图（OpenAI 兼容格式）
    需要可灵 API access_key + secret_key → JWT
    """
    access_key = api_key
    secret_key = ""
    if not access_key:
        env = _load_env_file(KLING_KEY_FILE)
        access_key = env.get("KLING_ACCESS_KEY", os.environ.get("KLING_ACCESS_KEY", ""))
        secret_key = env.get("KLING_SECRET_KEY", os.environ.get("KLING_SECRET_KEY", ""))

    if not access_key or not secret_key:
        return {"success": False, "error": "需要可灵 API Key",
                "setup": f"创建文件 {KLING_KEY_FILE}\n写入:\nKLING_ACCESS_KEY=xxx\nKLING_SECRET_KEY=xxx"}

    # 生成 JWT
    try:
        import jwt as pyjwt  # PyJWT
        now = int(time.time())
        token = pyjwt.encode(
            {"iss": access_key, "exp": now + 1800, "nbf": now - 5},
            secret_key, algorithm="HS256"
        )
    except ImportError:
        # 手动构造 JWT（不依赖 PyJWT）
        import struct

        def _b64url(data):
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        def _jwt_encode(header, payload, secret):
            h = _b64url(json.dumps(header).encode())
            p = _b64url(json.dumps(payload).encode())
            sig_input = f"{h}.{p}".encode()
            sig = hmac.new(secret.encode(), sig_input, hashlib.sha256).digest()
            return f"{h}.{p}.{_b64url(sig)}"

        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": access_key,
            "exp": now + 1800,
            "nbf": now - 5
        }
        token = _jwt_encode(header, payload, secret_key)

    host = "api.klingai.com"

    # 提交任务
    body = json.dumps({
        "model": "Kling-V2.1",
        "prompt": prompt,
        "n": 1,
        "aspect_ratio": aspect,
        "resolution": "1k"
    })

    try:
        req = urllib.request.Request(
            f"https://{host}/v1/images/generations",
            data=body.encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        images = result.get("data", [])

        if not images:
            return {"success": False, "error": "未返回图片", "platform": "kling"}

        img_url = images[0].get("url", "")
        if not img_url:
            return {"success": False, "error": "图片 URL 为空", "platform": "kling"}

        if save_path:
            img_data = urllib.request.urlopen(img_url, timeout=30).read()
            with open(save_path, "wb") as f:
                f.write(img_data)
            return {"success": True, "path": save_path, "platform": "kling"}

        return {"success": True, "url": img_url, "platform": "kling"}

    except Exception as e:
        return {"success": False, "error": str(e), "platform": "kling"}


# ════════════════════════════════════════════════════════════
# 统一入口
# ════════════════════════════════════════════════════════════

PLATFORM_PRIORITY = ["siliconflow", "jimeng", "kling"]

def generate(prompt: str, platform: str = "auto",
             size: str = "768x1024", aspect: str = "3:4",
             save_path: str = "") -> dict:
    """
    统一生图接口。

    Args:
        prompt: 生图提示词
        platform: 平台名 (siliconflow/jimeng/kling/auto)
        size: 图片尺寸 (硅基流动/即梦用)
        aspect: 宽高比 (可灵用)
        save_path: 保存路径（不填则只返回 URL）

    Returns:
        {"success": bool, "url"|"path": str, "platform": str, "error"?: str}
    """
    if not save_path:
        save_path = "/tmp/ai_generated.jpg"

    if platform == "auto":
        # 检查哪些平台有 key，按优先级选
        for p in PLATFORM_PRIORITY:
            env_file = {
                "siliconflow": SILICONFLOW_KEY_FILE,
                "jimeng": JIMENG_ARK_FILE,
                "kling": KLING_KEY_FILE,
            }[p]
            env = _load_env_file(env_file)
            if p == "siliconflow" and env.get("SILICONFLOW_API_KEY"):
                platform = p; break
            elif p == "jimeng" and env.get("JIMENG_ARK_KEY"):
                platform = p; break
            elif p == "kling" and env.get("KLING_ACCESS_KEY"):
                platform = p; break
        else:
            return {"success": False, "error": "没有配置任何平台的 API Key",
                    "setup": f"至少创建一个配置文件:\n"
                             f"  {SILICONFLOW_KEY_FILE} (推荐，最简单)\n"
                             f"  {JIMENG_ARK_FILE}\n"
                             f"  {KLING_KEY_FILE}"}

    if platform == "siliconflow":
        return _siliconflow_generate(prompt, size=size, save_path=save_path)
    elif platform == "jimeng":
        return _jimeng_generate(prompt, save_path=save_path)
    elif platform == "kling":
        return _kling_generate(prompt, aspect=aspect, save_path=save_path)
    else:
        return {"success": False, "error": f"未知平台: {platform}"}


def main():
    parser = argparse.ArgumentParser(description="AI 生图工具 — 三平台统一接口")
    parser.add_argument("--prompt", required=True, help="生图提示词")
    parser.add_argument("--platform", default="auto", choices=["auto", "siliconflow", "jimeng", "kling"])
    parser.add_argument("--size", default="768x1024", help="图片尺寸 WxH")
    parser.add_argument("--aspect", default="3:4", help="宽高比 (可灵)")
    parser.add_argument("--save", default="/tmp/ai_generated.jpg", help="保存路径")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = generate(args.prompt, args.platform, args.size, args.aspect, args.save)
    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()

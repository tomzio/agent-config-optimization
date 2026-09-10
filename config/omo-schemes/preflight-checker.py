#!/usr/bin/env python3
"""
Pre-flight 配额检查器
在 Agent 调用前检查 coding-plan 配额，耗尽时自动切换到下一优先级 provider
可集成到 OpenCode 的 pre-command hook 或自定义命令中
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "opencode" / "opencode.json"
QUOTA_CACHE = Path.home() / ".cache" / "opencode" / "quota-cache.json"
CACHE_TTL = 300  # 5分钟缓存

def load_config():
    with open(CONFIG_PATH, "r") as f:
        content = f.read()
    # 简单去注释（实际建议用 jsonc 解析器）
    import re
    content = re.sub(r'^\s*//.*$', '', content, flags=re.M)
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    return json.loads(content)

def check_coding_plan_quota(api_key: str, base_url: str) -> dict:
    """调用 Ark API 检查配额（需根据实际 API 调整端点）"""
    try:
        # 尝试常见的配额查询端点
        endpoints = [
            f"{base_url}/billing/usage",
            f"{base_url}/usage",
            f"{base_url}/quota",
        ]
        headers = {"Authorization": f"Bearer {api_key}"}
        for ep in endpoints:
            try:
                resp = requests.get(ep, headers=headers, timeout=10)
                if resp.status_code == 200:
                    return {"available": True, "data": resp.json()}
            except Exception:
                continue
        # 无专用端点时，尝试发起一个最小请求探测
        test_resp = requests.post(
            f"{base_url}/chat/completions",
            headers={**headers, "Content-Type": "application/json"},
            json={"model": "ark-code-latest", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1},
            timeout=15,
        )
        if test_resp.status_code == 429:
            return {"available": False, "reason": "429 rate limited"}
        if test_resp.status_code == 200:
            return {"available": True, "data": {"test": "ok"}}
        return {"available": False, "reason": f"HTTP {test_resp.status_code}"}
    except Exception as e:
        return {"available": False, "reason": str(e)}

def get_cached_quota():
    if QUOTA_CACHE.exists():
        try:
            data = json.loads(QUOTA_CACHE.read_text())
            if time.time() - data.get("ts", 0) < CACHE_TTL:
                return data.get("available", True)
        except Exception:
            pass
    return None

def set_cached_quota(available: bool):
    QUOTA_CACHE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_CACHE.write_text(json.dumps({"available": available, "ts": time.time()}))

def main():
    config = load_config()
    cp = config.get("provider", {}).get("coding-plan", {})
    options = cp.get("options", {})
    api_key = options.get("apiKey") or os.getenv("ARK_API_KEY")
    base_url = options.get("baseURL", "https://ark.cn-beijing.volces.com/api/coding/v3")

    if not api_key:
        print("⚠️  未找到 ARK_API_KEY，跳过配额检查")
        sys.exit(0)

    # 优先读缓存
    cached = get_cached_quota()
    if cached is not None:
        if not cached:
            print("❌ 缓存显示配额耗尽，建议切换方案")
            sys.exit(1)
        else:
            print("✅ 缓存显示配额充足")
            sys.exit(0)

    # 实时检查
    result = check_coding_plan_quota(api_key, base_url)
    set_cached_quota(result["available"])

    if result["available"]:
        print("✅ 配额检查通过")
        sys.exit(0)
    else:
        print(f"❌ 配额耗尽或异常: {result.get('reason')}")
        print("💡 建议：运行 `python switch.py switch 1` 切换到免费优先方案")
        sys.exit(1)

if __name__ == "__main__":
    main()
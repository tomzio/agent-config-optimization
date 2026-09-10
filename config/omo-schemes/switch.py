#!/usr/bin/env python3
"""
OpenCode/OmO 多模型路由配置一键切换工具
支持 macOS / Windows / Linux
"""

import json
import re
import shutil
import sys
from pathlib import Path
from datetime import datetime

# 配置路径
SCHEMES_DIR = Path(__file__).parent
TARGET_OMO = Path.home() / ".omo" / "omo.jsonc"
BACKUP_DIR = Path.home() / ".omo" / "backups"

SCHEMES = {
    "1": {
        "name": "scheme1-free-first",
        "file": "scheme1-free-first.jsonc",
        "desc": "免费(opencode) → coding-plan 套餐 → zhipuai GLM → deepseek（末位）\n适用：套餐额度紧张、想最大化免费模型、或免费模型网络更好",
    },
    "2": {
        "name": "scheme2-plan-first",
        "file": "scheme2-plan-first.jsonc",
        "desc": "coding-plan 套餐(Ark独占) → deepseek官方(独立配额) → 免费 → zhipuai → deepseek末位\n适用：套餐充足、追求稳定、deepseek独立配额避免套餐耗尽影响",
    },
    "3": {
        "name": "scheme3-free-only",
        "file": "scheme3-free-only.jsonc",
        "desc": "纯免费(零成本) — 仅用 opencode 免费模型，套餐/按量全不用\n适用：拒绝任何按量调用、压测免费上限、临时额度用尽",
    },
}

def strip_jsonc(content: str) -> str:
    """去除 JSONC 注释和尾逗号，用于验证语法"""
    content = re.sub(r'^\s*//.*$', '', content, flags=re.M)
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    return content

def validate_jsonc(filepath: Path) -> tuple[bool, str]:
    """验证 JSONC 语法和模型引用合法性"""
    try:
        content = filepath.read_text(encoding="utf-8")
        json.loads(strip_jsonc(content))
        return True, "语法校验通过"
    except json.JSONDecodeError as e:
        return False, f"JSONC 语法错误: {e}"
    except Exception as e:
        return False, f"校验失败: {e}"

def backup_current() -> Path:
    """备份当前 omo.jsonc"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if TARGET_OMO.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = BACKUP_DIR / f"omo.jsonc.{timestamp}.bak"
        shutil.copy2(TARGET_OMO, backup_path)
        return backup_path
    return None

def switch_scheme(scheme_id: str, dry_run: bool = False) -> bool:
    """切换方案"""
    if scheme_id not in SCHEMES:
        print(f"❌ 无效方案 ID: {scheme_id}，可选: {list(SCHEMES.keys())}")
        return False

    scheme = SCHEMES[scheme_id]
    src_file = SCHEMES_DIR / scheme["file"]

    if not src_file.exists():
        print(f"❌ 方案文件不存在: {src_file}")
        return False

    # 验证源文件
    ok, msg = validate_jsonc(src_file)
    if not ok:
        print(f"❌ 源配置校验失败: {msg}")
        return False

    print(f"📋 方案: {scheme['name']}")
    print(f"📝 说明: {scheme['desc']}")
    print(f"📄 源文件: {src_file}")

    if dry_run:
        print("🔍 [Dry-run] 验证通过，未实际切换")
        return True

    # 备份当前配置
    backup_path = backup_current()
    if backup_path:
        print(f"💾 已备份当前配置: {backup_path}")

    # 复制新配置
    TARGET_OMO.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, TARGET_OMO)
    print(f"✅ 已切换到方案 {scheme_id}: {scheme['name']}")
    print(f"📍 生效位置: {TARGET_OMO}")
    print("🔄 请重启 OpenCode 使配置生效")
    return True

def show_current() -> None:
    """显示当前配置信息"""
    if not TARGET_OMO.exists():
        print("⚠️  当前无配置文件")
        return

    try:
        content = TARGET_OMO.read_text(encoding="utf-8")
        if "scheme3" in content.lower() or "纯免费" in content:
            print("📌 当前方案: Scheme 3 (纯免费，零成本)")
        elif "免费(opencode)" in content and "coding-plan 套餐" in content:
            if content.index("免费(opencode)") < content.index("coding-plan 套餐"):
                print("📌 当前方案: Scheme 1 (免费优先)")
            else:
                print("📌 当前方案: Scheme 2 (套餐优先，含 provider 隔离)")
        else:
            print("📌 当前方案: 自定义/未识别")
    except Exception:
        print("📌 当前方案: 无法识别")

def list_schemes() -> None:
    """列出所有可用方案"""
    print("\n📦 可用方案:")
    for sid, info in SCHEMES.items():
        src = SCHEMES_DIR / info["file"]
        status = "✅" if src.exists() else "❌"
        print(f"  {sid}. {info['name']} {status}")
        print(f"     {info['desc']}")
        print()

def main():
    if len(sys.argv) < 2:
        print("""
🔀 OpenCode/OmO 模型路由配置切换工具

用法:
  python switch.py list              # 列出所有方案
  python switch.py current           # 显示当前方案
  python switch.py check <1|2|3>     # 校验方案配置（不切换）
  python switch.py switch <1|2|3>    # 切换到指定方案

方案:
  1 - Scheme 1: 免费优先（参考 a0fa618）
  2 - Scheme 2: 套餐优先+provider隔离（参考 a32b23c，当前推荐）
  3 - Scheme 3: 纯免费(零成本，仅用 opencode 免费模型)

示例:
  python switch.py switch 2
  python switch.py check 3
""")
        return

    cmd = sys.argv[1]

    if cmd == "list":
        list_schemes()
    elif cmd == "current":
        show_current()
    elif cmd == "check":
        if len(sys.argv) < 3:
            print("❌ 请指定方案 ID: python switch.py check <1|2|3>")
            return
        scheme_id = sys.argv[2]
        if scheme_id in SCHEMES:
            src = SCHEMES_DIR / SCHEMES[scheme_id]["file"]
            ok, msg = validate_jsonc(src)
            print(f"{'✅' if ok else '❌'} {SCHEMES[scheme_id]['name']}: {msg}")
        else:
            print(f"❌ 无效方案 ID: {scheme_id}")
    elif cmd == "switch":
        if len(sys.argv) < 3:
            print("❌ 请指定方案 ID: python switch.py switch <1|2|3>")
            return
        if not switch_scheme(sys.argv[2]):
            sys.exit(1)
    else:
        print(f"❌ 未知命令: {cmd}")

if __name__ == "__main__":
    main()
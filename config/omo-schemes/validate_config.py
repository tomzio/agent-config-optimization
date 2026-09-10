#!/usr/bin/env python3
"""
OpenCode/OmO 配置格式验证脚本
独立可复用的验证工具，供 install.sh/install.ps1/switch.py 调用

用法:
    python3 validate_config.py <scheme_file>          # 完整验证
    python3 validate_config.py <scheme_file> --syntax # 仅语法检查
    python3 validate_config.py <scheme_file> --models # 仅模型引用检查
    python3 validate_config.py <scheme_file> --variants # 仅 variant 检查
"""

import json
import re
import sys
from pathlib import Path

PROVIDER_MODELS_PATH = Path.home() / ".cache" / "oh-my-opencode" / "provider-models.json"


def strip_jsonc(content: str) -> str:
    """去除 JSONC 注释和尾逗号"""
    content = re.sub(r"^\s*//.*$", "", content, flags=re.M)
    content = re.sub(r",(\s*[}\]])", r"\1", content)
    return content


def load_jsonc(filepath: Path) -> dict:
    """加载并解析 JSONC 文件"""
    content = filepath.read_text(encoding="utf-8")
    return json.loads(strip_jsonc(content))


def load_provider_catalog() -> tuple[set, set]:
    """加载 provider 目录，返回 (所有模型集合, 支持variant的模型集合)"""
    if not PROVIDER_MODELS_PATH.exists():
        raise FileNotFoundError(f"Provider 目录不存在: {PROVIDER_MODELS_PATH}")

    with open(PROVIDER_MODELS_PATH, "r") as f:
        pm = json.load(f)

    catalog = set()
    variant_models = set()
    for provider, models in pm.get("models", {}).items():
        for m in models:
            mid = f"{provider}/{m['id']}"
            catalog.add(mid)
            if m.get("variants"):
                variant_models.add(mid)

    return catalog, variant_models


def extract_refs(data: dict) -> tuple[list, list]:
    """提取所有 model 引用和带 variant 的引用"""
    refs = []
    refs_with_variant = []

    def extract(obj):
        if isinstance(obj, dict):
            if "model" in obj:
                refs.append(obj["model"])
                if "variant" in obj:
                    refs_with_variant.append((obj["model"], obj["variant"]))
            for v in obj.values():
                extract(v)
        elif isinstance(obj, list):
            for v in obj:
                extract(v)

    extract(data)
    return refs, refs_with_variant


def validate_syntax(filepath: Path) -> tuple[bool, str]:
    """1. JSONC 语法验证"""
    try:
        load_jsonc(filepath)
        return True, "JSONC 语法校验通过"
    except json.JSONDecodeError as e:
        return False, f"JSONC 语法错误: {e}"
    except Exception as e:
        return False, f"校验异常: {e}"


def validate_models(filepath: Path) -> tuple[bool, str, int]:
    """2. 模型引用合法性验证"""
    try:
        data = load_jsonc(filepath)
        catalog, _ = load_provider_catalog()
        refs, _ = extract_refs(data)

        missing = [m for m in refs if m not in catalog]
        if missing:
            return False, f"缺失模型 ({len(missing)} 个): " + ", ".join(sorted(set(missing))), 0

        return True, f"模型引用合法性校验通过 ({len(refs)} 个引用)", len(refs)
    except FileNotFoundError:
        return True, "⚠️  无法加载 provider-models.json，跳过模型引用校验", 0
    except Exception as e:
        return False, f"模型引用校验异常: {e}", 0


def validate_variants(filepath: Path) -> tuple[bool, str]:
    """3. Variant 合法性验证"""
    try:
        data = load_jsonc(filepath)
        _, variant_models = load_provider_catalog()
        _, refs_with_variant = extract_refs(data)

        illegal = [(m, v) for m, v in refs_with_variant if m not in variant_models]
        if illegal:
            return False, "非法 variant: " + "; ".join(f"{m} -> variant={v}" for m, v in illegal)

        return True, "Variant 合法性校验通过"
    except FileNotFoundError:
        return True, "⚠️  无法加载 provider-models.json，跳过 variant 校验"
    except Exception as e:
        return False, f"Variant 校验异常: {e}"


def validate_all(filepath: Path) -> tuple[bool, list]:
    """完整验证：语法 + 模型 + variant"""
    results = []

    # 语法
    ok, msg = validate_syntax(filepath)
    results.append(("语法", ok, msg))
    if not ok:
        return False, results

    # 模型引用
    ok, msg, count = validate_models(filepath)
    results.append(("模型引用", ok, msg))
    if not ok:
        return False, results

    # Variant
    ok, msg = validate_variants(filepath)
    results.append(("Variant", ok, msg))
    if not ok:
        return False, results

    return True, results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    mode = "all"
    if len(sys.argv) > 2:
        mode = sys.argv[2].lstrip("-")

    print(f"🔍 验证: {filepath}")
    print(f"模式: {mode}")
    print()

    if mode == "syntax":
        ok, msg = validate_syntax(filepath)
        print(f"{'✅' if ok else '❌'} {msg}")
        sys.exit(0 if ok else 1)

    elif mode == "models":
        ok, msg, count = validate_models(filepath)
        print(f"{'✅' if ok else '❌'} {msg}")
        sys.exit(0 if ok else 1)

    elif mode == "variants":
        ok, msg = validate_variants(filepath)
        print(f"{'✅' if ok else '❌'} {msg}")
        sys.exit(0 if ok else 1)

    else:  # all
        ok, results = validate_all(filepath)
        for name, result, msg in results:
            print(f"{'✅' if result else '❌'} [{name}] {msg}")

        if ok:
            print("\n🎉 所有验证通过")
            sys.exit(0)
        else:
            print("\n💥 验证失败")
            sys.exit(1)


if __name__ == "__main__":
    main()
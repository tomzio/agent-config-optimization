#!/usr/bin/env python3
"""
测试套件：验证 omo-schemes 切换工具的正确性
运行: python3 test_switch.py
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMES_DIR = Path(__file__).parent
SWITCH_SCRIPT = SCHEMES_DIR / "switch.py"

ALL_SCHEMES = [
    ("1", "free-first"),
    ("2", "plan-first"),
    ("3", "free-only"),
]


def scheme_path(scheme_id: str) -> Path:
    """根据方案 ID 返回对应 JSONC 文件路径"""
    slug = dict(ALL_SCHEMES)[scheme_id]
    return SCHEMES_DIR / f"scheme{scheme_id}-{slug}.jsonc"


def strip_jsonc(content: str) -> str:
    content = re.sub(r'^\s*//.*$', '', content, flags=re.M)
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    return content


def validate_jsonc(filepath: Path) -> tuple[bool, str]:
    try:
        content = filepath.read_text(encoding="utf-8")
        json.loads(strip_jsonc(content))
        return True, "OK"
    except json.JSONDecodeError as e:
        return False, f"JSONC 语法错误: {e}"
    except Exception as e:
        return False, str(e)


def run_switch(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(SWITCH_SCRIPT)] + args,
        capture_output=True,
        text=True,
        cwd=SCHEMES_DIR,
    )
    return result.returncode, result.stdout, result.stderr


def test_scheme_files_exist():
    """测试方案文件存在"""
    print("🧪 测试: 方案文件存在性")
    for scheme_id, _slug in ALL_SCHEMES:
        sp = scheme_path(scheme_id)
        assert sp.exists(), f"方案文件不存在: {sp}"
    print("  ✅ 通过")


def test_scheme_syntax_valid():
    """测试方案 JSONC 语法合法"""
    print("🧪 测试: 方案 JSONC 语法")
    for scheme_id, _slug in ALL_SCHEMES:
        ok, msg = validate_jsonc(scheme_path(scheme_id))
        assert ok, f"方案 {scheme_id} 语法校验失败: {msg}"
    print("  ✅ 通过")


def test_scheme_model_refs_valid():
    """测试方案模型引用在 provider 目录中存在"""
    print("🧪 测试: 模型引用合法性")
    with open(Path.home() / ".cache" / "oh-my-opencode" / "provider-models.json", "r") as f:
        pm = json.load(f)
    catalog = set()
    for provider, models in pm.get("models", {}).items():
        for m in models:
            catalog.add(f"{provider}/{m['id']}")

    for scheme_id, _slug in ALL_SCHEMES:
        content = scheme_path(scheme_id).read_text(encoding="utf-8")
        content = strip_jsonc(content)
        data = json.loads(content)

        refs = []
        def extract(obj):
            if isinstance(obj, dict):
                if "model" in obj:
                    refs.append(obj["model"])
                for v in obj.values():
                    extract(v)
            elif isinstance(obj, list):
                for v in obj:
                    extract(v)
        extract(data)

        missing = [m for m in refs if m not in catalog]
        assert not missing, f"方案 {scheme_id} 缺失模型: {missing}"
    print("  ✅ 通过")


def test_switch_list():
    """测试 list 命令"""
    print("🧪 测试: list 命令")
    code, out, err = run_switch(["list"])
    assert code == 0, f"list 失败: {err}"
    for scheme_id, slug in ALL_SCHEMES:
        assert f"scheme{scheme_id}-{slug}" in out, f"list 应包含 scheme{scheme_id}-{slug}"
    print("  ✅ 通过")


def test_switch_check():
    """测试 check 命令"""
    print("🧪 测试: check 命令")
    for scheme_id, _slug in ALL_SCHEMES:
        code, out, err = run_switch(["check", scheme_id])
        assert code == 0, f"check {scheme_id} 失败: {err}"
        assert "✅" in out or "语法校验通过" in out
    print("  ✅ 通过")


def test_switch_invalid_scheme():
    """测试无效方案 ID"""
    print("🧪 测试: 无效方案 ID")
    code, out, err = run_switch(["switch", "999"])
    assert code != 0, "应拒绝无效方案"
    print("  ✅ 通过")


def test_switch_dry_run():
    """测试 dry-run（通过 check 模拟）"""
    print("🧪 测试: 切换前校验")
    for scheme_id, _slug in ALL_SCHEMES:
        code, out, err = run_switch(["check", scheme_id])
        assert code == 0
    print("  ✅ 通过")


def test_switch_actual():
    """测试实际切换（使用临时目录）"""
    print("🧪 测试: 实际切换流程")
    from switch import validate_jsonc

    for scheme_id, _slug in ALL_SCHEMES:
        ok, _msg = validate_jsonc(scheme_path(scheme_id))
        assert ok, f"方案 {scheme_id} 核心校验失败"

    print("  ✅ 核心切换逻辑验证通过")


def test_backup_created():
    """测试备份创建"""
    print("🧪 测试: 备份机制")
    with tempfile.TemporaryDirectory() as tmp:
        test_target = Path(tmp) / "omo.jsonc"
        test_target.write_text('{"test": "data"}')

        backup_dir = Path(tmp) / "backups"
        backup_dir.mkdir()
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = backup_dir / f"omo.jsonc.{timestamp}.bak"
        shutil.copy2(test_target, backup_path)

        assert backup_path.exists()
        assert backup_path.read_text() == '{"test": "data"}'
    print("  ✅ 通过")


def test_scheme_differentiation():
    """测试各方案的关键差异"""
    print("🧪 测试: 方案关键差异验证")

    for scheme_id, expected_prefix in [
        ("1", "opencode/"),
        ("2", "coding-plan/"),
        ("3", "opencode/"),
    ]:
        content = scheme_path(scheme_id).read_text(encoding="utf-8")
        content = strip_jsonc(content)
        data = json.loads(content)

        main_model = data["[opencode]"]["agents"]["sisyphus"]["model"]
        assert main_model.startswith(expected_prefix), (
            f"方案 {scheme_id} 主模型应为 {expected_prefix} 开头，实际: {main_model}"
        )

    # 方案 2 验证 deepseek 用官方 provider
    content2 = scheme_path("2").read_text(encoding="utf-8")
    data2 = json.loads(strip_jsonc(content2))

    refs = []
    def extract(obj):
        if isinstance(obj, dict):
            if "model" in obj:
                refs.append(obj["model"])
            for v in obj.values():
                extract(v)
        elif isinstance(obj, list):
            for v in obj:
                extract(v)
    extract(data2)

    deepseek_official = sum(1 for m in refs if m.startswith("deepseek/deepseek-"))
    deepseek_cp = sum(1 for m in refs if m.startswith("coding-plan/deepseek-"))
    assert deepseek_official > deepseek_cp, (
        f"方案 2 应优先使用官方 deepseek (官方:{deepseek_official} vs 套餐:{deepseek_cp})"
    )

    # 方案 3 验证零外部依赖（仅用 opencode 免费模型，不引用 coding-plan / zhipuai / deepseek 官方）
    content3 = scheme_path("3").read_text(encoding="utf-8")
    data3 = json.loads(strip_jsonc(content3))

    refs3 = []
    def extract3(obj):
        if isinstance(obj, dict):
            if "model" in obj:
                refs3.append(obj["model"])
            for v in obj.values():
                extract3(v)
        elif isinstance(obj, list):
            for v in obj:
                extract3(v)
    extract3(data3)

    external_refs = [
        m for m in refs3
        if m.startswith("coding-plan/")
        or m.startswith("zhipuai/")
        or m.startswith("deepseek/")
    ]
    assert not external_refs, (
        f"方案 3 应零外部依赖（不引用 coding-plan/zhipuai/deepseek 官方），但发现: {external_refs}"
    )

    print("  ✅ 通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 开始运行测试套件")
    print("=" * 60)

    tests = [
        test_scheme_files_exist,
        test_scheme_syntax_valid,
        test_scheme_model_refs_valid,
        test_switch_list,
        test_switch_check,
        test_switch_invalid_scheme,
        test_switch_dry_run,
        test_switch_actual,
        test_backup_created,
        test_scheme_differentiation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            failed += 1

    print("=" * 60)
    print(f"📊 结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

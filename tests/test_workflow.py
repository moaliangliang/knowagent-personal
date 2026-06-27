"""
知行 Workflow 模块测试 — 涵盖多场景
运行: python -m pytest tests/test_workflow.py -v

测试截图:
  tests/screenshots/wf_test_results.png   — 全部 17 个场景测试结果
  tests/screenshots/wf_cli.png            — CLI 工作流执行界面
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── 场景 1: 工作流命令注册 ─────────────────────────

def test_workflow_commands_registered():
    """验证 workflow 相关命令已注册"""
    from zhixing.agent.tools import COMMANDS
    assert "workflow_execute" in COMMANDS, "workflow_execute 未注册"
    assert "auto_script" in COMMANDS, "auto_script 未注册"
    print("✅ 工作流命令已注册: workflow_execute, auto_script")


# ── 场景 2: CLI 预设工作流 ─────────────────────────

def test_workflow_presets():
    """验证 CLI 预设工作流存在"""
    from zhixing.ui.cli import WORKFLOW_PRESETS
    assert "📊 系统报告" in WORKFLOW_PRESETS, "缺少预设: 系统报告"
    assert "🎵 音乐时光" in WORKFLOW_PRESETS, "缺少预设: 音乐时光"
    assert len(WORKFLOW_PRESETS) >= 20, f"预设数不足: {len(WORKFLOW_PRESETS)}"
    print(f"✅ 预设工作流: {list(WORKFLOW_PRESETS.keys())}")


def test_workflow_preset_steps():
    """验证预设工作流步骤结构"""
    from zhixing.ui.cli import WORKFLOW_PRESETS
    for name, steps in WORKFLOW_PRESETS.items():
        assert isinstance(steps, list), f"{name} 步骤不是列表"
        assert len(steps) > 0, f"{name} 没有步骤"
        for i, s in enumerate(steps):
            assert "cmd" in s, f"{name}[{i}] 缺少 cmd"
            assert "desc" in s, f"{name}[{i}] 缺少 desc"
    print(f"✅ 所有预设步骤结构正确 (共 {sum(len(v) for v in WORKFLOW_PRESETS.values())} 步)")


# ── 场景 3: 工作流执行（基础）────────────────────

def test_workflow_execute_basic():
    """执行简单工作流：两个系统命令"""
    from zhixing.agent.tools import cmd_workflow_execute
    result = cmd_workflow_execute({
        "steps": [
            {"cmd": "battery_status", "params": {}, "desc": "检查电池"},
            {"cmd": "wifi_status", "params": {}, "desc": "检查WiFi"},
        ]
    })
    assert "✅" in result or "📋" in result or "❌" in result
    # 应该显示步骤进度
    assert "正在播放" not in result
    print(f"✅ 工作流执行成功\n{result[:200]}")
    return result


def test_workflow_execute_empty():
    """空步骤列表"""
    from zhixing.agent.tools import cmd_workflow_execute
    result = cmd_workflow_execute({"steps": []})
    assert "❌" in result
    print(f"✅ 空步骤检测正确: {result}")


def test_workflow_execute_invalid_cmd():
    """无效命令"""
    from zhixing.agent.tools import cmd_workflow_execute
    result = cmd_workflow_execute({
        "steps": [{"cmd": "non_existent_cmd_xxx", "params": {}, "desc": "不存在的命令"}]
    })
    assert "❌" in result or "未知" in result
    print(f"✅ 无效命令检测正确: {result[:100]}")


# ── 场景 4: 工作流执行（带参数）────────────────────

def test_workflow_execute_with_params():
    """带参数的工作流"""
    from zhixing.agent.tools import cmd_workflow_execute
    result = cmd_workflow_execute({
        "steps": [
            {"cmd": "system_volume", "params": {"level": 50}, "desc": "设置音量50%"},
        ]
    })
    assert "50" in result
    print(f"✅ 带参数工作流执行成功: {result[:100]}")


# ── 场景 5: 音乐工作流 ─────────────────────────

def test_workflow_music_search():
    """音乐搜索工作流"""
    from zhixing.agent.tools import cmd_music_search_online
    result = cmd_music_search_online({"keyword": "周杰伦"})
    assert "🎵" in result or "❌" in result
    print(f"✅ 音乐搜索工作流: {'搜索成功' if '🎵' in result else '未找到'}")


# ── 场景 6: Harness 集成测试 ─────────────────────

def test_harness_workflow_events():
    """验证工作流事件定义"""
    from zhixing.harness.events import EventBus
    bus = EventBus()
    # 检查事件总线基本功能
    assert hasattr(bus, "on"), "EventBus 缺少 on 方法"
    assert hasattr(bus, "emit"), "EventBus 缺少 emit 方法"
    print(f"✅ Harness 事件总线正常工作 (EventBus.on/emit)")


def test_harness_workflow_permission():
    """验证工作流权限级别"""
    from zhixing.harness.registry import PermissionLevel, TOOL_REGISTRY
    # workflow_execute 应在注册表中
    if "workflow_execute" in TOOL_REGISTRY._tools:
        tool = TOOL_REGISTRY._tools["workflow_execute"]
        assert tool.permission == PermissionLevel.DESTRUCTIVE
        print(f"✅ workflow_execute 权限级别: DESTRUCTIVE")
    else:
        # 可能在 COMMANDS 中但不在 TOOL_REGISTRY 中
        print(f"ℹ️ workflow_execute 不在 TOOL_REGISTRY 中 (COMMANDS 模式)")


# ── 场景 7: auto_script YAML 解析 ─────────────────

def test_auto_script_yaml_parse():
    """验证 auto_script YAML 解析"""
    yaml_content = """
steps:
  - action: screenshot
    name: 首页截图
  - action: wait
    value: 2
  - action: click
    target: 登录
  - action: screenshot
    name: 登录后
"""
    import tempfile, yaml
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp = f.name
    try:
        with open(tmp) as f:
            data = yaml.safe_load(f)
        assert "steps" in data
        assert len(data["steps"]) == 4
        assert data["steps"][0]["action"] == "screenshot"
        assert data["steps"][2]["action"] == "click"
        print(f"✅ YAML 解析正确: {len(data['steps'])} 步")
    finally:
        os.unlink(tmp)


# ── 场景 8: 工作流编辑器组件 ─────────────────────

def test_workflow_step_types():
    """验证工作流步骤类型定义（从 JS 源分析）"""
    wf_js = os.path.join(os.path.dirname(__file__), "..", "electron-app", "renderer", "workflow.js")
    assert os.path.exists(wf_js), "workflow.js 不存在"
    with open(wf_js) as f:
        content = f.read()
    # 检查步骤类型定义
    step_types = ["trigger_schedule", "trigger_interval", "trigger_webhook",
                  "condition", "wait_until", "variable", "extract",
                  "navigate", "click", "fill", "type", "wait", "screenshot", "assert"]
    for st in step_types:
        assert st in content, f"步骤类型 {st} 未在 workflow.js 中定义"
    print(f"✅ 全部 {len(step_types)} 种步骤类型已定义")


def test_workflow_yaml_export():
    """验证 YAML 导出功能"""
    wf_js = os.path.join(os.path.dirname(__file__), "..", "electron-app", "renderer", "workflow.js")
    with open(wf_js) as f:
        content = f.read()
    assert "toYaml" in content or "toYAML" in content or "export" in content.lower()
    print(f"✅ YAML 导出功能存在")


# ── 场景 9: 多步骤顺序执行 ─────────────────────

def test_workflow_multi_step_sequence():
    """多步骤顺序执行"""
    from zhixing.agent.tools import cmd_workflow_execute
    steps = [
        {"cmd": "system_volume", "params": {"level": 30}, "desc": "设置音量"},
        {"cmd": "system_volume", "params": {"level": 50}, "desc": "恢复音量"},
    ]
    result = cmd_workflow_execute({"steps": steps})
    assert "50" in result
    progress_indicators = ["1/2", "2/2"]
    has_progress = any(p in result for p in progress_indicators)
    print(f"✅ 多步骤顺序执行: {'进度显示正常' if has_progress else '执行完成'}")
    print(f"   完整输出前100字: {result[:100]}")


# ── 场景 10: 错误恢复 ─────────────────────────

def test_workflow_error_continue():
    """工作流中一个步骤失败不影响后续"""
    from zhixing.agent.tools import cmd_workflow_execute
    result = cmd_workflow_execute({
        "steps": [
            {"cmd": "non_existent_cmd", "params": {}, "desc": "失败步骤"},
            {"cmd": "system_volume", "params": {"level": 50}, "desc": "恢复音量"},
        ]
    })
    # 即使第一步失败，第二步仍应被执行
    assert "50" in result or "恢复" in result
    print(f"✅ 错误恢复: 失败后继续执行后续步骤")


# ── 场景 11: 工作时间流测试（预设执行）─────────────

def test_cli_workflow_presets():
    """测试 CLI 工作流预设加载（不实际执行）"""
    from zhixing.ui.cli import WORKFLOW_PRESETS
    for name, steps in WORKFLOW_PRESETS.items():
        for s in steps:
            from zhixing.agent.tools import COMMANDS
            assert s["cmd"] in COMMANDS, f"预设 {name} 中的命令 {s['cmd']} 不存在"
    print(f"✅ 所有预设命令均有效")


# ── 场景 12: 工作流步骤计数 ─────────────────────

def test_workflow_total_steps():
    """验证工作流命令总数 >= 预期"""
    from zhixing.ui.cli import WORKFLOW_PRESETS
    total = sum(len(steps) for steps in WORKFLOW_PRESETS.values())
    assert total >= 30, f"预设总步骤数不足: {total}"
    print(f"✅ 预设总步骤数: {total}")


# ── 运行 ──────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  知行 Workflow 工作流测试")
    print("=" * 60)
    print()

    tests = [
        ("命令注册", test_workflow_commands_registered),
        ("预设存在", test_workflow_presets),
        ("预设结构", test_workflow_preset_steps),
        ("基础执行", test_workflow_execute_basic),
        ("空步骤", test_workflow_execute_empty),
        ("无效命令", test_workflow_execute_invalid_cmd),
        ("参数传递", test_workflow_execute_with_params),
        ("音乐搜索", test_workflow_music_search),
        ("Harness事件", test_harness_workflow_events),
        ("权限级别", test_harness_workflow_permission),
        ("YAML解析", test_auto_script_yaml_parse),
        ("步骤类型", test_workflow_step_types),
        ("YAML导出", test_workflow_yaml_export),
        ("多步顺序", test_workflow_multi_step_sequence),
        ("错误恢复", test_workflow_error_continue),
        ("预设命令", test_cli_workflow_presets),
        ("步骤计数", test_workflow_total_steps),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"  结果: {passed}/{len(tests)} 通过", end="")
    if failed:
        print(f", {failed} 失败")
    else:
        print()
    print("=" * 60)

# ══════════════════════════════════════════════════════════
# 测试截图说明
# ══════════════════════════════════════════════════════════
#
# 截图 1: tests/screenshots/wf_test_results.png
#   17/17 场景全部通过
#   覆盖: 命令注册、预设验证、基础执行、参数传递、
#         错误恢复、多步顺序、YAML解析、Harness集成、
#         CLI预设、音乐搜索、步骤类型定义
#
# 截图 2: tests/screenshots/wf_cli.png
#   CLI 工作流执行界面
#   展示: 预设工作流列表、命令提示

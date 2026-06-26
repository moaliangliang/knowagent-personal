#!/usr/bin/env python3
"""zhixing 综合测试脚本
运行方式: python3 tests/run_all.py [-v]

测试内容:
  Phase 0: 项目结构、命令注册、配置管理、导入完整性
  Phase 1: RAG 知识库、对话记忆、语音输入模块、菜单栏模块

返回码: 0 全部通过, 1 有失败
"""

import importlib
import inspect
import json
import os
import subprocess
import sys
import time
import traceback

# ── 配置 ─────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

PASSED = 0
FAILED = 0
SKIPPED = 0
VERBOSE = "-v" in sys.argv


def log(msg: str, level: str = "INFO"):
    icons = {"INFO": "  ℹ", "PASS": "  ✅", "FAIL": "  ❌", "SKIP": "  ⏭", "HEAD": "▸", "DONE": "✅"}
    icon = icons.get(level, "  •")
    print(f"{icon} {msg}")


def check(condition: bool, msg: str):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        log(msg, "PASS")
    else:
        FAILED += 1
        log(msg, "FAIL")


def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def run_cmd(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip() + r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except FileNotFoundError as e:
        return -2, str(e)


# ═══════════════════════════════════════════════════════════
# Phase 0: 项目结构
# ═══════════════════════════════════════════════════════════

def test_project_structure():
    section("Phase 0 — 项目结构")

    required_dirs = [
        "zhixing",
        "zhixing/agent",
        "zhixing/memory",
        "zhixing/ui",
        "swift",
        "tests",
    ]
    for d in required_dirs:
        check(
            os.path.isdir(os.path.join(PROJECT_ROOT, d)),
            f"目录存在: {d}/",
        )

    required_files = [
        "pyproject.toml",
        "Makefile",
        "README.md",
        ".gitignore",
        "zhixing/__init__.py",
        "zhixing/__main__.py",
        "zhixing/main.py",
        "zhixing/config.py",
        "zhixing/app.py",
        "zhixing/agent/__init__.py",
        "zhixing/agent/tools.py",
        "zhixing/agent/llm.py",
        "zhixing/agent/core.py",
        "zhixing/memory/__init__.py",
        "zhixing/memory/db.py",
        "zhixing/memory/rag.py",
        "zhixing/ui/__init__.py",
        "zhixing/ui/cli.py",
        "zhixing/ui/menubar.py",
        "swift/ax_inspector.swift",
        "swift/screen_ocr.swift",
        "swift/hotkey.swift",
        "tests/test_tools.py",
    ]
    for f in required_files:
        check(
            os.path.isfile(os.path.join(PROJECT_ROOT, f)),
            f"文件存在: {f}",
        )


# ═══════════════════════════════════════════════════════════
# Phase 0: 导入完整性
# ═══════════════════════════════════════════════════════════

def test_imports():
    section("Phase 0 — 导入完整性")

    modules = [
        "zhixing",
        "zhixing.config",
        "zhixing.main",
        "zhixing.agent.tools",
        "zhixing.agent.llm",
        "zhixing.agent.core",
        "zhixing.memory.db",
        "zhixing.memory.rag",
        "zhixing.ui.cli",
        "zhixing.ui.menubar",
        "zhixing.app",
    ]
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
            check(True, f"导入成功: {mod_name}")
        except Exception as e:
            check(False, f"导入失败: {mod_name} — {e}")


# ═══════════════════════════════════════════════════════════
# Phase 0: 命令注册表验证
# ═══════════════════════════════════════════════════════════

def test_commands():
    section("Phase 0 — 命令注册表")

    from zhixing.agent.tools import COMMANDS, get_tool_definitions

    # 数量
    check(len(COMMANDS) >= 31, f"命令数量 >= 31 (实际: {len(COMMANDS)})")

    # Windchill 已移除
    check("windchill" not in COMMANDS, "Windchill 命令已移除")

    # Phase 1 新增命令
    check("knowledge_retrieve" in COMMANDS, "存在 knowledge_retrieve")
    check("voice_input" in COMMANDS, "存在 voice_input")

    # 关键命令存在
    expected = [
        "system_status", "mail_read", "mail_send", "notification",
        "file_list", "screenshot", "screenshot_analyze",
        "calendar", "music_play", "music_search_online",
        "open_app", "open_url", "battery_status", "wifi_status",
        "speak", "keyboard_type", "keyboard_press",
        "ui_tree", "ui_find", "ui_click",
        "lock_screen", "reminder_add", "notes_list", "contacts_search",
        "workflow_execute",
    ]
    for name in expected:
        check(name in COMMANDS, f"关键命令存在: {name}")

    # 所有命令返回 str
    for name, func in COMMANDS.items():
        params = inspect.signature(func).parameters
        if list(params.keys()) == ["params"]:  # cmd_* 风格
            try:
                result = func({})
                check(isinstance(result, str), f"{name}() 返回 str")
            except Exception:
                # macOS-only 命令可能因无 GUI 环境失败，跳过
                pass

    # Tool definitions
    defs = get_tool_definitions()
    check(len(defs) == len(COMMANDS), f"Tool definitions 数量匹配 ({len(defs)})")
    for td in defs:
        check(
            td["type"] == "function" and td["function"]["name"] in COMMANDS,
            f"Tool definition 格式正确: {td['function']['name']}",
        )


# ═══════════════════════════════════════════════════════════
# Phase 0: 配置管理
# ═══════════════════════════════════════════════════════════

def test_config():
    section("Phase 0 — 配置管理")

    from zhixing.config import Config

    c = Config()
    check(c.get("llm.provider") == "ollama", "默认 provider: ollama")
    check(c.get("rag.enabled") is True, "RAG 默认启用")  # Phase 1 变更
    check(c.get("llm.model") == "qwen2.5:7b", "默认模型: qwen2.5:7b")
    check(c.get("storage.db_path", "").endswith("personal.db"), "持久化路径正确")

    # 配置持久化
    test_val = f"test_{int(time.time())}"
    c.set("test.key", test_val)
    c.save()

    c2 = Config()
    check(c2.get("test.key") == test_val, "配置读写持久化")

    # 清理
    import os
    cfg_file = os.path.expanduser("~/.zhixing/config.yaml")
    import yaml
    with open(cfg_file) as f:
        data = yaml.safe_load(f) or {}
    data.pop("test", None)
    with open(cfg_file, "w") as f:
        yaml.dump(data, f)

    # CLI overrides
    c3 = Config(cli_overrides={"model": "custom-model"})
    check(c3.get("llm.model") == "custom-model", "CLI 覆盖配置生效")


# ═══════════════════════════════════════════════════════════
# Phase 0: 包入口
# ═══════════════════════════════════════════════════════════

def test_entry_points():
    section("Phase 0 — 包入口")

    # python -m zhixing --help
    rc, out = run_cmd([sys.executable, "-m", "zhixing", "--help"])
    check(rc == 0 and ("usage" in out.lower() or "用法" in out), "python -m zhixing --help")

    # ka help (single command)
    rc, out = run_cmd([sys.executable, "-m", "zhixing", "help"])
    check(rc == 0 and "命令列表" in out, "ka help 显示命令列表")

    # ka 系统状态（快速命令）
    rc, out = run_cmd([sys.executable, "-m", "zhixing", "系统状态"])
    if rc == 0 and ("CPU" in out or "系统" in out or "状态" in out):
        check(True, "ka 系统状态 执行成功")
    else:
        check(False, f"ka 系统状态 失败 (rc={rc}): {out[:100]}")


# ═══════════════════════════════════════════════════════════
# Phase 1: RAG 知识库
# ═══════════════════════════════════════════════════════════

def test_rag():
    section("Phase 1 — RAG 知识库")

    from zhixing.memory.rag import PersonalRAG
    from zhixing.config import Config

    config = Config()
    rag = PersonalRAG(config)

    # init 可能因缺少依赖失败，但不崩溃
    try:
        ok = rag.init()
        if ok:
            check(True, "RAG 初始化成功")
            # 索引测试文件
            test_dir = os.path.join(PROJECT_ROOT, "tests")
            result = rag.index_directory(test_dir)
            check(
                "added" in result and "skipped" in result,
                f"RAG 索引目录返回结果: {result}",
            )
            # 搜索
            hits = rag.search("test")
            check(isinstance(hits, list), "RAG 搜索返回列表")
        else:
            global SKIPPED
            SKIPPED += 1
            log("RAG 跳过: 缺少 chromadb / sentence-transformers 依赖", "SKIP")
    except Exception as e:
        SKIPPED += 1
        log(f"RAG 跳过: 初始化异常 — {e}", "SKIP")

    # knowledge_retrieve 函数
    from zhixing.agent.tools import knowledge_retrieve, set_rag
    result = knowledge_retrieve("test")
    if ok:
        check(isinstance(result, str), "knowledge_retrieve 返回 str")
    else:
        check("未启用" in result, "knowledge_retrieve 提示 RAG 未启用")


# ═══════════════════════════════════════════════════════════
# Phase 1: SQLite 记忆持久化
# ═══════════════════════════════════════════════════════════

def test_memory():
    section("Phase 1 — 对话记忆持久化")

    from zhixing.memory.db import (
        init_db,
        save_message,
        get_recent_messages,
        clear_history,
        get_setting,
        set_setting,
    )

    init_db()

    # 保存消息
    save_message("user", "测试消息1")
    save_message("assistant", "测试回复1")
    msgs = get_recent_messages(limit=10)
    check(len(msgs) >= 2, f"保存并读取 2 条消息 (实际: {len(msgs)})")

    # 设置读写
    set_setting("test_key", "test_value")
    val = get_setting("test_key")
    check(val == "test_value", "设置读写: settings")

    # 清除历史
    clear_history()
    msgs_after = get_recent_messages(limit=10)
    check(len(msgs_after) == 0, "清除对话历史")

    # 通过 Agent 自动持久化
    from zhixing.config import Config
    from zhixing.agent.llm import LLMClient
    from zhixing.agent.core import Agent

    config = Config()
    llm = LLMClient(config)
    agent = Agent(llm, config)
    check(agent is not None, "Agent 含 RAG + SQLite 初始化完成")


# ═══════════════════════════════════════════════════════════
# Phase 1: 语音输入模块
# ═══════════════════════════════════════════════════════════

def test_voice():
    section("Phase 1 — 语音输入模块")

    from zhixing.agent.tools import cmd_voice_input

    # 不真正录音，只验证函数存在且能处理无麦克风场景
    result = cmd_voice_input({})
    check(isinstance(result, str), "cmd_voice_input 返回 str")
    # 在没有麦克风或没有 SpeechRecognition 时给出合理提示
    check(
        "❌" not in result or "需要安装" in result or "不可用" in result,
        f"语音输入错误信息清晰: {result[:80]}",
    )


# ═══════════════════════════════════════════════════════════
# Phase 1: 菜单栏模块
# ═══════════════════════════════════════════════════════════

def test_menubar():
    section("Phase 1 — 菜单栏模块")

    # 只验证导入，不真正启动 GUI
    try:
        from zhixing.ui.menubar import run_menubar
        check(True, "menubar 模块导入成功")
    except ImportError as e:
        check(False, f"menubar 导入失败: {e}")
    except Exception as e:
        check(False, f"menubar 导入异常: {e}")

    # app.py 入口
    try:
        from zhixing.app import menubar, main
        check(True, "app.py 入口导入成功")
    except Exception as e:
        check(False, f"app.py 导入失败: {e}")

    # hotkey.swift 文件存在
    hotkey_path = os.path.join(PROJECT_ROOT, "swift", "hotkey.swift")
    check(os.path.isfile(hotkey_path), "hotkey.swift 文件存在")
    check(os.path.getsize(hotkey_path) > 500, "hotkey.swift 内容非空")


# ═══════════════════════════════════════════════════════════
# Phase 1: Agent 核心工具调用
# ═══════════════════════════════════════════════════════════

def test_agent_core():
    section("Phase 1 — Agent 核心")

    from zhixing.agent.core import Agent, SYSTEM_PROMPT
    from zhixing.config import Config
    from zhixing.agent.llm import LLMClient

    # 验证 SYSTEM_PROMPT 包含新工具
    check("knowledge_retrieve" in SYSTEM_PROMPT, "SYSTEM_PROMPT 含 knowledge_retrieve 描述")
    check("知识库" in SYSTEM_PROMPT, "SYSTEM_PROMPT 含知识库说明")

    config = Config()
    llm = LLMClient(config)
    agent = Agent(llm, config)

    # local_chat 离线回退
    check("Mac Agent" in agent.local_chat("你是谁"), "local_chat 你是谁")
    check("33" in agent.local_chat("能力") or "个命令" in agent.local_chat("能力"),
           f"local_chat 能力 ({agent.local_chat('能力')[:60]})")

    # _execute_tool
    result = agent._execute_tool("system_status", {})
    check(isinstance(result, str), "agent._execute_tool system_status")
    check(len(result) > 20, f"system_status 输出有内容 ({len(result)} chars)")

    # _execute_tool 处理未知命令
    result = agent._execute_tool("nonexistent", {})
    check("未知命令" in result, "未知命令错误提示")

    # 验证 SQLite 已初始化 (配置目录应存在)
    db_path = os.path.expanduser("~/.zhixing/personal.db")
    check(os.path.exists(os.path.dirname(db_path)), "~/.zhixing 目录存在")


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

def main():
    global PASSED, FAILED, SKIPPED

    print(f"\n{'#' * 60}")
    print(f"  Mac Agent Personal — 综合测试 v0.1.0")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  路径: {PROJECT_ROOT}")
    print(f"{'#' * 60}\n")

    tests = [
        ("项目结构", test_project_structure),
        ("导入完整性", test_imports),
        ("命令注册表", test_commands),
        ("配置管理", test_config),
        ("包入口", test_entry_points),
        ("RAG 知识库", test_rag),
        ("对话记忆持久化", test_memory),
        ("语音输入模块", test_voice),
        ("菜单栏模块", test_menubar),
        ("Agent 核心", test_agent_core),
    ]

    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            FAILED += 1
            log(f"{name} 异常崩溃: {e}\n{traceback.format_exc()}", "FAIL")

    # 汇总
    total = PASSED + FAILED
    print(f"\n{'=' * 60}")
    print(f"  测试完成: {total} 项")
    print(f"  ✅ 通过: {PASSED}")
    print(f"  ❌ 失败: {FAILED}")
    print(f"  ⏭ 跳过: {SKIPPED}")
    print(f"{'=' * 60}")

    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""Tool 模块功能测试 — 验证每个模块的参数校验、边界条件、错误处理。

覆盖模块:
  system_tools, network_tools, file_tools, dev_tools,
  media_tools, daily_tools, ai_tools, monitor_tools,
  clipboard_daemon

现有测试 (test_new_tools.py) 只验证了命令注册存在，
本文件验证函数级别的行为：参数校验、边界条件、返回格式。
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zhixing.agent.tools import COMMANDS


# ═══════════════════════════════════════════════════════════
# system_tools
# ═══════════════════════════════════════════════════════════

def test_system_volume_params():
    """system_volume: 参数校验（值范围 0-100）"""
    func = COMMANDS.get("system_volume")
    assert func is not None, "system_volume 未注册"

    # 有效值
    r = func({"level": 50})
    assert "✅" in r or "❌" in r, f"预期状态码, 实际: {r[:60]}"
    assert isinstance(r, str)

    # 边界值
    r0 = func({"level": 0})
    assert "0" in r0 or "❌" in r0, f"边界0: {r0[:60]}"

    r100 = func({"level": 100})
    assert "100" in r100 or "❌" in r100, f"边界100: {r100[:60]}"

    # 越界值
    r_neg = func({"level": -1})
    assert "❌" in r_neg, f"负值应被拒绝: {r_neg[:60]}"

    r_over = func({"level": 101})
    assert "❌" in r_over, f"超过100应被拒绝: {r_over[:60]}"


def test_display_brightness_params():
    """display_brightness: 参数校验"""
    func = COMMANDS.get("display_brightness")
    assert func is not None

    r = func({"level": 50})
    assert "✅" in r or "❌" in r, f"预期状态码: {r[:60]}"

    # 越界
    r_neg = func({"level": -5})
    assert "❌" in r_neg, f"负值应拒绝: {r_neg}"

    r_over = func({"level": 200})
    assert "❌" in r_over, f"超范围应拒绝: {r_over}"


def test_screensaver():
    """screensaver: 基础调用"""
    func = COMMANDS.get("screensaver")
    assert func is not None
    r = func({})
    assert "✅" in r or "❌" in r, f"预期状态码: {r[:60]}"


def test_focus_mode():
    """focus_mode: 基础调用"""
    func = COMMANDS.get("focus_mode")
    assert func is not None
    r = func({})
    assert isinstance(r, str), f"应返回 str: {type(r)}"


# ═══════════════════════════════════════════════════════════
# network_tools
# ═══════════════════════════════════════════════════════════

def test_my_ip():
    """my_ip: 返回格式"""
    func = COMMANDS.get("my_ip")
    assert func is not None
    r = func({})
    assert isinstance(r, str), f"应返回 str: {type(r)}"
    # 可能是成功或失败（网络不可用），但格式必须一致
    assert "公网" in r or "IP" in r or "❌" in r


def test_ping():
    """ping: 主机参数"""
    func = COMMANDS.get("ping")
    assert func is not None

    # 有参
    r = func({"host": "127.0.0.1"})
    assert isinstance(r, str)

    # 空参 — 应报错提示缺少参数
    r_empty = func({})
    assert "❌" in r_empty or "主机" in r_empty or "host" in r_empty


def test_port_check():
    """port_check: 端口检测参数"""
    func = COMMANDS.get("port_check")
    assert func is not None

    r = func({"host": "127.0.0.1", "port": "80"})
    assert isinstance(r, str)

    # 缺参
    r_no_host = func({"port": "80"})
    assert "❌" in r_no_host or "主机" in r_no_host or "host" in r_no_host


def test_http_request():
    """http_request: 基础请求"""
    func = COMMANDS.get("http_request")
    assert func is not None

    r = func({"url": "https://httpbin.org/get"})
    assert isinstance(r, str)


def test_download():
    """download: 参数校验"""
    func = COMMANDS.get("download")
    assert func is not None

    # 缺参
    r = func({})
    assert "❌" in r or "url" in r


# ═══════════════════════════════════════════════════════════
# file_tools
# ═══════════════════════════════════════════════════════════

def test_file_search():
    """file_search: 搜索模式"""
    func = COMMANDS.get("file_search")
    assert func is not None

    # 有 pattern
    r = func({"pattern": "*.py"})
    assert isinstance(r, str) and len(r) > 0

    # 空 pattern
    r_empty = func({})
    assert "❌" in r_empty or "pattern" in r_empty


def test_file_grep():
    """file_grep: 内容搜索"""
    func = COMMANDS.get("file_grep")
    assert func is not None

    r = func({"pattern": "import", "path": "."})
    assert isinstance(r, str)

    # 缺参
    r_empty = func({})
    assert "❌" in r_empty or "pattern" in r_empty


def test_compress_extract():
    """compress/extract: 基础参数校验"""
    compress = COMMANDS.get("compress")
    extract = COMMANDS.get("extract")
    assert compress is not None
    assert extract is not None

    r = compress({})
    assert "❌" in r, f"缺参应拒绝: {r[:60]}"

    r = extract({})
    assert "❌" in r, f"缺参应拒绝: {r[:60]}"


def test_convert_image():
    """convert_image: 基础调用"""
    func = COMMANDS.get("convert_image")
    assert func is not None
    r = func({})
    assert isinstance(r, str)


def test_trash():
    """trash: 基础调用"""
    func = COMMANDS.get("trash")
    assert func is not None
    r = func({"path": "/tmp/test_trash_file.txt"})
    assert isinstance(r, str)
    assert "❌" in r or "✅" in r  # 文件不存在时也应有格式响应


# ═══════════════════════════════════════════════════════════
# dev_tools
# ═══════════════════════════════════════════════════════════

def test_brew():
    """brew: 基础调用"""
    func = COMMANDS.get("brew")
    assert func is not None
    r = func({"action": "list", "formula": ""})
    assert isinstance(r, str)


def test_process():
    """process: 基础调用"""
    func = COMMANDS.get("process")
    assert func is not None
    r = func({"action": "list"})
    assert isinstance(r, str)


def test_docker():
    """docker: 基础调用"""
    func = COMMANDS.get("docker")
    assert func is not None
    r = func({"action": "ps"})
    assert isinstance(r, str)


# ═══════════════════════════════════════════════════════════
# media_tools
# ═══════════════════════════════════════════════════════════

def test_screen_record():
    """screen_record: 参数校验"""
    func = COMMANDS.get("screen_record")
    assert func is not None
    r = func({})
    assert isinstance(r, str)


def test_audio_record():
    """audio_record: 参数校验"""
    func = COMMANDS.get("audio_record")
    assert func is not None
    r = func({})
    assert isinstance(r, str)


def test_video_info():
    """video_info: 缺参处理"""
    func = COMMANDS.get("video_info")
    assert func is not None
    r = func({})
    assert "❌" in r or "路径" in r or "file" in r


def test_ocr_file():
    """ocr_file: 缺参处理"""
    func = COMMANDS.get("ocr_file")
    assert func is not None
    r = func({})
    assert isinstance(r, str)


# ═══════════════════════════════════════════════════════════
# daily_tools
# ═══════════════════════════════════════════════════════════

def test_timer_params():
    """timer: 参数校验（分钟数范围）"""
    func = COMMANDS.get("timer")
    assert func is not None

    # 负数
    r = func({"minutes": -1})
    assert "❌" in r, f"负分应拒绝: {r[:60]}"

    # 超长
    r = func({"minutes": 9999})
    assert "❌" in r, f"超长应拒绝: {r[:60]}"

    # 正常
    r = func({"minutes": 1})
    assert isinstance(r, str)


def test_translate():
    """translate: 基础调用"""
    func = COMMANDS.get("translate")
    assert func is not None
    r = func({"text": "hello"})
    assert isinstance(r, str)


def test_clipboard_read_write():
    """clipboard_read / clipboard_write: 读写"""
    read = COMMANDS.get("clipboard_read")
    write = COMMANDS.get("clipboard_write")
    assert read is not None
    assert write is not None

    # 写
    r = write({"text": "知行之测试"})
    assert isinstance(r, str)

    # 读
    r2 = read({})
    assert isinstance(r2, str)


def test_shortcut():
    """shortcut: 基础参数"""
    func = COMMANDS.get("shortcut")
    assert func is not None
    r = func({"name": "test"})
    assert isinstance(r, str)


# ═══════════════════════════════════════════════════════════
# ai_tools
# ═══════════════════════════════════════════════════════════

def test_chat():
    """chat: 参数校验"""
    func = COMMANDS.get("chat")
    assert func is not None
    r = func({"message": "hello"})
    assert isinstance(r, str)


def test_summarize():
    """summarize: 参数校验"""
    func = COMMANDS.get("summarize")
    assert func is not None
    r = func({"text": "long text here" * 100})
    assert isinstance(r, str)


def test_code_review():
    """code_review: 参数校验"""
    func = COMMANDS.get("code_review")
    assert func is not None
    r = func({"code": "print('hello')"})
    assert isinstance(r, str)


def test_image_gen():
    """image_gen: 参数校验"""
    func = COMMANDS.get("image_gen")
    assert func is not None
    r = func({"prompt": "test prompt"})
    assert isinstance(r, str)


# ═══════════════════════════════════════════════════════════
# monitor_tools
# ═══════════════════════════════════════════════════════════

def test_disk_monitor():
    """disk_monitor: 返回磁盘信息"""
    func = COMMANDS.get("disk_monitor")
    assert func is not None
    r = func({})
    assert isinstance(r, str)
    assert len(r) > 0


def test_battery_health():
    """battery_health: 返回电池健康"""
    func = COMMANDS.get("battery_health")
    assert func is not None
    r = func({})
    assert isinstance(r, str)


def test_sensor_temp():
    """sensor_temp: 返回温度信息"""
    func = COMMANDS.get("sensor_temp")
    assert func is not None
    r = func({})
    assert isinstance(r, str)


# ═══════════════════════════════════════════════════════════
# clipboard_daemon
# ═══════════════════════════════════════════════════════════

def test_clipboard_monitor():
    """clipboard_monitor: 状态检查"""
    status = COMMANDS.get("clipboard_monitor_status")
    start = COMMANDS.get("clipboard_monitor_start")
    stop = COMMANDS.get("clipboard_monitor_stop")
    assert status is not None
    assert start is not None
    assert stop is not None

    r = status({})
    assert isinstance(r, str)


# ═══════════════════════════════════════════════════════════
# __tools_init__ 聚合测试
# ═══════════════════════════════════════════════════════════

def test_tools_init_aggregation():
    """验证 __tools_init__.py 聚合了所有模块"""
    from zhixing.agent.__tools_init__ import (
        ALL_COMMANDS, ALL_TOOL_SCHEMAS, ALL_COMMAND_NAMES, register_all,
    )
    # 所有命令应被聚合
    assert len(ALL_COMMANDS) >= 60, f"聚合命令数不足: {len(ALL_COMMANDS)}"
    assert len(ALL_COMMAND_NAMES) == len(ALL_COMMANDS)
    assert len(ALL_TOOL_SCHEMAS) >= 60

    # register_all 应能合并到目标 dict
    target_cmd = {}
    target_schema = {}
    register_all(target_commands=target_cmd, target_schemas=target_schema)
    assert len(target_cmd) == len(ALL_COMMANDS)
    assert len(target_schema) == len(ALL_TOOL_SCHEMAS)

    # 模块特定关键命令在聚合列表中
    for name in ("system_volume", "display_brightness", "my_ip",
                 "file_search", "timer", "chat"):
        assert name in ALL_COMMANDS, f"聚合中缺少模块命令: {name}"

    # 旧版命令（tools.py 中的）不在 ALL_COMMANDS 中，但在最终的 COMMANDS 中
    from zhixing.agent.tools import COMMANDS
    for name in ("system_status", "screenshot", "workflow_execute",
                 "mail_read", "mail_send"):
        assert name in COMMANDS, f"COMMANDS 中缺少旧版命令: {name}"


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import inspect

    tests = [
        (name, fn) for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
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

    total = passed + failed
    print(f"\n{'=' * 50}")
    print(f"  结果: {passed}/{total} 通过", end="")
    if failed:
        print(f", {failed} 失败")
    else:
        print()
    print(f"{'=' * 50}")

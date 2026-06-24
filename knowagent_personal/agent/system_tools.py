"""macOS 系统控制命令模块

亮度、音量、睡眠、关机、重启、屏保、专注模式。
所有 cmd_* 函数统一返回 str（纯文本），格式：
  ✅ 成功信息
  ❌ 错误信息
"""

import subprocess


# ── 工具函数 ─────────────────────────────────────────────

def _run_osa(script: str, timeout: int = 30) -> str:
    """执行 AppleScript 并返回 stdout 去除尾随空格。"""
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if r.returncode != 0:
            return f"❌ osascript 错误: {r.stderr.strip()}"
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return "❌ osascript 执行超时"
    except FileNotFoundError:
        return "❌ osascript 未找到"
    except Exception as e:
        return f"❌ 执行错误: {e}"


def _run_cmd(cmd: list[str], timeout: int = 15) -> str:
    """执行外部命令并返回 stdout 去除尾随空格。"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return f"❌ 命令错误: {r.stderr.strip()}"
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return "❌ 命令执行超时"
    except FileNotFoundError:
        return "❌ 命令未找到"
    except Exception as e:
        return f"❌ 执行错误: {e}"


# ── 亮度 ─────────────────────────────────────────────────

def cmd_display_brightness(params: dict) -> str:
    """设置显示器亮度。level: 亮度 0-100"""
    level = int(params.get("level", 50))
    if level < 0 or level > 100:
        return "❌ 亮度值须为 0-100 的整数"
    try:
        script = (
            f'tell application "System Events"\n'
            f"    repeat with d in every display\n"
            f"        set brightness of d to {level / 100}\n"
            f"    end repeat\n"
            f"end tell"
        )
        _run_osa(script)
        return f"✅ 显示器亮度已设置为 {level}"
    except Exception as e:
        return f"❌ 设置亮度失败: {e}"


# ── 音量 ─────────────────────────────────────────────────

def cmd_system_volume(params: dict) -> str:
    """设置系统音量。level: 音量 0-100"""
    level = int(params.get("level", 50))
    if level < 0 or level > 100:
        return "❌ 音量值须为 0-100 的整数"
    try:
        _run_osa(f"set volume output volume {level}")
        return f"✅ 系统音量已设置为 {level}"
    except Exception as e:
        return f"❌ 设置音量失败: {e}"


# ── 睡眠 ─────────────────────────────────────────────────

def cmd_system_sleep(params: dict) -> str:
    """使 Mac 进入睡眠状态。"""
    try:
        _run_osa('tell application "System Events" to sleep')
        return "✅ 已进入睡眠状态"
    except Exception as e:
        return f"❌ 睡眠失败: {e}"


# ── 关机 ─────────────────────────────────────────────────

def cmd_system_shutdown(params: dict) -> str:
    """关机（需用户确认）。"""
    try:
        _run_osa(
            'tell application "System Events"\n'
            '    display dialog "确定要关机吗？" buttons {"取消", "关机"} default button "关机"\n'
            '    if button returned of result is "关机" then shut down\n'
            "end tell"
        )
        return "✅ 已执行关机"
    except Exception as e:
        return f"❌ 关机失败: {e}"


# ── 重启 ─────────────────────────────────────────────────

def cmd_system_restart(params: dict) -> str:
    """重启（需用户确认）。"""
    try:
        _run_osa(
            'tell application "System Events"\n'
            '    display dialog "确定要重启吗？" buttons {"取消", "重启"} default button "重启"\n'
            '    if button returned of result is "重启" then restart\n'
            "end tell"
        )
        return "✅ 已执行重启"
    except Exception as e:
        return f"❌ 重启失败: {e}"


# ── 屏保 ─────────────────────────────────────────────────

def cmd_screensaver(params: dict) -> str:
    """启动屏幕保护程序。"""
    # 优先使用 open -a ScreenSaverEngine
    result = _run_cmd(["open", "-a", "ScreenSaverEngine"])
    if result.startswith("❌"):
        # 回退方案：通过 System Events 启动
        try:
            _run_osa(
                'tell application "System Events"\n'
                "    start screen saver\n"
                "end tell"
            )
            return "✅ 已启动屏幕保护"
        except Exception as e:
            return f"❌ 启动屏保失败: {e}"
    return "✅ 已启动屏幕保护"


# ── 专注模式（勿扰模式）─────────────────────────────────────

def cmd_focus_mode(params: dict) -> str:
    """切换专注模式（勿扰模式）。mode: on/off"""
    mode = params.get("mode", "on").strip().lower()
    if mode not in ("on", "off"):
        return "❌ mode 须为 'on' 或 'off'"

    # macOS 14+ 使用 shortcuts 运行 Focus 快捷指令
    # 回退方案使用 osascript 切换 Do Not Disturb
    target_state = "true" if mode == "on" else "false"
    try:
        _run_osa(
            f'tell application "System Events"\n'
            f"    tell expose preferences to set do not disturb to {target_state}\n"
            f"end tell"
        )
        label = "开启" if mode == "on" else "关闭"
        return f"✅ 已{label}专注模式"
    except Exception as e:
        label = "开启" if mode == "on" else "关闭"
        return f"❌ {label}专注模式失败: {e}"


def cmd_config(params: dict) -> str:
    """查看或修改配置。
    action=show(默认)/reload/get/set，key=配置路径(如 llm.model)，value=新值"""
    from knowagent_personal.config import Config, CONFIG_FILE

    action = params.get("action", "show")
    cfg = Config()

    if action == "reload":
        cfg.__init__()
        return f"✅ 配置已重新加载: {CONFIG_FILE}"

    if action == "get":
        key = params.get("key", "")
        if not key:
            return "❌ 需要 key 参数，如 llm.model"
        val = cfg.get(key, "未设置")
        # 隐藏敏感字段
        if any(s in key for s in ["password", "api_key", "secret"]):
            val = "****" if val else ""
        return f"  {key} = {val}"

    if action == "set":
        key = params.get("key", "")
        value = params.get("value", "")
        if not key or not value:
            return "❌ 需要 key 和 value 参数"
        cfg.set(key, value)
        cfg.save()
        return f"✅ {key} 已设置为 {value}"

    # show
    raw = cfg.raw
    lines = [f"📋 配置 ({CONFIG_FILE})"]
    def _fmt(d, prefix=""):
        for k, v in d.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                lines.append(f"  {path}/")
                _fmt(v, path)
            else:
                display = str(v)
                if any(s in path.lower() for s in ["password", "api_key", "secret", "key"]):
                    display = "****" if v else ""
                lines.append(f"  {path} = {display}")
    _fmt(raw)
    return "\n".join(lines)


# ── 命令注册 ─────────────────────────────────────────────

COMMANDS: dict = {
    "display_brightness": cmd_display_brightness,
    "system_volume": cmd_system_volume,
    "system_sleep": cmd_system_sleep,
    "system_shutdown": cmd_system_shutdown,
    "system_restart": cmd_system_restart,
    "screensaver": cmd_screensaver,
    "focus_mode": cmd_focus_mode,
    "config": cmd_config,
}

TOOL_SCHEMAS: dict = {
    "display_brightness": {
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "亮度 0-100"},
        },
        "required": ["level"],
    },
    "system_volume": {
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "音量 0-100"},
        },
        "required": ["level"],
    },
    "system_sleep": {
        "type": "object",
        "properties": {},
    },
    "system_shutdown": {
        "type": "object",
        "properties": {},
    },
    "system_restart": {
        "type": "object",
        "properties": {},
    },
    "screensaver": {
        "type": "object",
        "properties": {},
    },
    "focus_mode": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "description": "on 开启，off 关闭"},
        },
        "required": ["mode"],
    },
    "config": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "show(默认)查看配置，reload重载，get获取指定key，set设置key=value",
                "enum": ["show", "reload", "get", "set"],
            },
            "key": {"type": "string", "description": "配置路径，如 llm.model"},
            "value": {"type": "string", "description": "配置值（set 时使用）"},
        },
    },
}

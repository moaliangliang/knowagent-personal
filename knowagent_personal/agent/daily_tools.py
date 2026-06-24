"""日常生产力工具命令模块

计时器、剪贴板历史、翻译、快捷指令。
所有 cmd_* 函数统一返回 str（纯文本），格式：
  ✅ 成功信息
  ❌ 错误信息
  📋 数据/列表信息
"""

import json
import os
import subprocess
import time

from knowagent_personal.agent.keychain import cmd_credential

# ── 常量 ─────────────────────────────────────────────────

_CLIPBOARD_HISTORY_PATH = os.path.expanduser("~/.knowagent/clipboard_history.json")


# ── 工具函数 ─────────────────────────────────────────────

def _read_clipboard_history(limit: int = 10) -> list[dict]:
    """从 ~/.knowagent/clipboard_history.json 读取剪贴板历史。"""
    if not os.path.exists(_CLIPBOARD_HISTORY_PATH):
        return []
    try:
        with open(_CLIPBOARD_HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data[-limit:]
    except (json.JSONDecodeError, OSError):
        return []


def _notify(title: str, message: str) -> None:
    """通过 osascript 显示通知。"""
    script = f'display notification "{message}" with title "{title}" sound name "default"'
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)


def _speak(text: str) -> None:
    """通过 say 命令朗读文本。"""
    subprocess.run(["say", text], capture_output=True, timeout=30)


# ── 命令处理器（全部返回 str）───────────────────────────

def cmd_timer(params: dict) -> str:
    """番茄钟 / 计时器。sleep MINUTES*60 秒后显示通知，可选朗读"时间到"。

    参数:
        minutes (int): 计时分钟数。默认为 5。
        name (str, optional): 计时器名称，默认"番茄钟"。
    """
    minutes = int(params.get("minutes", 5))
    name = params.get("name", "番茄钟")

    if minutes <= 0:
        return "❌ minutes 必须大于 0"
    if minutes > 1440:
        return "❌ minutes 不能超过 1440（24小时）"

    try:
        total_seconds = minutes * 60
        time.sleep(total_seconds)
        _notify(name, "时间到！")
        _speak("时间到")
        return f"✅ [{name}] {minutes} 分钟计时结束，已通知"
    except Exception as e:
        return f"❌ 计时器异常: {e}"


def cmd_clipboard_history(params: dict) -> str:
    """读取剪贴板历史记录。

    参数:
        limit (int, optional): 返回最近几条记录，默认 10。
    """
    limit = min(int(params.get("limit", 10)), 100)

    try:
        history = _read_clipboard_history(limit)
        if not history:
            return "📋 剪贴板历史: (空)"

        lines: list[str] = []
        total = len(history)
        for i, entry in enumerate(history):
            idx = total - i
            content = entry.get("content", entry.get("text", ""))
            timestamp = entry.get("timestamp", entry.get("time", ""))
            if isinstance(content, str):
                # 截断过长内容
                display = content[:120].replace("\n", " ")
                if len(content) > 120:
                    display += "..."
            else:
                display = str(content)[:120]
            ts_str = f" [{timestamp}]" if timestamp else ""
            lines.append(f"  {idx}. {display}{ts_str}")

        total_count = 0
        try:
            with open(_CLIPBOARD_HISTORY_PATH, "r", encoding="utf-8") as f:
                all_data = json.load(f)
            if isinstance(all_data, list):
                total_count = len(all_data)
        except Exception:
            pass

        summary = f"（共 {total_count} 条记录，显示最近 {len(history)} 条）" if total_count > len(history) else f"（共 {len(history)} 条记录）"
        return f"📋 剪贴板历史 {summary}:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ 读取剪贴板历史失败: {e}"


def cmd_translate(params: dict) -> str:
    """文本翻译。使用 MyMemory API。

    参数:
        text (str): 待翻译文本。
        from_ (str, optional): 源语言代码，默认 "auto"。
        to (str, optional): 目标语言代码，默认 "zh"。
    """
    text = params.get("text", params.get("keyword", ""))
    from_lang = params.get("from", "auto")
    to_lang = params.get("to", "zh")

    if not text:
        return "❌ 需要 text 参数"

    # from 是 Python 关键字，params 可能以 "from" 传入
    if "from" not in params and "from_" in params:
        from_lang = params.get("from_", "auto")

    if len(text) > 500:
        return "❌ 文本过长，MyMemory 免费 API 限制 500 字符以内"

    # MyMemory 不支持 auto 检测 — 用启发式判断
    if from_lang == "auto":
        import re as _re
        if _re.search(r'[一-鿿㐀-䶿]', text):
            from_lang = "zh"
            to_lang = to_lang if to_lang != "zh" else "en"
        else:
            from_lang = "en"

    try:
        import urllib.parse
        import urllib.request

        query = urllib.parse.quote(text)
        langpair = f"{from_lang}|{to_lang}"
        url = f"https://api.mymemory.translated.net/get?q={query}&langpair={langpair}"

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("responseStatus") != 200:
            return f"❌ 翻译失败: {data.get('responseDetails', '未知错误')}"

        translated = data.get("responseData", {}).get("translatedText", "")
        match_ratio = data.get("responseData", {}).get("match", "")
        if not translated:
            return "❌ 翻译结果为空"

        detail = f"（匹配度: {match_ratio}）" if match_ratio else ""
        return f"📋 翻译 {from_lang}→{to_lang} {detail}:\n  原文: {text}\n  译文: {translated}"
    except urllib.error.HTTPError as e:
        return f"❌ 翻译 API 请求失败 (HTTP {e.code}): {e.reason}"
    except urllib.error.URLError as e:
        return f"❌ 翻译网络错误: {e.reason}"
    except Exception as e:
        return f"❌ 翻译异常: {e}"


def cmd_shortcut(params: dict) -> str:
    """运行 macOS 快捷指令（Shortcuts.app）。

    参数:
        name (str): 快捷指令名称。
        input (str, optional): 输入文本（通过 --input-path 传入）。
    """
    name = params.get("name", "")
    input_text = params.get("input", params.get("input_", ""))

    if not name:
        return "❌ 需要 name 参数（快捷指令名称）"

    try:
        cmd = ["shortcuts", "run", name]

        # 如果有输入文本，写入临时文件通过 --input-path 传入
        temp_file = None
        if input_text:
            import tempfile
            f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
            f.write(input_text)
            f.close()
            temp_file = f.name
            cmd.extend(["--input-path", temp_file])

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        # 清理临时文件
        if temp_file:
            try:
                os.unlink(temp_file)
            except OSError:
                pass

        if r.returncode != 0:
            stderr = r.stderr.strip()
            if stderr:
                return f"❌ 快捷指令「{name}」执行失败: {stderr}"
            return f"❌ 快捷指令「{name}」执行失败（返回码 {r.returncode}）"

        output = r.stdout.strip()
        if output:
            return f"✅ 快捷指令「{name}」执行成功:\n{output}"
        return f"✅ 快捷指令「{name}」执行成功"
    except FileNotFoundError:
        return "❌ 未找到 shortcuts 命令，请确认 macOS 12.0+ 且安装了快捷指令"
    except subprocess.TimeoutExpired:
        return f"❌ 快捷指令「{name}」执行超时（120 秒）"
    except Exception as e:
        return f"❌ 快捷指令异常: {e}"


# ── 命令注册 ─────────────────────────────────────────────

COMMANDS: dict = {
    "timer": cmd_timer,
    "clipboard_history": cmd_clipboard_history,
    "translate": cmd_translate,
    "shortcut": cmd_shortcut,
    "credential": cmd_credential,
}

TOOL_SCHEMAS: dict = {
    "timer": {
        "type": "object",
        "properties": {
            "minutes": {
                "type": "integer",
                "description": "计时分钟数，默认 5",
                "default": 5,
            },
            "name": {
                "type": "string",
                "description": "计时器名称，默认「番茄钟」",
                "default": "番茄钟",
            },
        },
    },
    "clipboard_history": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "返回最近几条记录，默认 10",
                "default": 10,
            },
        },
    },
    "translate": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "待翻译的文本",
            },
            "from": {
                "type": "string",
                "description": "源语言代码，默认 auto",
                "default": "auto",
            },
            "to": {
                "type": "string",
                "description": "目标语言代码，默认 zh",
                "default": "zh",
            },
        },
        "required": ["text"],
    },
    "shortcut": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "快捷指令名称",
            },
            "input": {
                "type": "string",
                "description": "输入文本（可选，通过 --input-path 传入）",
            },
        },
        "required": ["name"],
    },
    "credential": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作: get(获取密码), set(存储), delete(删除), list(列出所有凭据)",
                "enum": ["get", "set", "delete", "list"],
            },
            "name": {
                "type": "string",
                "description": "凭据名称（account），get/set/delete 需要",
            },
            "password": {
                "type": "string",
                "description": "密码值（action=set 时使用，不传则交互式输入）",
            },
            "service": {
                "type": "string",
                "description": "Keychain 服务名称，默认 knowagent",
            },
        },
        "required": ["action"],
    },
}

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

from zhixing.agent.keychain import cmd_credential

# ── 常量 ─────────────────────────────────────────────────

_CLIPBOARD_HISTORY_PATH = os.path.expanduser("~/.zhixing/clipboard_history.json")


# ── 工具函数 ─────────────────────────────────────────────

def _read_clipboard_history(limit: int = 10) -> list[dict]:
    """从 ~/.zhixing/clipboard_history.json 读取剪贴板历史。"""
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


def _osa_escape(s: str) -> str:
    """Escape string for safe use inside an AppleScript string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _notify(title: str, message: str) -> None:
    """通过 osascript 显示通知。"""
    title = _osa_escape(title)
    message = _osa_escape(message)
    script = f'display notification "{message}" with title "{title}" sound name "default"'
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)


def _speak(text: str) -> None:
    """通过 say 命令朗读文本。"""
    subprocess.run(["say", text], capture_output=True, timeout=30)


# ── 命令处理器（全部返回 str）───────────────────────────

def cmd_timer(params: dict) -> str:
    """番茄钟 / 计时器。打开 GUI 倒计时窗口，支持暂停/继续/取消。

    Community 版: 基础通知计时（阻塞式）
    Pro 版:       GUI 窗口（暂停/继续、进度条、语音提醒）

    参数:
        minutes (int): 计时分钟数。默认为 25（一个番茄）。
        name (str, optional): 计时器名称，默认"番茄钟"。
    """
    minutes = int(params.get("minutes", 25))
    name = params.get("name", "番茄钟")

    if minutes <= 0:
        return "❌ minutes 必须大于 0"
    if minutes > 1440:
        return "❌ minutes 不能超过 1440（24小时）"

    from zhixing.agent.pro import require_pro

    # 尝试 Pro 版（GUI 番茄钟窗口）
    guard = require_pro("enhanced_timer")
    if guard is None:
        # Pro 已激活 或 试用期内 → 使用 GUI 番茄钟
        try:
            from zhixing.ui.timer_window import start_timer
            return start_timer(minutes=minutes, name=name)
        except ImportError:
            pass  # GUI 不可用时回退到基础版
        except Exception as e:
            return f"❌ 计时器异常: {e}"

    # Community 版基础计时（阻塞通知）
    _notify(name, f"{minutes} 分钟倒计时开始")
    import time as _t
    _t.sleep(minutes * 60)
    _notify(name, "时间到！")
    _speak("时间到")
    return f"✅ [{name}] {minutes} 分钟计时结束"


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


# ── Pro 版：剪贴板增强（搜索/筛选/收藏/类型识别） ────────


def _detect_clipboard_type(content: str) -> str:
    """启发式判断剪贴板内容类型。"""
    import re
    if not content:
        return "empty"
    # URL
    if re.match(r'^https?://', content.strip()):
        return "url"
    # 文件路径
    if content.strip().startswith(('/Users/', '/tmp/', '~/')):
        return "file"
    if re.match(r'^[A-Z]:\\', content.strip()):
        return "file"
    # 代码（含缩进 + 常见语法）
    lines = content.split('\n')
    if len(lines) > 1 and any(
        line.startswith(('    ', '\t', 'def ', 'class ', 'import ', 'if ', 'for ', 'while '))
        for line in lines[:5]
    ):
        return "code"
    # JSON
    if content.strip().startswith('{') and content.strip().endswith('}'):
        try:
            json.loads(content)
            return "json"
        except json.JSONDecodeError:
            pass
    return "text"


def cmd_clipboard_pro(params: dict) -> str:
    """📋 Pro 版剪贴板管理 — 搜索/筛选/收藏/预览。

    参数:
        action (str): search | filter | favorite | view | stats | list
        query (str, optional): 搜索关键词（action=search 时）
        id (int, optional): 条目编号（action=view/favorite 时）
        type (str, optional): 筛选类型（action=filter 时）url|file|code|json|text
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("enhanced_clipboard")
    if guard is not None:
        return guard

    action = params.get("action", "list")
    query = params.get("query", "")
    entry_id = params.get("id", None)
    filter_type = params.get("type", "")

    entries = _load_full_history()

    if action == "stats":
        return _clipboard_stats(entries)

    if action == "search":
        if not query:
            return "❌ search 需要 query 参数"
        query_lower = query.lower()
        matched = [
            e for e in entries
            if query_lower in e.get("content", "").lower()
        ]
        return _format_clipboard_results(matched, f"🔍 搜索「{query}」")

    if action == "filter":
        matched = [e for e in entries if _detect_clipboard_type(e.get("content", "")) == filter_type]
        return _format_clipboard_results(matched, f"📋 筛选: {filter_type}")

    if action == "favorite":
        if entry_id is None:
            return "❌ favorite 需要 id 参数"
        return _clipboard_toggle_favorite(entry_id, entries)

    if action == "favorites":
        favs = [e for e in entries if e.get("favorite")]
        return _format_clipboard_results(favs, "⭐ 收藏夹")

    if action == "view":
        if entry_id is None:
            return "❌ view 需要 id 参数"
        return _clipboard_view(entry_id, entries)

    # action == "list" — 增强列表
    return _format_clipboard_results(entries, "📋 剪贴板历史", show_type=True)


def _load_full_history() -> list[dict]:
    """读取全部剪贴板历史（从新到旧）。"""
    try:
        with open(_CLIPBOARD_HISTORY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data[::-1]  # 最新的在前
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return []


def _format_clipboard_results(entries: list, title: str, show_type: bool = False) -> str:
    """格式化剪贴板结果列表。"""
    if not entries:
        return f"{title}: (空)"

    lines = [f"{title}（共 {len(entries)} 条）:"]
    for i, entry in enumerate(entries, 1):
        content = entry.get("content", "")
        ts = entry.get("timestamp_str", entry.get("timestamp", ""))
        fav = " ⭐" if entry.get("favorite") else ""
        ctype = _detect_clipboard_type(content)
        type_tag = f" [{ctype}]" if show_type else ""

        # 预览截断
        display = content[:150].replace("\n", " ")
        if len(content) > 150:
            display += "…"

        ts_str = f" {ts}" if ts else ""
        lines.append(f"  {i}.{type_tag}{fav}{ts_str}")
        lines.append(f"     {display}")

    return "\n".join(lines)


def _clipboard_view(entry_id: int, entries: list) -> str:
    """显示某条剪贴板完整内容。"""
    if entry_id < 1 or entry_id > len(entries):
        return f"❌ 无效编号: {entry_id}"
    entry = entries[entry_id - 1]
    content = entry.get("content", "")
    ts = entry.get("timestamp_str", entry.get("timestamp", ""))
    ctype = _detect_clipboard_type(content)
    lines = [
        f"📋 第 {entry_id} 条  [{ctype}]  {ts}",
        "─" * 40,
        content,
    ]
    if entry.get("favorite"):
        lines.append("─" * 40)
        lines.append("⭐ 已收藏")
    return "\n".join(lines)


def _clipboard_toggle_favorite(entry_id: int, entries: list) -> str:
    """切换收藏状态。"""
    if entry_id < 1 or entry_id > len(entries):
        return f"❌ 无效编号: {entry_id}"
    entry = entries[entry_id - 1]
    current = entry.get("favorite", False)
    entry["favorite"] = not current
    # 写入文件（entries 可能倒序过，用原始顺序写回）
    try:
        with open(_CLIPBOARD_HISTORY_PATH, encoding="utf-8") as f:
            all_data = json.load(f)
        # 找到对应条目
        target_content = entry.get("content")
        target_ts = entry.get("timestamp_str")
        for e in all_data:
            if e.get("content") == target_content and e.get("timestamp_str") == target_ts:
                e["favorite"] = not current
                break
        _save_history_file(all_data)
    except Exception:
        return "❌ 保存失败"
    status = "已收藏 ⭐" if not current else "取消收藏"
    return f"✅ 第 {entry_id} 条 {status}"


def _clipboard_stats(entries: list) -> str:
    """剪贴板使用统计。"""
    total = len(entries)
    if total == 0:
        return "📋 剪贴板统计: 暂无数据"

    # 按类型统计
    type_counts: dict[str, int] = {}
    for e in entries:
        t = _detect_clipboard_type(e.get("content", ""))
        type_counts[t] = type_counts.get(t, 0) + 1

    fav_count = sum(1 for e in entries if e.get("favorite"))
    today_count = sum(
        1 for e in entries
        if e.get("timestamp_str", "").startswith(time.strftime("%Y-%m-%d"))
    )

    lines = ["📊 剪贴板统计:", f"  总条目: {total}", f"  今天: {today_count}", f"  收藏: {fav_count}", ""]
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        lines.append(f"    {t}: {c} 条")

    return "\n".join(lines)


def _save_history_file(data: list):
    """写回剪贴板文件。"""
    import tempfile
    tmp = _CLIPBOARD_HISTORY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _CLIPBOARD_HISTORY_PATH)


# ── 命令注册 ─────────────────────────────────────────────

COMMANDS: dict = {
    "timer": cmd_timer,
    "clipboard_history": cmd_clipboard_history,
    "clipboard_pro": cmd_clipboard_pro,
    "translate": cmd_translate,
    "shortcut": cmd_shortcut,
    "credential": cmd_credential,
}

TOOL_SCHEMAS: dict = {
    "clipboard_pro": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "search", "filter", "favorite", "favorites", "view", "stats"],
                "description": "操作类型: list=列表, search=搜索, filter=按类型筛选, favorite=收藏, favorites=查看收藏, view=查看完整内容, stats=统计",
            },
            "query": {
                "type": "string",
                "description": "搜索关键词（action=search 时必填）",
            },
            "id": {
                "type": "integer",
                "description": "条目编号（action=view/favorite 时必填）",
            },
            "type": {
                "type": "string",
                "enum": ["url", "file", "code", "json", "text"],
                "description": "筛选类型（action=filter 时必填）",
            },
        },
        "required": ["action"],
    },

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
                "description": "Keychain 服务名称，默认 zhixing",
            },
        },
        "required": ["action"],
    },
}

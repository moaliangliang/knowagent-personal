"""国际化支持 — 中英文双语。

自动检测系统语言，提供中文/英文翻译。
"""

import locale
import os
import re


def detect_lang() -> str:
    """检测系统语言，返回 'zh' 或 'en'。"""
    # 环境变量覆盖
    env_lang = os.environ.get("ZHIXING_LANG", "")
    if env_lang in ("zh", "en"):
        return env_lang

    # macOS 系统语言检测
    try:
        import subprocess
        r = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            out = r.stdout
            if "en" in out and "zh" not in out:
                return "en"
            if "zh" in out:
                return "zh"
    except Exception:
        pass

    # locale 回退
    try:
        lang = locale.getdefaultlocale()[0] or ""
        if lang.startswith("zh"):
            return "zh"
        return "en"
    except Exception:
        return "en"


# ── 翻译表 ─────────────────────────────────────

_T = {
    # 通用
    "连接成功":       {"zh": "● 已连接", "en": "● Connected"},
    "未连接":         {"zh": "○ 未连接", "en": "○ Disconnected"},
    "连接服务器失败": {"zh": "❌ 连接服务器失败\n请确认 python3 server.py 已运行",
                      "en": "❌ Server connection failed\nRun: python3 server.py"},
    "处理中":         {"zh": "⏳ 处理中...", "en": "⏳ Processing..."},
    "已复制":         {"zh": "✅ 已复制", "en": "✅ Copied"},
    "复制":           {"zh": "📋 复制", "en": "📋 Copy"},
    "清除":           {"zh": "🗑️ 清除", "en": "🗑️ Clear"},
    "清除会话":       {"zh": "🗑️ 会话已清除", "en": "🗑️ Session cleared"},
    "查看命令":       {"zh": "💡 输入 help 查看命令", "en": "💡 Type help for commands"},
    "暂无待办":       {"zh": "✅ 暂无待办事项", "en": "✅ No pending tasks"},
    "加载中":         {"zh": "加载中...", "en": "Loading..."},
    "刷新":           {"zh": "🔄 刷新", "en": "🔄 Refresh"},

    # 标签
    "对话":           {"zh": "💬 对话", "en": "💬 Chat"},
    "待办":           {"zh": "📋 待办", "en": "📋 Tasks"},

    # 标题
    "AppName":        {"zh": "🤖 知行", "en": "🤖 Flow"},

    # 输入框占位
    "输入命令":       {"zh": "输入命令...", "en": "Type a command..."},

    # 系统
    "系统状态":       {"zh": "系统", "en": "System"},
    "网络工具":       {"zh": "网络", "en": "Network"},
    "文件管理":       {"zh": "文件", "en": "Files"},
    "媒体处理":       {"zh": "媒体", "en": "Media"},
    "音乐":           {"zh": "音乐", "en": "Music"},
    "邮件":           {"zh": "邮件", "en": "Mail"},
    "日常效率":       {"zh": "日常", "en": "Daily"},
    "AI 增强":        {"zh": "AI", "en": "AI"},
    "监控":           {"zh": "监控", "en": "Monitor"},
    "开发工具":       {"zh": "开发", "en": "Dev"},
    "工具":           {"zh": "工具", "en": "Tools"},
    "VPN":            {"zh": "VPN", "en": "VPN"},
    "自动化":         {"zh": "自动化", "en": "Automation"},
    "待办管理":       {"zh": "待办", "en": "Todos"},
    "Pro 功能":       {"zh": "Pro", "en": "Pro"},
    "企业消息":       {"zh": "消息", "en": "Messaging"},

    # 截图
    "截图已保存":     {"zh": "截屏已保存", "en": "Screenshot saved"},
    "图片已复制":     {"zh": "图片已复制到剪贴板", "en": "Image copied to clipboard"},
    "隐藏按钮":       {"zh": "隐藏按钮", "en": "Hide button"},

    # 待办
    "添加待办":       {"zh": "添加待办", "en": "Add task"},
    "待办列表":       {"zh": "待办列表", "en": "Task list"},
    "完成待办":       {"zh": "完成待办", "en": "Complete task"},
    "删除待办":       {"zh": "删除待办", "en": "Delete task"},
    "新建待办":       {"zh": "＋ 新建", "en": "＋ New"},
    "输入待办":       {"zh": "输入待办内容...", "en": "New task..."},
    "添加":           {"zh": "添加", "en": "Add"},

    # 自动操作
    "任务执行完成":   {"zh": "🎉 任务执行完成", "en": "🎉 Task completed"},
    "请选择":         {"zh": "请选择操作类型：", "en": "Please select an action:"},
    "创建物料":       {"zh": "📦 创建物料", "en": "📦 Create Part"},
    "搜索零件":       {"zh": "🔍 搜索零件", "en": "🔍 Search Part"},
    "截屏分析":       {"zh": "📸 截屏分析", "en": "📸 Screenshot"},
    "系统状态快捷":   {"zh": "⚡ 系统状态", "en": "⚡ System Status"},
    "查看命令":       {"zh": "📋 查看全部命令", "en": "📋 All Commands"},
}


def t(key: str, lang: str | None = None) -> str:
    """翻译：根据语言返回对应文本。"""
    if lang is None:
        lang = detect_lang()
    entry = _T.get(key, {})
    if lang == "en":
        return entry.get("en", key)
    return entry.get("zh", key)


def tt(text: str, lang: str | None = None) -> str:
    """智能翻译：对文本中的中文关键词做翻译。

    保留非中文部分，只替换已知的翻译项。
    """
    if lang is None:
        lang = detect_lang()
    if lang == "zh":
        return text

    result = text
    for key, entry in _T.items():
        zh_text = entry.get("zh", "")
        en_text = entry.get("en", "")
        if zh_text and en_text and zh_text in result:
            result = result.replace(zh_text, en_text)
    return result

"""系统语言检测与多语言帮助文本"""

import locale
import subprocess


def get_system_lang() -> str:
    """获取 macOS 系统语言，返回 'zh' 或 'en'"""
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            out = result.stdout.strip()
            if "zh-Hans" in out or "zh_CN" in out or "zh-TW" in out or "zh_HK" in out:
                return "zh"
        # fallback: locale
        lang = locale.getdefaultlocale()[0] or ""
        if lang.startswith("zh"):
            return "zh"
        return "en"
    except Exception:
        try:
            lang = locale.getdefaultlocale()[0] or ""
            return "zh" if lang.startswith("zh") else "en"
        except Exception:
            return "en"


# ── 英文帮助文本 ─────────────────────────────────────────

HELP_EN: dict = {
    "title": "📖 Mac Agent Personal Help",
    "natural_title": "Natural Language Examples",
    "ex_categories": {
        "🔧 System Control": ["display_brightness", "system_volume", "system_sleep", "system_shutdown", "system_restart", "screensaver", "focus_mode", "system_status", "battery_status", "wifi_status", "lock_screen"],
        "🌐 Network Tools": ["my_ip", "speedtest", "http_request", "download", "whois", "ping", "port_check"],
        "📁 File Management": ["file_search", "file_grep", "file_list", "compress", "extract", "trash", "duplicate_finder", "convert_image"],
        "💻 Dev Tools": ["brew", "process", "docker"],
        "🎬 Media": ["screen_record", "audio_record", "video_info", "ocr_file", "screenshot", "screenshot_analyze"],
        "📅 Daily": ["timer", "clipboard_history", "translate", "shortcut", "notification", "calendar", "reminder_add"],
        "🤖 AI": ["chat", "summarize", "code_review", "image_gen", "knowledge_retrieve"],
        "📊 Monitor & VPN": ["disk_monitor", "battery_health", "sensor_temp", "vpn_status"],
        "🎵 Music & Mail": ["music_play", "music_search", "music_search_online", "music_volume", "music_next", "mail_read", "mail_master", "mail_send"],
        "⌨️ UI & Keyboard": ["ui_tree", "ui_find", "ui_click", "keyboard_type", "keyboard_press", "clipboard_read", "clipboard_write", "speak", "voice_input", "contacts_search", "notes_list", "workflow_execute", "open_app", "open_url"],
    },
    "natural_examples": [
        ("play Jay Chou", "Search & play on Apple Music"),
        ("system status", "Check CPU/RAM/disk/network"),
        ("translate hello", "Text translation"),
        ("speed test", "Network speed test"),
        ("search file report.pdf", "Spotlight file search"),
        ("screenshot", "Take a screenshot"),
        ("record screen 10s", "Screen recording"),
        ("temperature", "CPU temperature"),
        ("lock screen", "Lock the screen"),
        ("workflow", "Run preset multi-step workflow"),
    ],
    "knowledge_title": "Personal Knowledge Base",
    "knowledge_cmds": [
        ("rag init", "Initialize knowledge base"),
        ("rag index ~/Documents", "Index documents"),
        ("rag search <query>", "Search knowledge base"),
        ("rag clear", "Clear chat history"),
    ],
    "params_title": "Commands with Parameters",
    "params_examples": [
        "music_search_online keyword=Jay Chou",
        "file_search query=report limit=20",
        "translate text=hello world to=zh",
        "display_brightness level=70",
        "timer minutes=25 name=Pomodoro",
    ],
    "footer": "Type any command name or Chinese name directly, e.g. 亮度 70  or 温度",
}

# ── 中文帮助文本 ─────────────────────────────────────────

HELP_ZH: dict = {
    "title": "📖 Mac Agent Personal 使用帮助",
    "natural_title": "自然语言示例",
    "ex_categories": {
        "🔧 系统控制": ["display_brightness", "system_volume", "system_sleep", "system_shutdown", "system_restart", "screensaver", "focus_mode", "system_status", "battery_status", "wifi_status", "lock_screen"],
        "🌐 网络工具": ["my_ip", "speedtest", "http_request", "download", "whois", "ping", "port_check"],
        "📁 文件管理": ["file_search", "file_grep", "file_list", "compress", "extract", "trash", "duplicate_finder", "convert_image"],
        "💻 开发工具": ["brew", "process", "docker"],
        "🎬 媒体处理": ["screen_record", "audio_record", "video_info", "ocr_file", "screenshot", "screenshot_analyze"],
        "📅 日常效率": ["timer", "clipboard_history", "translate", "shortcut", "notification", "calendar", "reminder_add"],
        "🤖 AI 增强": ["chat", "summarize", "code_review", "image_gen", "knowledge_retrieve"],
        "📊 监控 & VPN": ["disk_monitor", "battery_health", "sensor_temp", "vpn_status"],
        "🎵 音乐 & 邮件": ["music_play", "music_search", "music_search_online", "music_volume", "music_next", "mail_read", "mail_master", "mail_send"],
        "⌨️ UI & 键盘": ["ui_tree", "ui_find", "ui_click", "keyboard_type", "keyboard_press", "clipboard_read", "clipboard_write", "speak", "voice_input", "contacts_search", "notes_list", "workflow_execute", "open_app", "open_url"],
    },
    "natural_examples": [
        ("播放周杰伦的歌", "搜索 Apple Music 并播放"),
        ("系统状态", "查 CPU/内存/磁盘/网络"),
        ("翻译 hello", "文本翻译"),
        ("测速", "网络测速"),
        ("搜索文件 report.pdf", "Spotlight 搜索文件"),
        ("截个屏", "截屏"),
        ("录屏 10秒", "录屏"),
        ("温度", "查看 CPU 温度"),
        ("锁屏", "锁定屏幕"),
        ("工作流", "运行预设的多步工作流"),
    ],
    "knowledge_title": "个人知识库",
    "knowledge_cmds": [
        ("rag init", "初始化知识库"),
        ("rag index ~/Documents", "索引文档"),
        ("rag search <关键词>", "搜索知识库"),
        ("rag clear", "清除对话历史"),
    ],
    "params_title": "命令+参数",
    "params_examples": [
        "music_search_online keyword=周杰伦",
        "file_search query=report limit=20",
        "translate text=hello world to=zh",
        "display_brightness level=70",
        "timer minutes=25 name=番茄钟",
    ],
    "footer": "直接输入命令名或中文名即可调用，如 亮度 70 或 温度",
}


def get_help_text(lang: str | None = None) -> dict:
    """获取对应语言的帮助文本"""
    if lang is None:
        lang = get_system_lang()
    return HELP_ZH if lang == "zh" else HELP_EN

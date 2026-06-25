"""系统语言检测与多语言帮助文本 — Harness 感知版本"""

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
        lang = locale.getdefaultlocale()[0] or ""
        return "zh" if lang.startswith("zh") else "en"
    except Exception:
        try:
            lang = locale.getdefaultlocale()[0] or ""
            return "zh" if lang.startswith("zh") else "en"
        except Exception:
            return "en"


# ── 英文帮助文本 ─────────────────────────────────────────

HELP_EN: dict = {
    "title": "📖 Mac Agent Personal Help",
    "subtitle": "83 commands · Harness-powered · 5 security modes",
    "natural_title": "Natural Language Examples",
    "harness_title": "🛡️ Harness Security Layer",
    "harness_info": [
        ("5 permission modes", "plan / normal / accept_edits / elevated / trusted"),
        ("7-layer defense", "Pre-filter → Deny-First → Mode → Session → ThreatScan → Sandbox → Audit"),
        ("code sandbox", "7-tool whitelist · env scrubbing · 60s timeout"),
        ("audit log", "~/.knowagent/logs/audit_*.jsonl"),
    ],
    "ex_categories": {
        "🔧 System Control": ["display_brightness", "system_volume", "system_sleep", "system_shutdown", "system_restart", "screensaver", "focus_mode", "system_status", "battery_status", "wifi_status", "lock_screen"],
        "💬 Messaging": ["wecom", "feishu", "dingtalk", "broadcast"],
        "🌐 Network Tools": ["my_ip", "speedtest", "http_request", "download", "whois", "ping", "port_check"],
        "📁 File Management": ["file_search", "file_grep", "file_list", "compress", "extract", "trash", "duplicate_finder", "convert_image"],
        "💻 Dev Tools": ["brew", "process", "docker"],
        "🎬 Media": ["screen_record", "audio_record", "video_info", "ocr_file", "screenshot", "screenshot_analyze"],
        "📅 Daily": ["timer", "clipboard_history", "translate", "shortcut", "notification", "calendar", "reminder_add"],
        "🤖 AI": ["chat", "summarize", "code_review", "image_gen", "knowledge_retrieve"],
        "📊 Monitor & VPN": ["disk_monitor", "battery_health", "sensor_temp", "vpn_status"],
        "🎵 Music & Mail": ["music_play", "music_search", "music_search_online", "music_volume", "music_next", "mail_read", "mail_master", "mail_send"],
        "⌨️ UI & Keyboard": ["ui_tree", "ui_find", "ui_click", "keyboard_type", "keyboard_press", "clipboard_read", "clipboard_write", "speak", "voice_input", "contacts_search", "notes_list", "workflow_execute", "open_app", "open_url"],
        "🔐 Security & Tools": ["clipboard_monitor_start", "clipboard_monitor_stop", "clipboard_monitor_status", "credential", "config"],
        "🔌 Plugin & Skill": ["skill"],
    },
    "natural_examples": [
        ("play Jay Chou", "Search & play on Apple Music"),
        ("system status", "Check CPU/RAM/disk/network"),
        ("screenshot", "Take a screenshot"),
        ("translate hello", "Text translation"),
        ("speed test", "Network speed test"),
        ("search file report.pdf", "Spotlight file search"),
        ("temperature", "CPU temperature"),
        ("lock screen", "Lock the screen"),
        ("workflow", "Run preset multi-step workflow"),
    ],
    "knowledge_title": "Personal Knowledge Base (RAG)",
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
    "footer": "Type any command name or Chinese name directly, e.g. 'brightness 70' or 'temperature'",
}

# ── 中文帮助文本 ─────────────────────────────────────────

HELP_ZH: dict = {
    "title": "📖 Mac Agent Personal 使用帮助",
    "subtitle": "83 个命令 · Harness 安全架构 · 5 种权限模式",
    "natural_title": "自然语言示例",
    "harness_title": "🛡️ Harness 安全层",
    "harness_info": [
        ("5 种权限模式", "plan(全部审批) / normal(日常默认) / accept_edits / elevated / trusted"),
        ("7 层防御", "预过滤 → 拒绝优先 → 模式约束 → 会话授权 → 威胁扫描 → 隔离执行 → 审计日志"),
        ("代码沙箱", "7 工具白名单 · 环境变量清洗 · 60 秒超时"),
        ("审计日志", "~/.knowagent/logs/audit_*.jsonl"),
    ],
    "ex_categories": {
        "🔧 系统控制": ["display_brightness", "system_volume", "system_sleep", "system_shutdown", "system_restart", "screensaver", "focus_mode", "system_status", "battery_status", "wifi_status", "lock_screen"],
        "💬 企业通讯": ["wecom", "feishu", "dingtalk", "broadcast"],
        "🌐 网络工具": ["my_ip", "speedtest", "http_request", "download", "whois", "ping", "port_check"],
        "📁 文件管理": ["file_search", "file_grep", "file_list", "compress", "extract", "trash", "duplicate_finder", "convert_image"],
        "💻 开发工具": ["brew", "process", "docker"],
        "🎬 媒体处理": ["screen_record", "audio_record", "video_info", "ocr_file", "screenshot", "screenshot_analyze"],
        "📅 日常效率": ["timer", "clipboard_history", "translate", "shortcut", "notification", "calendar", "reminder_add"],
        "🤖 AI 增强": ["chat", "summarize", "code_review", "image_gen", "knowledge_retrieve"],
        "📊 监控 & VPN": ["disk_monitor", "battery_health", "sensor_temp", "vpn_status"],
        "🎵 音乐 & 邮件": ["music_play", "music_search", "music_search_online", "music_volume", "music_next", "mail_read", "mail_master", "mail_send"],
        "⌨️ UI & 键盘": ["ui_tree", "ui_find", "ui_click", "keyboard_type", "keyboard_press", "clipboard_read", "clipboard_write", "speak", "voice_input", "contacts_search", "notes_list", "workflow_execute", "open_app", "open_url"],
        "🔐 安全 & 工具": ["clipboard_monitor_start", "clipboard_monitor_stop", "clipboard_monitor_status", "credential", "config"],
        "🔌 插件 & Skill": ["skill"],
    },
    "natural_examples": [
        ("播放周杰伦的歌", "搜索 Apple Music 并播放"),
        ("系统状态", "查 CPU/内存/磁盘/网络"),
        ("截个屏", "截屏"),
        ("看看屏幕上有什么字", "截屏+OCR 识别文字"),
        ("打开 Music 的界面结构", "查看 Music App 的 UI 树"),
        ("翻译 hello", "文本翻译"),
        ("测速", "网络测速"),
        ("搜索文件 report.pdf", "Spotlight 搜索文件"),
        ("锁屏", "锁定屏幕（需权限确认）"),
        ("工作流", "运行预设的多步工作流"),
    ],
    "knowledge_title": "个人知识库 (RAG)",
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
    "footer": "直接输入命令名或中文名即可调用。风险操作（锁屏/关机/键盘模拟）需要权限确认。",
}


def get_help_text(lang: str | None = None) -> dict:
    """获取对应语言的帮助文本（自动注入动态命令计数）。"""
    if lang is None:
        lang = get_system_lang()
    text = HELP_ZH if lang == "zh" else HELP_EN

    # 从注册表动态注入命令计数
    try:
        from knowagent_personal.harness.registry import TOOL_REGISTRY
        count = TOOL_REGISTRY.count
        if count > 0:
            text = dict(text)  # 不修改全局
            text["subtitle"] = text["subtitle"].replace("83 ", f"{count} ")
    except Exception:
        pass

    return text

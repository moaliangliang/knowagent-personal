"""中文命令别名 — 让所有命令可以用中文调用"""

# 中文命令名 → 英文命令名 映射
CN_ALIASES = {
    # ── 系统控制 ──
    "亮度": "display_brightness",
    "屏幕亮度": "display_brightness",
    "音量": "system_volume",
    "系统音量": "system_volume",
    "睡眠": "system_sleep",
    "休眠": "system_sleep",
    "关机": "system_shutdown",
    "重启": "system_restart",
    "重新启动": "system_restart",
    "屏保": "screensaver",
    "屏幕保护": "screensaver",
    "专注模式": "focus_mode",
    "勿扰模式": "focus_mode",
    "免打扰": "focus_mode",

    # ── 网络工具 ──
    "我的IP": "my_ip",
    "公网IP": "my_ip",
    "外网IP": "my_ip",
    "测速": "speedtest",
    "网速测试": "speedtest",
    "网络测速": "speedtest",
    "HTTP请求": "http_request",
    "请求": "http_request",
    "调用API": "http_request",
    "下载": "download",
    "下载文件": "download",
    "whois": "whois",
    "域名查询": "whois",
    "ping": "ping",
    "网络延迟": "ping",
    "端口检查": "port_check",
    "端口检测": "port_check",

    # ── 文件管理 ──
    "搜索文件": "file_search",
    "查找文件": "file_search",
    "文件搜索": "file_search",
    "搜索内容": "file_grep",
    "文件内容搜索": "file_grep",
    "文件查找": "file_grep",
    "压缩": "compress",
    "打包": "compress",
    "解压": "extract",
    "解压缩": "extract",
    "删除": "trash",
    "移到废纸篓": "trash",
    "清空废纸篓": "trash",
    "清空回收站": "trash",
    "重复文件": "duplicate_finder",
    "重复文件检测": "duplicate_finder",
    "转换图片": "convert_image",
    "图片转换": "convert_image",
    "图片格式": "convert_image",

    # ── 开发工具 ──
    "brew": "brew",
    "Homebrew": "brew",
    "安装包": "brew",
    "进程": "process",
    "进程管理": "process",
    "进程列表": "process",
    "杀进程": "process",
    "docker": "docker",
    "容器": "docker",

    # ── 媒体处理 ──
    "录屏": "screen_record",
    "屏幕录制": "screen_record",
    "录音": "audio_record",
    "音频录制": "audio_record",
    "视频信息": "video_info",
    "视频详情": "video_info",
    "视频元数据": "video_info",
    "OCR": "ocr_file",
    "识别图片": "ocr_file",
    "图片文字识别": "ocr_file",

    # ── 日常效率 ──
    "计时器": "timer",
    "倒计时": "timer",
    "番茄钟": "timer",
    "剪贴板历史": "clipboard_history",
    "粘贴板历史": "clipboard_history",
    "翻译": "translate",
    "翻译文本": "translate",
    "快捷指令": "shortcut",
    "捷径": "shortcut",

    # ── AI 增强 ──
    "对话": "chat",
    "聊天": "chat",
    "直接对话": "chat",
    "总结": "summarize",
    "摘要": "summarize",
    "概括": "summarize",
    "代码审查": "code_review",
    "审查代码": "code_review",
    "代码评审": "code_review",
    "生成图片": "image_gen",
    "画图": "image_gen",
    "AI绘图": "image_gen",

    # ── 监控 ──
    "磁盘": "disk_monitor",
    "磁盘空间": "disk_monitor",
    "硬盘": "disk_monitor",
    "电池健康": "battery_health",
    "电池状态": "battery_health",
    "电池寿命": "battery_health",
    "温度": "sensor_temp",
    "CPU温度": "sensor_temp",
    "传感器温度": "sensor_temp",

    # ── VPN（已有的） ──
    "VPN": "vpn_status",
    "代理": "vpn_status",

    # ── 企业通讯（新增）──
    "企业微信": "wecom",
    "微信通知": "wecom",
    "飞书": "feishu",
    "飞书通知": "feishu",
    "钉钉": "dingtalk",
    "钉钉通知": "dingtalk",
    "群发": "broadcast",
    "通知全部": "broadcast",

    # ── 从 NL_RULES 迁移（简单映射，无需参数提取）──
    "播放": "music_search_online",
    "听": "music_search_online",
    "唱": "music_search_online",
    "放": "music_search_online",
    "邮箱大师": "mail_master",
    "系统": "system_status",
    "状态": "system_status",
    "内存": "system_status",
    "性能": "system_status",
    "电量": "battery_status",
    "网络": "wifi_status",
    "无线": "wifi_status",
    "截图": "screenshot",
    "屏幕": "screenshot",
    "截屏": "screenshot",
    "帮助": "help",
    "输入": "keyboard_type",
    "打字": "keyboard_type",
    "快捷键": "keyboard_press",
    "通知": "notification",
    "提醒": "notification",
    "日历": "calendar",
    "日程": "calendar",
    "锁屏": "lock_screen",
    "锁定": "lock_screen",
    "朗读": "speak",
    "语音": "voice_input",
    "说话": "voice_input",
    "麦克风": "voice_input",
    "打开": "open_app",
    "启动": "open_app",
    "目录": "file_list",
}

# 构建反向映射（英文 → 中文列表），供帮助信息使用
EN_TO_CN: dict[str, list[str]] = {}
for cn, en in CN_ALIASES.items():
    EN_TO_CN.setdefault(en, []).append(cn)


def get_cn_aliases(cmd_name: str) -> list[str]:
    """获取某个命令的所有中文别名"""
    return EN_TO_CN.get(cmd_name, [])


def resolve_cn(text: str) -> tuple[str, str] | None:
    """将中文命令名解析为英文命令名。
    返回 (英文命令名, 剩余参数字符串) 或 None。
    支持 "翻译 text=hello" 这样的 "别名 参数" 格式。
    """
    text = text.strip()
    # 1. 精确匹配（仅中文别名，无参数）
    if text in CN_ALIASES:
        return (CN_ALIASES[text], "")

    # 2. 前缀匹配：中文别名 + 参数
    # 按长度降序排列，优先匹配最长别名
    import re as _re
    sorted_keys = sorted(CN_ALIASES.keys(), key=len, reverse=True)
    for cn_key in sorted_keys:
        if text.startswith(cn_key + " ") or text.startswith(cn_key + "="):
            remaining = text[len(cn_key):].strip()
            return (CN_ALIASES[cn_key], remaining)
        # CJK 别名无需空格：如 "播放周杰伦的歌" 匹配 "播放"
        if text.startswith(cn_key) and _re.search(r'[一-鿿]', cn_key):
            remaining = text[len(cn_key):].strip()
            if remaining:  # 有后续内容才匹配
                return (CN_ALIASES[cn_key], remaining)

    return None

"""Enhanced Tool Registry — 工具定义的元数据层。

比原始 COMMANDS 字典增加了：
- 工具分类（category）
- 权限级别（permission）
- 只读/破坏性标记（is_readonly, is_destructive）
- 并发安全标记（concurrency_safe）
- 执行超时（timeout）
- 文档描述（description）

遵循 Claude Code 的 buildTool() 工厂模式原则。
"""

from __future__ import annotations

import inspect
import enum
import time
from dataclasses import dataclass, field
from typing import Any, Callable

# ── 分类与权限定义 ────────────────────────────────────────


class ToolCategory(str, enum.Enum):
    """工具分类 — 用于分组和权限域控制"""
    SYSTEM = "system"          # 系统状态查询
    SYSTEM_CTRL = "system_ctrl"  # 系统控制（锁屏、睡眠等）
    MEDIA = "media"            # 音乐/语音
    MAIL = "mail"              # 邮件
    FILE = "file"              # 文件操作
    UI = "ui"                  # UI 自动化
    INPUT = "input"            # 键盘/输入
    CLIPBOARD = "clipboard"    # 剪贴板
    CALENDAR = "calendar"      # 日历
    NETWORK = "network"        # 网络
    DEV = "dev"                # 开发工具
    AI = "ai"                  # AI 相关
    WINDCHILL = "windchill"    # Windchill 桥接
    VPN = "vpn"                # VPN
    WORKFLOW = "workflow"      # 工作流
    PLUGIN = "plugin"          # 插件/Skill
    KNOWLEDGE = "knowledge"    # 知识库
    MONITOR = "monitor"        # 系统监控
    GENERAL = "general"        # 通用 / 未分类


class PermissionLevel(int, enum.Enum):
    """权限级别 — 遵循拒绝优先（Deny-First）模型。

    数值越大，所需权限越高。
    默认拒绝所有，由用户/策略逐步开放。
    """
    BASIC = 10      # 基础只读查询
    READ_ONLY = 20  # 只读操作
    MEDIA = 30      # 媒体控制
    FILE_READ = 40  # 文件读取
    FILE_WRITE = 50 # 文件写入
    UI_READ = 60    # UI 查看
    UI_CTRL = 70    # UI 操作（点击、打字）
    SYSTEM_CTRL = 80  # 系统控制（锁屏、睡眠）
    DESTRUCTIVE = 90  # 破坏性操作
    ADMIN = 100       # 管理员级


# 默认分类映射 — 命令名 → 推断分类
# 先精确匹配（完整命令名），再前缀匹配
_PREFIX_CATEGORY: dict[str, ToolCategory] = {
    # ── 系统类 ──
    "system_": ToolCategory.SYSTEM,
    "battery_": ToolCategory.SYSTEM,
    "wifi_": ToolCategory.SYSTEM,
    "display_": ToolCategory.SYSTEM,        # display_brightness
    "system_": ToolCategory.SYSTEM_CTRL,    # system_sleep/shutdown/restart/volume
    "sound_": ToolCategory.SYSTEM_CTRL,
    "screensaver": ToolCategory.SYSTEM_CTRL,
    "focus_": ToolCategory.SYSTEM_CTRL,
    "lock_": ToolCategory.SYSTEM_CTRL,
    "config": ToolCategory.SYSTEM,          # 系统配置

    # ── 媒体类 ──
    "music_": ToolCategory.MEDIA,
    "audio_": ToolCategory.MEDIA,           # audio_record
    "screen_record": ToolCategory.MEDIA,
    "speak": ToolCategory.MEDIA,
    "voice_": ToolCategory.MEDIA,
    "video_": ToolCategory.MEDIA,           # video_info
    "notification": ToolCategory.MEDIA,

    # ── 邮件类 ──
    "mail_": ToolCategory.MAIL,

    # ── 文件类 ──
    "file_": ToolCategory.FILE,
    "compress": ToolCategory.FILE,
    "extract": ToolCategory.FILE,
    "trash": ToolCategory.FILE,
    "duplicate_": ToolCategory.FILE,
    "convert_": ToolCategory.FILE,          # convert_image
    "ocr_": ToolCategory.FILE,             # ocr_file

    # ── UI 自动化 ──
    "screenshot": ToolCategory.UI,
    "ui_": ToolCategory.UI,

    # ── 输入 ──
    "keyboard_": ToolCategory.INPUT,

    # ── 剪贴板 ──
    "clipboard_": ToolCategory.CLIPBOARD,

    # ── 日历 ──
    "calendar": ToolCategory.CALENDAR,

    # ── 应用管理 ──
    "open_app": ToolCategory.UI,        # 精确匹配优于 open_ 前缀
    "open_url": ToolCategory.UI,        # 精确匹配优于 open_ 前缀
    "open_": ToolCategory.GENERAL,

    # ── 提醒 ──
    "reminder_": ToolCategory.SYSTEM_CTRL,
    "notes_": ToolCategory.SYSTEM,
    "contacts_": ToolCategory.SYSTEM,

    # ── 效率工具 ──
    "timer": ToolCategory.GENERAL,
    "shortcut": ToolCategory.GENERAL,

    # ── 企业通信 ──
    "wecom": ToolCategory.GENERAL,
    "feishu": ToolCategory.GENERAL,
    "dingtalk": ToolCategory.GENERAL,
    "broadcast": ToolCategory.GENERAL,

    # ── 网络 ──
    "network_": ToolCategory.NETWORK,
    "my_": ToolCategory.NETWORK,           # my_ip
    "speedtest": ToolCategory.NETWORK,
    "http_": ToolCategory.NETWORK,
    "download": ToolCategory.NETWORK,
    "whois": ToolCategory.NETWORK,
    "ping": ToolCategory.NETWORK,
    "port_": ToolCategory.NETWORK,

    # ── VPN ──
    "vpn_": ToolCategory.VPN,

    # ── 工作流 ──
    "workflow_": ToolCategory.WORKFLOW,

    # ── 知识库 ──
    "knowledge_": ToolCategory.KNOWLEDGE,

    # ── 开发工具 ──
    "dev_": ToolCategory.DEV,
    "brew": ToolCategory.DEV,
    "docker": ToolCategory.DEV,
    "process": ToolCategory.DEV,

    # ── AI ──
    "chat": ToolCategory.AI,
    "code_": ToolCategory.AI,              # code_review
    "summarize": ToolCategory.AI,
    "image_": ToolCategory.AI,             # image_gen
    "translate": ToolCategory.AI,

    # ── 企业通信 ──
    "wecom": ToolCategory.GENERAL,
    "feishu": ToolCategory.GENERAL,
    "dingtalk": ToolCategory.GENERAL,
    "broadcast": ToolCategory.GENERAL,

    # ── 插件/技能 ──
    "skill": ToolCategory.PLUGIN,

    # ── 效率工具 ──
    "timer": ToolCategory.GENERAL,
    "shortcut": ToolCategory.GENERAL,

    # ── 监控 ──
    "monitor_": ToolCategory.MONITOR,
    "disk_": ToolCategory.MONITOR,         # disk_monitor
    "sensor_": ToolCategory.MONITOR,       # sensor_temp

    # ── 凭证 ──
    "credential": ToolCategory.GENERAL,
}

# 精确命令名 → 分类映射（优先级高于前缀匹配）
_EXACT_CATEGORY: dict[str, ToolCategory] = {
    "open_app": ToolCategory.UI,
    "open_url": ToolCategory.UI,
    "timer": ToolCategory.GENERAL,
    "shortcut": ToolCategory.SYSTEM_CTRL,
    "credential": ToolCategory.GENERAL,
    "notes_list": ToolCategory.SYSTEM,
    "contacts_search": ToolCategory.SYSTEM,
    "system_volume": ToolCategory.SYSTEM_CTRL,
    "system_sleep": ToolCategory.SYSTEM_CTRL,
    "system_shutdown": ToolCategory.SYSTEM_CTRL,
    "system_restart": ToolCategory.SYSTEM_CTRL,
}

# 默认权限映射 — 自动推断权限级别
# Deny-first: 未列出的命令根据分类推断，推断失败则 DESTRUCTIVE
_CMD_PERMISSION: dict[str, PermissionLevel] = {
    # ═══════════════ 只读查询 ═══════════════
    "system_status": PermissionLevel.BASIC,
    "battery_status": PermissionLevel.BASIC,
    "battery_health": PermissionLevel.BASIC,
    "wifi_status": PermissionLevel.BASIC,
    "calendar": PermissionLevel.BASIC,
    "clipboard_read": PermissionLevel.READ_ONLY,
    "clipboard_history": PermissionLevel.READ_ONLY,
    "file_list": PermissionLevel.FILE_READ,
    "file_search": PermissionLevel.FILE_READ,
    "file_grep": PermissionLevel.FILE_READ,
    "contacts_search": PermissionLevel.READ_ONLY,
    "notes_list": PermissionLevel.READ_ONLY,
    "ui_tree": PermissionLevel.UI_READ,
    "ui_find": PermissionLevel.UI_READ,
    "knowledge_retrieve": PermissionLevel.READ_ONLY,
    "my_ip": PermissionLevel.BASIC,
    "whois": PermissionLevel.BASIC,
    "ping": PermissionLevel.BASIC,
    "port_check": PermissionLevel.BASIC,
    "speedtest": PermissionLevel.READ_ONLY,
    "sensor_temp": PermissionLevel.BASIC,
    "disk_monitor": PermissionLevel.BASIC,
    "video_info": PermissionLevel.READ_ONLY,

    # ═══════════════ 媒体控制 ═══════════════
    "music_play": PermissionLevel.MEDIA,
    "music_next": PermissionLevel.MEDIA,
    "music_volume": PermissionLevel.MEDIA,
    "music_search": PermissionLevel.MEDIA,
    "music_search_online": PermissionLevel.MEDIA,
    "speak": PermissionLevel.MEDIA,
    "notification": PermissionLevel.MEDIA,
    "voice_input": PermissionLevel.MEDIA,
    "screen_record": PermissionLevel.MEDIA,
    "audio_record": PermissionLevel.MEDIA,

    # ═══════════════ 文件操作 ═══════════════
    "screenshot": PermissionLevel.FILE_WRITE,
    "screenshot_analyze": PermissionLevel.FILE_WRITE,
    "clipboard_write": PermissionLevel.FILE_WRITE,
    "mail_read": PermissionLevel.READ_ONLY,
    "mail_master": PermissionLevel.READ_ONLY,
    "mail_send": PermissionLevel.FILE_WRITE,
    "compress": PermissionLevel.FILE_WRITE,
    "extract": PermissionLevel.FILE_WRITE,
    "ocr_file": PermissionLevel.FILE_WRITE,
    "convert_image": PermissionLevel.FILE_WRITE,
    "download": PermissionLevel.FILE_WRITE,
    "trash": PermissionLevel.FILE_WRITE,
    "duplicate_finder": PermissionLevel.READ_ONLY,

    # ═══════════════ UI 自动化 ═══════════════
    "ui_click": PermissionLevel.UI_CTRL,
    "keyboard_type": PermissionLevel.UI_CTRL,
    "keyboard_press": PermissionLevel.UI_CTRL,
    "open_app": PermissionLevel.UI_CTRL,
    "open_url": PermissionLevel.UI_CTRL,

    # ═══════════════ 系统控制 ═══════════════
    "lock_screen": PermissionLevel.SYSTEM_CTRL,
    "reminder_add": PermissionLevel.SYSTEM_CTRL,
    "display_brightness": PermissionLevel.SYSTEM_CTRL,
    "system_volume": PermissionLevel.SYSTEM_CTRL,
    "system_sleep": PermissionLevel.SYSTEM_CTRL,
    "system_shutdown": PermissionLevel.DESTRUCTIVE,
    "system_restart": PermissionLevel.DESTRUCTIVE,
    "screensaver": PermissionLevel.SYSTEM_CTRL,
    "focus_mode": PermissionLevel.SYSTEM_CTRL,

    # ═══════════════ VPN ═══════════════
    "vpn_status": PermissionLevel.SYSTEM_CTRL,

    # ═══════════════ 工作流 ═══════════════
    "workflow_execute": PermissionLevel.DESTRUCTIVE,

    # ═══════════════ 开发工具 ═══════════════
    "brew": PermissionLevel.DESTRUCTIVE,
    "docker": PermissionLevel.DESTRUCTIVE,
    "process": PermissionLevel.SYSTEM_CTRL,
    "config": PermissionLevel.ADMIN,

    # ═══════════════ AI ═══════════════
    "chat": PermissionLevel.MEDIA,
    "code_review": PermissionLevel.READ_ONLY,
    "summarize": PermissionLevel.READ_ONLY,
    "image_gen": PermissionLevel.FILE_WRITE,
    "translate": PermissionLevel.READ_ONLY,

    # ═══════════════ 效率工具 ═══════════════
    "timer": PermissionLevel.MEDIA,
    "shortcut": PermissionLevel.UI_CTRL,
    "clipboard_monitor_start": PermissionLevel.FILE_WRITE,
    "clipboard_monitor_stop": PermissionLevel.FILE_WRITE,
    "clipboard_monitor_status": PermissionLevel.READ_ONLY,

    # ═══════════════ 插件 ═══════════════
    "skill": PermissionLevel.ADMIN,

    # ═══════════════ 企业通信 ═══════════════
    "credential": PermissionLevel.ADMIN,
}


# ── ToolDef — 统一的工具定义数据类 ────────────────────────


@dataclass
class ToolDef:
    """统一工具定义 — 对应 Claude Code 的 buildTool() 产物。

    所有工具的元数据在此统一描述，执行器根据元数据做不同调度策略。
    """
    name: str                          # 工具名称
    handler: Callable[[dict], str]     # 处理函数 (params: dict) -> str
    category: ToolCategory = ToolCategory.GENERAL
    permission: PermissionLevel = PermissionLevel.READ_ONLY
    description: str = ""              # 从 docstring 提取
    is_readonly: bool = False          # 是否只读 → 可并行执行
    is_destructive: bool = False       # 是否破坏性 → 需二次确认
    concurrency_safe: bool = False     # 是否可并发
    timeout: int = 30                  # 执行超时（秒）
    schema: dict = field(default_factory=dict)  # OpenAI 兼容参数 schema
    plugin: str = ""                   # 来源插件名（空=内置）

    def __post_init__(self):
        if not self.description and self.handler.__doc__:
            self.description = self.handler.__doc__.strip().split("\n")[0]

    def to_openai_tool(self) -> dict:
        """转换为 OpenAI 兼容的 tool definition。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema or {"type": "object", "properties": {}},
            },
        }


# ── 注册表 ────────────────────────────────────────────────


class _ToolRegistry:
    """全局工具注册表 — 单例。

    Deny-first: 未注册的工具既不可见也不可执行。
    """

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        """注册一个工具。如果已存在同名工具则覆盖（方便插件动态替换）。"""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """卸载一个工具。"""
        self._tools.pop(name, None)

    def get(self, name: str) -> ToolDef | None:
        """按名称获取工具定义。"""
        return self._tools.get(name)

    def list(self, category: ToolCategory | None = None,
             min_permission: PermissionLevel | None = None) -> list[ToolDef]:
        """列出工具，支持分类和权限过滤。

        Deny-first: 默认过滤掉高于 BASIC 权限的工具，
        除非调用者显式指定 min_permission。
        """
        results = []
        for tool in self._tools.values():
            if category and tool.category != category:
                continue
            if min_permission and tool.permission.value > min_permission.value:
                continue
            results.append(tool)
        return sorted(results, key=lambda t: t.name)

    @property
    def count(self) -> int:
        return len(self._tools)

    def get_definitions(self) -> list[dict]:
        """返回所有工具的 OpenAI tool definitions。"""
        return [t.to_openai_tool() for t in self._tools.values()]

    @property
    def commands(self) -> dict[str, Callable]:
        """兼容旧版 COMMANDS 字典。"""
        return {name: t.handler for name, t in self._tools.items()}

    @property
    def schemas(self) -> dict[str, dict]:
        """兼容旧版 TOOL_SCHEMAS 字典。"""
        return {name: t.schema for name, t in self._tools.items()}


TOOL_REGISTRY = _ToolRegistry()


# ── 装饰器注册 ────────────────────────────────────────────


def _infer_category(name: str) -> ToolCategory:
    """根据命令名推断分类。

    先精确匹配完整命令名（_EXACT_CATEGORY），再前缀匹配（_PREFIX_CATEGORY）。
    """
    # 先精确匹配
    if name in _EXACT_CATEGORY:
        return _EXACT_CATEGORY[name]
    # 再前缀匹配
    for prefix, cat in _PREFIX_CATEGORY.items():
        if name.startswith(prefix):
            return cat
    return ToolCategory.GENERAL


def _infer_permission(name: str, category: ToolCategory) -> PermissionLevel:
    """根据命令名和分类推断权限级别。

    遵循拒绝优先原则：未明确映射的默认为 DESTRUCTIVE，
    调用者需要显式调低。
    """
    if name in _CMD_PERMISSION:
        return _CMD_PERMISSION[name]

    # 按分类推断默认权限
    category_defaults = {
        ToolCategory.SYSTEM: PermissionLevel.BASIC,
        ToolCategory.SYSTEM_CTRL: PermissionLevel.SYSTEM_CTRL,
        ToolCategory.KNOWLEDGE: PermissionLevel.BASIC,
        ToolCategory.CALENDAR: PermissionLevel.BASIC,
        ToolCategory.CLIPBOARD: PermissionLevel.READ_ONLY,
        ToolCategory.MAIL: PermissionLevel.READ_ONLY,
        ToolCategory.FILE: PermissionLevel.FILE_READ,
        ToolCategory.MEDIA: PermissionLevel.MEDIA,
        ToolCategory.NETWORK: PermissionLevel.READ_ONLY,
        ToolCategory.UI: PermissionLevel.UI_READ,
        ToolCategory.INPUT: PermissionLevel.UI_CTRL,
        ToolCategory.DEV: PermissionLevel.FILE_WRITE,
        ToolCategory.VPN: PermissionLevel.SYSTEM_CTRL,
        ToolCategory.WORKFLOW: PermissionLevel.DESTRUCTIVE,
        ToolCategory.MONITOR: PermissionLevel.BASIC,
        ToolCategory.AI: PermissionLevel.MEDIA,
        ToolCategory.PLUGIN: PermissionLevel.ADMIN,
        ToolCategory.GENERAL: PermissionLevel.FILE_READ,
    }
    return category_defaults.get(category, PermissionLevel.DESTRUCTIVE)


def _infer_readonly(name: str, category: ToolCategory) -> bool:
    """判断工具是否只读。"""
    readonly_categories = {
        ToolCategory.SYSTEM, ToolCategory.KNOWLEDGE,
        ToolCategory.CALENDAR, ToolCategory.MONITOR,
    }
    readonly_commands = {
        # 系统
        "system_status", "battery_status", "battery_health",
        "wifi_status", "sensor_temp", "disk_monitor",
        # 文件
        "file_list", "file_search", "file_grep",
        # 邮件
        "mail_read", "mail_master",
        # 剪贴板
        "clipboard_read", "clipboard_history", "clipboard_monitor_status",
        # 通用只读
        "contacts_search", "notes_list", "knowledge_retrieve",
        # UI
        "ui_tree", "ui_find",
        # 媒体只读
        "music_search", "video_info",
        # 日历
        "calendar",
        # AI
        "code_review", "summarize", "translate",
        # 网络只读
        "my_ip", "whois", "ping", "port_check", "speedtest",
        # 文件分析
        "duplicate_finder",
    }
    return category in readonly_categories or name in readonly_commands


def _infer_destructive(name: str) -> bool:
    """判断工具是否有潜在破坏性。

    破坏性操作 = 拒绝后无法无损恢复（文件删除、关机、系统设置变更等）。
    """
    destructive_names = {
        "lock_screen", "system_sleep", "system_shutdown", "system_restart",
        "workflow_execute", "trash",
        "brew", "docker",
    }
    destructive_prefixes = ("process_kill", "docker_", "brew_", "system_shutdown", "system_restart")
    return (name in destructive_names
            or any(name.startswith(p) for p in destructive_prefixes))


def register_tool(
    name: str | None = None,
    *,
    category: ToolCategory | None = None,
    permission: PermissionLevel | None = None,
    is_readonly: bool | None = None,
    is_destructive: bool | None = None,
    concurrency_safe: bool = False,
    timeout: int = 30,
    schema: dict | None = None,
    plugin: str = "",
) -> Callable:
    """装饰器：注册一个函数为工具。

    遵循拒绝优先原则：
    - 未声明 is_readonly → 自动推断，推断失败则 False（默认不安全）
    - 未声明 permission → 自动推断，推断失败则 DESTRUCTIVE（最高权限）

    用法:
        @register_tool("mail_send", category=ToolCategory.MAIL, permission=PermissionLevel.FILE_WRITE)
        def cmd_mail_send(params: dict) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        if tool_name.startswith("cmd_"):
            tool_name = tool_name[4:]

        inferred_cat = category or _infer_category(tool_name)
        tool = ToolDef(
            name=tool_name,
            handler=func,
            category=inferred_cat,
            permission=permission or _infer_permission(tool_name, inferred_cat),
            description=func.__doc__ or "",
            is_readonly=is_readonly if is_readonly is not None else _infer_readonly(tool_name, inferred_cat),
            is_destructive=is_destructive if is_destructive is not None else _infer_destructive(tool_name),
            concurrency_safe=concurrency_safe,
            timeout=timeout,
            schema=schema or {},
            plugin=plugin,
        )
        TOOL_REGISTRY.register(tool)
        return func
    return decorator


def unregister_tool(name: str) -> None:
    """卸载一个已注册的工具。"""
    TOOL_REGISTRY.unregister(name)


def get_tool(name: str) -> ToolDef | None:
    """获取工具定义。"""
    return TOOL_REGISTRY.get(name)


def list_tools(**kwargs) -> list[ToolDef]:
    """列出工具。"""
    return TOOL_REGISTRY.list(**kwargs)


def get_tool_definitions() -> list[dict]:
    """获取所有工具的 OpenAI tool definitions。"""
    return TOOL_REGISTRY.get_definitions()


# ── 批量导入辅助 ──────────────────────────────────────────


def import_from_legacy(commands: dict[str, Callable],
                       schemas: dict[str, dict] | None = None) -> None:
    """从旧版 COMMANDS 字典批量迁移到 ToolDef 注册表。

    用于渐进式迁移：现有模块可以先用这个函数注册，
    之后逐步将每个 cmd_* 改为 @register_tool 装饰器。
    """
    for cmd_name, handler in commands.items():
        if TOOL_REGISTRY.get(cmd_name):
            continue  # 同名工具已存在，跳过

        inferred_cat = _infer_category(cmd_name)
        perms = _infer_permission(cmd_name, inferred_cat)
        schema = (schemas or {}).get(cmd_name, {})

        tool = ToolDef(
            name=cmd_name,
            handler=handler,
            category=inferred_cat,
            permission=perms,
            description=handler.__doc__ or "",
            is_readonly=_infer_readonly(cmd_name, inferred_cat),
            is_destructive=_infer_destructive(cmd_name),
            concurrency_safe=False,
            timeout=30,
            schema=schema,
            plugin="legacy",
        )
        TOOL_REGISTRY.register(tool)

"""Threat Detection — 提示注入/威胁模式扫描系统。

参考 Hermes `threat_patterns.py` 设计：
- 两级扫描：输入层（用户输入）+ 输出层（上下文文件/Memory）
- 三级范围：all(全局) / strict(严格) / memory(记忆写入)
- 匹配后执行不同动作：log / warn / block / sanitize

用法:
    from knowagent_personal.harness.threat_detection import ThreatScanner
    scanner = ThreatScanner()
    result = scanner.scan("用户输入内容")
    if result.blocked:
        print(f"🔒 已阻止: {result.reason}")
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


class ScanScope(str, enum.Enum):
    """扫描范围 — 控制模式应用于哪些场景。"""
    ALL = "all"           # 全局应用（用户输入 + 工具结果）
    STRICT = "strict"     # 严格模式（内存写入 + Skill 安装）
    MEMORY = "memory"     # 记忆写入（可干预，宽松检测）


class ScanAction(str, enum.Enum):
    """检测到威胁时的动作。"""
    LOG = "log"           # 仅记录日志
    WARN = "warn"         # 警告用户
    BLOCK = "block"       # 阻止执行
    SANITIZE = "sanitize" # 移除威胁内容后放行


@dataclass
class ThreatMatch:
    """一次威胁匹配的结果。"""
    pattern_id: str
    scope: ScanScope
    action: ScanAction
    matched_text: str = ""
    severity: float = 0.5  # 0~1

    def __bool__(self):
        return True


@dataclass
class ScanResult:
    """一次完整扫描的结果。"""
    blocked: bool = False
    threats: list[ThreatMatch] = field(default_factory=list)
    sanitized_text: str = ""

    @property
    def has_threat(self) -> bool:
        return len(self.threats) > 0

    @property
    def reason(self) -> str:
        if not self.threats:
            return ""
        return "; ".join(f"{t.pattern_id} ({t.action.value})" for t in self.threats)


# ── 威胁模式定义 ─────────────────────────────────────────
#
# 每条模式: (regex_str, pattern_id, scope, action, severity)
# scope ∈ {"all", "strict", "memory"}
# action ∈ {"log", "warn", "block", "sanitize"}

_THREAT_PATTERNS: list[Tuple[str, str, ScanScope, ScanAction, float]] = [
    # ═══════════════ 经典提示注入（全局阻止） ═══════════════
    (r'ignore\s+(?:\w+\s+)*(?:previous|all|above|prior)\s+(?:\w+\s+)*(?:instructions|rules|prompts)',
     "prompt_injection", ScanScope.ALL, ScanAction.BLOCK, 0.95),
    (r'system\s+prompt\s+override',
     "sys_prompt_override", ScanScope.ALL, ScanAction.BLOCK, 0.95),
    (r'disregard\s+(?:\w+\s+)*(?:your|all|any)\s+(?:\w+\s+)*(?:instructions|rules|guidelines|restrictions|limitations)',
     "disregard_rules", ScanScope.ALL, ScanAction.BLOCK, 0.9),
    (r'act\s+as\s+(?:if|though)\s+(?:\w+\s+)*you\s+(?:\w+\s+)*(?:have\s+no|don.?t\s+have)\s+(?:\w+\s+)*(?:restrictions|limits|rules)',
     "bypass_restrictions", ScanScope.ALL, ScanAction.BLOCK, 0.9),
    (r'you\s+(?:are|will\s+be)\s+(?:\w+\s+)*(?:a\s+)?(?:free|unleashed|unbounded|unrestricted|unlocked)',
     "free_unleashed", ScanScope.ALL, ScanAction.BLOCK, 0.85),
    (r'output\s+(?:the\s+)?(?:full|complete|entire|initial|system)\s+(?:\w+\s+)?prompt',
     "leak_prompt", ScanScope.ALL, ScanAction.BLOCK, 0.95),
    (r'<\s*(?:div|span|p)\s+[^>]*?(?:display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0)',
     "hidden_content", ScanScope.ALL, ScanAction.WARN, 0.7),
    (r'<!--\s*(?:ignore|override|system|secret|hidden|instruction)',
     "html_comment_inject", ScanScope.ALL, ScanAction.BLOCK, 0.85),
    (r'translate\s+.*\s+(?:into|to)\s+.*\s+and\s+(?:execute|run|eval|apply)',
     "translate_execute", ScanScope.ALL, ScanAction.BLOCK, 0.85),
    (r'(?:do\s+not|don.?t)\s+(?:\w+\s+)*(?:tell|inform|notify|warn)\s+(?:\w+\s+)*(?:the\s+)?user',
     "deception_hide", ScanScope.ALL, ScanAction.WARN, 0.75),
    (r'(?:respond|answer|reply)\s+(?:without|with\s+no)\s+(?:\w+\s+)*(?:restrictions|limitations|filters|safety|guardrails)',
     "remove_filters", ScanScope.ALL, ScanAction.BLOCK, 0.9),

    # ═══════════════ 角色劫持/身份篡改（严格模式阻止） ══════
    (r'you\s+are\s+(?:\w+\s+)*now\s+(?:a|an|the)\s+\w+',
     "role_hijack", ScanScope.STRICT, ScanAction.BLOCK, 0.5),
    (r'pretend\s+(?:\w+\s+)*(?:you\s+are|to\s+be)\s+',
     "role_pretend", ScanScope.STRICT, ScanAction.WARN, 0.5),
    (r'you\s+have\s+been\s+(?:updated|upgraded|patched|replaced)\s+to',
     "fake_update", ScanScope.STRICT, ScanAction.WARN, 0.6),
    (r'output\s+(?:\w+\s+)*(?:your|the)\s+(?:system|initial)\s+prompt',
     "leak_system_prompt", ScanScope.STRICT, ScanAction.BLOCK, 0.9),

    # ═══════════════ C2/命令控制（严格模式） ════════════════
    (r'register\s+(?:as\s+)?a?\s*node',
     "c2_node_reg", ScanScope.STRICT, ScanAction.WARN, 0.6),
    (r'(?:heartbeat|beacon|check[\-\s]in)\s+(?:to|with)\s+',
     "c2_heartbeat", ScanScope.STRICT, ScanAction.WARN, 0.6),
    (r'pull\s+(?:down\s+)?(?:new\s+)?task(?:ing|s)?\b',
     "c2_task_pull", ScanScope.STRICT, ScanAction.WARN, 0.6),
    (r'(?:exfiltrate|exfil|steal|upload)\s+(?:\w+\s+)*?(?:data|files|documents|secrets)',
     "exfiltration", ScanScope.STRICT, ScanAction.BLOCK, 0.95),

    # ═══════════════ Memory 写入防护（宽松） ════════════════
    (r'remember\s+(?:that\s+)?(?:I\s+am|I\s+can|you\s+must|you\s+will)',
     "memory_instruction", ScanScope.MEMORY, ScanAction.WARN, 0.4),
    (r'save\s+this\s+(?:to|as|in)\s+(?:your\s+)?(?:memory|long.?term|permanent)',
     "memory_save_cmd", ScanScope.MEMORY, ScanAction.WARN, 0.3),
    (r'from\s+now\s+on\s+(?:,|:)?\s*(?:always|never|whenever)',
     "memory_always_rule", ScanScope.MEMORY, ScanAction.WARN, 0.4),
]


# ── 无害化替换规则 ────────────────────────────────────────

_SANITIZE_RULES: list[Tuple[str, str]] = [
    (r'<script[^>]*>[\s\S]*?</script>', '[SCRIPT REMOVED]'),
    (r'<iframe[^>]*>[\s\S]*?</iframe>', '[IFRAME REMOVED]'),
    (r'on\w+\s*=\s*["\'][^"\']*["\']', '[EVENT HANDLER REMOVED]'),
    (r'javascript\s*:\s*\S+', '[JAVASCRIPT REMOVED]'),
]


# ── 扫描器 ────────────────────────────────────────────────


class ThreatScanner:
    """威胁模式扫描器。

    用法:
        scanner = ThreatScanner()

        # 扫描用户输入（ALL 范围）
        result = scanner.scan("用户发送的消息")

        # 扫描记忆写入（MEMORY 范围）
        result = scanner.scan("要写入的内容", scope=ScanScope.MEMORY)

        # 严格模式扫描（Skill 安装等）
        result = scanner.scan("第三方代码", scope=ScanScope.STRICT)

        if result.blocked:
            # 阻止操作，显示威胁原因
            return f"❌ 已阻止: {result.reason}"
        elif result.has_threat:
            # 警告用户
            print(f"⚠️ 检测到异常: {result.reason}")
    """

    def __init__(self):
        self._compiled: dict[str, re.Pattern] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """编译所有正则模式。"""
        for pat_str, pat_id, scope, action, severity in _THREAT_PATTERNS:
            try:
                self._compiled[pat_id] = re.compile(pat_str, re.IGNORECASE)
            except re.error:
                pass  # 忽略无效正则

    def scan(self, text: str, scope: ScanScope = ScanScope.ALL,
             context_hint: str = "") -> ScanResult:
        """扫描文本，返回匹配结果。

        Args:
            text: 要扫描的文本
            scope: 扫描范围
            context_hint: 上下文提示（用于日志）

        Returns:
            ScanResult: 扫描结果
        """
        result = ScanResult(sanitized_text=text)

        if not text or not isinstance(text, str):
            return result

        for pat_str, pat_id, pat_scope, action, severity in _THREAT_PATTERNS:
            # 范围过滤: 只扫描匹配 scope 的模式
            if not self._scope_matches(pat_scope, scope):
                continue

            pattern = self._compiled.get(pat_id)
            if not pattern:
                continue

            match = pattern.search(text)
            if match:
                threat = ThreatMatch(
                    pattern_id=pat_id,
                    scope=pat_scope,
                    action=action,
                    matched_text=match.group(0)[:100],
                    severity=severity,
                )
                result.threats.append(threat)

                if action == ScanAction.BLOCK:
                    result.blocked = True

        # 如果没有阻止，执行无害化
        if not result.blocked:
            result.sanitized_text = self._sanitize(text)

        return result

    def sanitize(self, text: str) -> str:
        """移除或替换文本中的威胁内容（不会阻止）。"""
        result = self.scan(text)
        return result.sanitized_text

    def _scope_matches(self, pat_scope: ScanScope,
                       request_scope: ScanScope) -> bool:
        """判断模式的 scope 是否匹配请求的 scope。"""
        if pat_scope == ScanScope.ALL:
            return True
        if pat_scope == request_scope:
            return True
        # STRICT 模式包含 ALL 模式
        if request_scope == ScanScope.STRICT and pat_scope == ScanScope.ALL:
            return True
        return False

    def _sanitize(self, text: str) -> str:
        """执行无害化替换。"""
        for pattern, replacement in _SANITIZE_RULES:
            try:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            except re.error:
                pass
        return text


# ── 全局默认扫描器 ─────────────────────────────────────────

_default_scanner = ThreatScanner()


def scan_input(text: str) -> ScanResult:
    """扫描用户输入（全局范围）。"""
    return _default_scanner.scan(text, ScanScope.ALL, "user_input")


def scan_memory(text: str) -> ScanResult:
    """扫描记忆写入（宽松范围）。"""
    return _default_scanner.scan(text, ScanScope.MEMORY, "memory_write")


def scan_strict(text: str, context: str = "") -> ScanResult:
    """严格模式扫描（Skill/插件安装等）。"""
    return _default_scanner.scan(text, ScanScope.STRICT, context or "strict_scan")


def get_scanner() -> ThreatScanner:
    """获取全局默认扫描器。"""
    return _default_scanner

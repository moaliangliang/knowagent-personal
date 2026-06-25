"""Permission System — 拒绝优先（Deny-First）多层权限系统。

遵循 Claude Code 的 7 层纵深防御模型：
1. 工具预过滤（registry 层）
2. Deny-first 规则（本模块）
3. 权限模式约束（basic / normal / elevated / admin）
4. 用户级白名单/黑名单
5. 会话级一次性授权
6. 操作二次确认（破坏性操作）
7. Hook 拦截扩展点
"""

from __future__ import annotations

import enum
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .registry import ToolDef, PermissionLevel, TOOL_REGISTRY

# ── 权限模式 ──────────────────────────────────────────────


class PermissionMode(str, enum.Enum):
    """权限模式 — 从严格到宽松。

    对应 Claude Code: plan → default → acceptEdits → auto → dontAsk
    """
    PLAN = "plan"               # 所有操作需审批
    NORMAL = "normal"           # 标准交互式审批
    ACCEPT_EDITS = "accept_edits"  # 文件编辑自动批准
    ELEVATED = "elevated"       # 仅破坏性操作需确认
    TRUSTED = "trusted"         # 信任模式（几乎不提示）
    BYPASS = "bypass"           # 绕过大部分检查（开发用）


# ── 策略 — 权限评估结果 ──────────────────────────────────


@dataclass
class PermissionVerdict:
    """权限评估结果。"""
    allowed: bool                           # 是否允许
    reason: str = ""                        # 原因说明
    require_confirmation: bool = False      # 是否需要二次确认
    mode: str = "auto"                      # 审批模式


# ── 权限规则 ──────────────────────────────────────────────


@dataclass
class PermissionRule:
    """一条权限规则。

    遵循 deny-first 原则：
    - effect="deny" 且与 effect="allow" 冲突时，deny 胜出。
    """
    effect: str                    # "allow" | "deny"
    tool_name: str = "*"           # 工具名（支持 * 通配符）
    user: str = "*"                # 用户名
    reason: str = ""               # 规则说明


# ── 权限管理器 ────────────────────────────────────────────


class DenyFirstPolicy:
    """拒绝优先策略评估器。

    核心逻辑：Deny > Ask > Allow
    1. 如果有 deny 规则匹配 → 拒绝
    2. 如果有 allow 规则匹配 → 允许
    3. 都没有匹配 → 根据权限模式决定
    """

    def __init__(self):
        self._rules: list[PermissionRule] = []
        self._user_grants: dict[str, set[str]] = {}  # user -> set<tool_name>

    def add_rule(self, rule: PermissionRule) -> None:
        """添加一条规则。deny 规则的优先级高于 allow。"""
        self._rules.append(rule)

    def grant_user(self, user: str, tool_name: str) -> None:
        """为用户授予特定工具的权限。"""
        if user not in self._user_grants:
            self._user_grants[user] = set()
        self._user_grants[user].add(tool_name)

    def revoke_user(self, user: str, tool_name: str) -> None:
        """撤销用户的特定工具权限。"""
        grants = self._user_grants.get(user)
        if grants:
            grants.discard(tool_name)

    def evaluate(self, tool: ToolDef, user: str = "",
                 mode: PermissionMode = PermissionMode.NORMAL) -> PermissionVerdict:
        """评估工具是否可执行。

        评估顺序：
        1. 先检查 deny 规则（deny 优先）
        2. 再检查 allow 规则
        3. 最后按权限模式默认策略
        """
        name = tool.name

        # Step 1: Deny-first — 检查 deny 规则
        for rule in self._rules:
            if rule.effect != "deny":
                continue
            if not _match_pattern(rule.tool_name, name):
                continue
            if rule.user != "*" and rule.user != user:
                continue
            return PermissionVerdict(
                allowed=False,
                reason=rule.reason or f"工具 {name} 被策略拒绝",
            )

        # Step 2: 检查用户级授权
        user_grants = self._user_grants.get(user, set())
        if name in user_grants:
            return PermissionVerdict(allowed=True, reason="用户已授权")

        # Step 3: 按权限模式处理
        return self._mode_evaluate(tool, mode)

    def _mode_evaluate(self, tool: ToolDef,
                       mode: PermissionMode) -> PermissionVerdict:
        """按权限模式评估。

        权限阈值（auto-allow 的权限上限）:
        - PLAN:     无 (全部需审批)
        - NORMAL:   READ_ONLY (日常只读操作自动放行)
        - ACCEPT_EDITS: FILE_WRITE (文件编辑自动放行)
        - ELEVATED: 仅破坏性操作需确认
        - TRUSTED:  全部自动放行
        """
        level = tool.permission

        # 阈值定义: 该模式下自动放行的最大权限值
        _AUTO_ALLOW_MAX = {
            PermissionMode.PLAN: -1,                     # 无自动放行
            PermissionMode.NORMAL: PermissionLevel.MEDIA.value,  # ≤30 自动放行（含通知/音乐）
            PermissionMode.ACCEPT_EDITS: PermissionLevel.FILE_WRITE.value,  # ≤50
            PermissionMode.ELEVATED: PermissionLevel.ADMIN.value - 1,  # 仅破坏性需确认
            PermissionMode.TRUSTED: PermissionLevel.ADMIN.value,       # 全部放行
            PermissionMode.BYPASS: PermissionLevel.ADMIN.value,
        }

        auto_max = _AUTO_ALLOW_MAX.get(mode, PermissionLevel.BASIC.value)

        if level.value <= auto_max:
            return PermissionVerdict(allowed=True, reason=f"{mode.value} 模式允许")
        if mode == PermissionMode.ELEVATED and not tool.is_destructive:
            return PermissionVerdict(allowed=True, reason="ELEVATED 模式允许")
        if mode == PermissionMode.PLAN:
            return PermissionVerdict(
                allowed=False, reason="PLAN 模式下需要审批",
                require_confirmation=True,
            )
        return PermissionVerdict(
            allowed=False,
            reason=f"需要确认: {tool.name} (权限: {level.name})",
            require_confirmation=True,
        )


# ── 会话级一次性授权 ──────────────────────────────────────


class SessionGrant:
    """会话级一次性授权 — 权限恢复后不重建（同 Claude Code 设计）。"""

    def __init__(self):
        self._grants: dict[str, float] = {}  # tool_name -> expiry
        self._ttl = 300  # 默认5分钟过期

    def grant(self, tool_name: str, ttl: int | None = None) -> None:
        """授予一次性权限。"""
        self._grants[tool_name] = time.time() + (ttl or self._ttl)

    def check(self, tool_name: str) -> bool:
        """检查是否有有效授权。"""
        expiry = self._grants.get(tool_name)
        if expiry is None:
            return False
        if time.time() > expiry:
            self._grants.pop(tool_name, None)
            return False
        return True

    def revoke(self, tool_name: str) -> None:
        """撤销授权。"""
        self._grants.pop(tool_name, None)

    def revoke_all(self) -> None:
        """清空所有授权。"""
        self._grants.clear()


# ── 权限管理器（总入口） ──────────────────────────────────


class PermissionManager:
    """权限管理器 — 7 层纵深防御的总入口。

    用法:
        pm = PermissionManager()
        pm.set_mode(PermissionMode.NORMAL)

        verdict = pm.check("screenshot_analyze")
        if verdict.allowed:
            execute()
        elif verdict.require_confirmation:
            ask_user()
        else:
            reject()
    """

    def __init__(self):
        self.policy = DenyFirstPolicy()
        self.session = SessionGrant()
        self.mode: PermissionMode = PermissionMode.NORMAL
        self._current_user: str = ""

        # 内置 deny 规则：默认禁止破坏性操作
        self.policy.add_rule(PermissionRule(
            effect="deny",
            tool_name="workflow_execute",
            reason="工作流执行需明确授权",
        ))

    def set_mode(self, mode: PermissionMode | str) -> None:
        """设置权限模式。"""
        if isinstance(mode, str):
            mode = PermissionMode(mode)
        self.mode = mode

    def set_user(self, user: str) -> None:
        """设置当前用户。"""
        self._current_user = user

    def add_deny_rule(self, tool_pattern: str, reason: str = "") -> None:
        """添加 deny 规则（拒绝优先）。"""
        self.policy.add_rule(PermissionRule(
            effect="deny", tool_name=tool_pattern, reason=reason,
        ))

    def add_allow_rule(self, tool_pattern: str, user: str = "*") -> None:
        """添加 allow 规则。"""
        self.policy.add_rule(PermissionRule(
            effect="allow", tool_name=tool_pattern, user=user,
        ))

    def check(self, tool_name: str,
              require_confirm: bool = False) -> PermissionVerdict:
        """检查工具是否可执行。

        评估管道：
        1. 工具是否存在注册表中 → 不存在视为拒绝
        2. 会话级授权 → 有则直接通过
        3. 策略评估 → Deny-first
        4. 操作二次确认 → 破坏性操作
        """
        # Layer 1: 工具存在性检查
        tool = TOOL_REGISTRY.get(tool_name)
        if tool is None:
            return PermissionVerdict(
                allowed=False, reason=f"工具 {tool_name} 未注册",
            )

        # Layer 2: 会话级授权
        if self.session.check(tool_name):
            return PermissionVerdict(allowed=True, reason="会话已授权")

        # Layer 3: 策略评估 (Deny-First)
        verdict = self.policy.evaluate(tool, self._current_user, self.mode)

        # Layer 4: 破坏性操作二次确认
        if verdict.allowed and (require_confirm or tool.is_destructive):
            if self.mode.value < PermissionMode.TRUSTED.value:
                return PermissionVerdict(
                    allowed=False,
                    reason=f"破坏性操作需要确认: {tool.name}",
                    require_confirmation=True,
                )

        return verdict

    def grant_session(self, tool_name: str, ttl: int = 300) -> None:
        """给予会话级一次性授权。"""
        self.session.grant(tool_name, ttl)

    def export_rules(self) -> list[dict]:
        """导出规则列表（用于展示或持久化）。"""
        return [
            {"effect": r.effect, "tool": r.tool_name,
             "user": r.user, "reason": r.reason}
            for r in self.policy._rules
        ]

    def save_rules(self, path: str | Path) -> None:
        """持久化规则到文件。"""
        path = Path(path)
        data = {
            "rules": self.export_rules(),
            "mode": self.mode.value,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load_rules(self, path: str | Path) -> None:
        """从文件加载规则。"""
        path = Path(path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.policy._rules = []
            for r in data.get("rules", []):
                self.policy._rules.append(PermissionRule(**r))
            self.mode = PermissionMode(data.get("mode", "normal"))
        except Exception:
            pass


# ── 简便函数 ──────────────────────────────────────────────

_default_manager = PermissionManager()


def allow_for_user(user: str, tool_name: str) -> None:
    """为用户授权特定工具。"""
    _default_manager.add_allow_rule(tool_name, user)


def deny_for_user(user: str, tool_name: str) -> None:
    """禁止用户使用特定工具。"""
    _default_manager.add_deny_rule(tool_name, f"用户 {user} 被禁止使用 {tool_name}")


def check_permission(tool_name: str) -> PermissionVerdict:
    """检查工具权限（使用默认管理器）。"""
    return _default_manager.check(tool_name)


# ── 辅助函数 ──────────────────────────────────────────────


def _match_pattern(pattern: str, name: str) -> bool:
    """简单通配符匹配。支持 * 和 ?"""
    if pattern == "*":
        return True
    if "?" not in pattern and "*" not in pattern:
        return pattern == name

    import fnmatch
    return fnmatch.fnmatch(name, pattern)

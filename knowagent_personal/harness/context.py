"""Context Manager — 分级上下文管理。

遵循 Claude Code 的 Tiered Memory 设计：
- T0: 系统提示/身份定义（始终加载）
- T1: 当前会话上下文（最近 N 轮）
- T2: 用户偏好/配置（按需加载）
- T3: 知识库记忆（RAG 检索，按需获取）

以及 Compaction Pipeline：
1. Budget Reduction — 每轮消息大小上限
2. Snip — 裁剪早期历史
3. Summary — 压缩/摘要
"""

from __future__ import annotations

import enum
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from .events import EventBus


class MemoryTier(int, enum.Enum):
    """记忆层级 — 0 最优先，3 最可丢弃。"""
    AXIOM = 0       # 系统身份、能力边界（永不丢弃）
    SESSION = 1      # 当前会话上下文
    USER = 2         # 用户偏好和配置
    ARCHIVE = 3      # 历史存档/RAG 检索


@dataclass
class MemoryItem:
    """一条记忆条目。"""
    tier: MemoryTier
    key: str
    content: str
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class TieredMemory:
    """分级记忆存储。

    用法:
        mem = TieredMemory()

        # 写入系统身份（T0）
        mem.set(MemoryTier.AXIOM, "system_prompt", "你是 Mac Agent...")

        # 写入会话记录（T1）
        mem.set(MemoryTier.SESSION, "user:hello", "帮我看看系统状态")

        # 读取
        axioms = mem.get_tier(MemoryTier.AXIOM)

        # 压缩（丢弃最旧的 T3，保留最新的 T1）
        mem.compact(target_budget=2000)
    """

    def __init__(self, max_items: dict[MemoryTier, int] | None = None):
        self._store: dict[MemoryTier, dict[str, MemoryItem]] = {
            tier: {} for tier in MemoryTier
        }
        self._max_items = max_items or {
            MemoryTier.AXIOM: 20,      # 系统定义
            MemoryTier.SESSION: 200,    # 最近的对话
            MemoryTier.USER: 50,        # 用户配置
            MemoryTier.ARCHIVE: 1000,   # 历史（可大量）
        }
        self._index: dict[str, list[MemoryItem]] = {}  # keyword -> items

    def set(self, tier: MemoryTier, key: str, content: str,
            metadata: dict | None = None) -> None:
        """写入一条记忆。"""
        item = MemoryItem(
            tier=tier,
            key=key,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        self._store[tier][key] = item

        # 更新索引（从 content 提取关键词）
        self._index_item(item)

    def get(self, key: str, tier: MemoryTier | None = None) -> MemoryItem | None:
        """按 key 查找记忆。"""
        if tier:
            return self._store[tier].get(key)
        for t in MemoryTier:
            if key in self._store[t]:
                return self._store[t][key]
        return None

    def get_tier(self, tier: MemoryTier) -> list[MemoryItem]:
        """获取指定层级的所有记忆，按时间排序（最新的在前）。"""
        items = list(self._store[tier].values())
        items.sort(key=lambda x: x.timestamp, reverse=True)
        return items

    def search(self, query: str, max_results: int = 5) -> list[MemoryItem]:
        """按关键词搜索记忆（跨层级）。"""
        query_lower = query.lower()
        results: list[tuple[MemoryItem, int]] = []

        for tier in MemoryTier:
            for item in self._store[tier].values():
                score = 0
                # 精确匹配关键词
                if query_lower in item.content.lower():
                    score += 10
                # metadata 匹配
                for v in item.metadata.values():
                    if isinstance(v, str) and query_lower in v.lower():
                        score += 5
                if score > 0:
                    results.append((item, score))

        results.sort(key=lambda x: (-x[1], -x[0].timestamp))
        return [item for item, _ in results[:max_results]]

    def compact(self, target_budget: int = 4000) -> int:
        """压缩记忆，释放上下文预算。

        策略（从最不重要的层级开始丢弃）：
        1. ARCHIVE: 删除最旧的一半
        2. USER: 删除重复配置
        3. SESSION: 保留最近 N 条
        4. AXIOM: 永不丢弃

        返回释放的字符数。
        """
        freed = 0

        # 计算当前占用
        current = sum(
            len(item.content) for tier in MemoryTier
            for item in self._store[tier].values()
        )
        if current <= target_budget:
            return 0

        # Step 1: 压缩 ARCHIVE — 删除最旧的一半
        archive = self.get_tier(MemoryTier.ARCHIVE)
        if archive:
            half = len(archive) // 2
            for item in archive[half:]:
                freed += len(item.content)
                del self._store[MemoryTier.ARCHIVE][item.key]
            # 重新检查预算
            current -= freed
            if current <= target_budget:
                return freed

        # Step 2: 压缩 USER — 删除非必需配置
        user_items = self.get_tier(MemoryTier.USER)
        non_essential = [i for i in user_items if not i.key.startswith("essential.")]
        if non_essential:
            for item in non_essential:
                freed += len(item.content)
                del self._store[MemoryTier.USER][item.key]
            current -= sum(len(i.content) for i in non_essential)
            del non_essential
            if current <= target_budget:
                return freed

        # Step 3: 压缩 SESSION — 只保留最近一半
        session = self.get_tier(MemoryTier.SESSION)
        if session:
            keep = session[:len(session) // 2]
            removed = set(s.key for s in session[len(session) // 2:])
            for key in removed:
                if key in self._store[MemoryTier.SESSION]:
                    freed += len(self._store[MemoryTier.SESSION][key].content)
                    del self._store[MemoryTier.SESSION][key]
            current -= sum(
                len(self._store[MemoryTier.SESSION][k].content)
                for k in removed.intersection(self._store[MemoryTier.SESSION])
            )
            del removed

        return freed

    def clear_tier(self, tier: MemoryTier) -> int:
        """清空指定层级，返回清除的条目数。"""
        count = len(self._store[tier])
        self._store[tier].clear()
        return count

    @property
    def stats(self) -> dict:
        """记忆统计。"""
        return {
            tier.name: {
                "count": len(items),
                "chars": sum(len(i.content) for i in items.values()),
            }
            for tier, items in self._store.items()
        }

    def save_to_db(self, db_path: str | None = None):
        """将 T2 (USER) 层级持久化到 SQLite settings 表。

        用于跨会话保留用户偏好和配置。
        """
        if db_path is None:
            db_path = os.path.expanduser("~/.knowagent/personal.db")
        if not os.path.exists(os.path.dirname(db_path)):
            return
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            # 确保 settings 表存在
            conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            for key, item in self._store[MemoryTier.USER].items():
                data = json.dumps({
                    "content": item.content,
                    "metadata": item.metadata,
                }, ensure_ascii=False)
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (f"memory:{key}", data),
                )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def load_from_db(self, db_path: str | None = None):
        """从 SQLite 恢复 T2 (USER) 层级的持久化记忆。"""
        if db_path is None:
            db_path = os.path.expanduser("~/.knowagent/personal.db")
        if not os.path.exists(db_path):
            return
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT key, value FROM settings WHERE key LIKE 'memory:%'"
            ).fetchall()
            conn.close()
            for key, value in rows:
                try:
                    data = json.loads(value)
                    memory_key = key[7:]  # 去掉 "memory:" 前缀
                    self.set(
                        MemoryTier.USER, memory_key,
                        data.get("content", ""),
                        metadata=data.get("metadata", {}),
                    )
                except (json.JSONDecodeError, KeyError):
                    pass
        except Exception:
            pass

    def _index_item(self, item: MemoryItem) -> None:
        """从 content 提取关键词用于搜索。"""
        # 简单分词：以空格/标点分割
        import re
        words = set(re.findall(r'[\w一-鿿]{2,}', item.content))
        for word in words:
            if word not in self._index:
                self._index[word] = []
            if item not in self._index[word]:
                self._index[word].append(item)


# ── 上下文管理器 ──────────────────────────────────────────


class ContextManager:
    """上下文管理器 — 为 LLM 构建上下文。

    遵循 Claude Code 的 9 步上下文组装流程：
    1. System prompt
    2. 环境信息
    3. CLAUDE.md 等效配置
    4. 路径作用域规则
    5. 自动记忆
    6. 工具定义
    7. 对话历史
    8. 工具结果
    9. 压缩摘要
    """

    def __init__(self, memory: TieredMemory | None = None,
                 events: EventBus | None = None):
        self.memory = memory or TieredMemory()
        self.events = events
        self.system_prompt: str = ""
        self.max_history_turns = 20
        self._conversation: list[dict] = []

    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示（T0）。"""
        self.system_prompt = prompt
        self.memory.set(MemoryTier.AXIOM, "system_prompt", prompt)

    def add_user_message(self, content: str) -> None:
        """添加用户消息。"""
        msg = {"role": "user", "content": content}
        self._conversation.append(msg)
        self.memory.set(MemoryTier.SESSION, f"user:{time.time()}", content)

    def add_assistant_message(self, content: str) -> None:
        """添加助手消息。"""
        msg = {"role": "assistant", "content": content}
        self._conversation.append(msg)
        self.memory.set(MemoryTier.SESSION, f"assistant:{time.time()}", content)

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """添加工具执行结果。"""
        msg = {"role": "tool", "content": result, "name": tool_name}
        self._conversation.append(msg)

    def build_messages(self, extra_tools: list[dict] | None = None) -> list[dict]:
        """组装完整的消息数组（Claude Code 9 步流程）。"""
        messages: list[dict] = []

        # Step 1-2: System prompt + Environment
        env_info = self._build_env_info()
        system = self.system_prompt
        if env_info:
            system = f"{system}\n\n{env_info}"
        messages.append({"role": "system", "content": system})

        # Step 3-5: Memory context
        memory_context = self._build_memory_context()
        if memory_context:
            messages[-1]["content"] += f"\n\n{memory_context}"

        # Step 6: Tool definitions (caller provides)
        # Step 7: Conversation history (trimmed)
        history = self._trim_history()
        messages.extend(history)

        return messages

    def _build_env_info(self) -> str:
        """构建环境信息。"""
        import platform
        try:
            import psutil
            boot = int(time.time() - psutil.boot_time())
            days = boot // 86400
            return (
                f"## 环境\n"
                f"- 系统: macOS {platform.mac_ver()[0]}\n"
                f"- 主机: {platform.node()}\n"
                f"- 启动: {days}天前"
            )
        except Exception:
            return f"## 环境\n- 系统: macOS {platform.mac_ver()[0]}"

    def _build_memory_context(self) -> str:
        """构建记忆上下文（T0 + T2 按需）。"""
        parts = []

        # T0: 系统定义
        axioms = self.memory.get_tier(MemoryTier.AXIOM)
        for item in axioms:
            if item.key != "system_prompt":  # 已包含在 system prompt 中
                parts.append(item.content)

        # T2: 用户偏好（前 5 条）
        user_prefs = self.memory.get_tier(MemoryTier.USER)[:5]
        for item in user_prefs:
            parts.append(item.content)

        return "\n".join(parts)

    def _trim_history(self) -> list[dict]:
        """裁剪对话历史 —— 保留最近 N 轮 + 上下文摘要。"""
        if len(self._conversation) <= self.max_history_turns:
            return self._conversation

        # 保留最近的
        recent = self._conversation[-self.max_history_turns:]

        # 将最早的对话压缩为摘要
        older = self._conversation[:-self.max_history_turns]
        summary = self._summarize_old(older)
        if summary:
            recent.insert(0, {
                "role": "system",
                "content": f"## 历史对话摘要\n{summary}",
            })

        return recent

    def _summarize_old(self, messages: list[dict]) -> str:
        """将旧对话压缩为摘要。"""
        # 当前用简单统计，后续可集成 LLM 摘要
        user_count = sum(1 for m in messages if m["role"] == "user")
        return f"（前面还有 {user_count} 轮对话，已自动压缩）"

    def add_fact(self, key: str, content: str,
                 tier: MemoryTier = MemoryTier.SESSION) -> None:
        """添加一个事实到记忆。"""
        self.memory.set(tier, key, content)

    def remember(self, query: str) -> list[MemoryItem]:
        """搜索相关记忆。"""
        return self.memory.search(query)

    def reset(self) -> None:
        """重置会话上下文（保留 T0 和 T2）。"""
        self._conversation.clear()
        self.memory.clear_tier(MemoryTier.SESSION)
        self.memory.clear_tier(MemoryTier.ARCHIVE)
        if self.events:
            self.events.emit("context.reset")

"""Todo / 待办事项管理 — 本地 JSON 存储 + macOS Reminders 桥接。"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

TODO_FILE = os.path.expanduser("~/.zhixing/todos.json")
_REMINDERS_AVAILABLE = True


@dataclass
class TodoItem:
    id: int = 0
    title: str = ""
    done: bool = False
    priority: str = "medium"      # high / medium / low
    category: str = "general"
    due_date: str = ""            # YYYY-MM-DD
    created_at: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "done": self.done,
            "priority": self.priority,
            "category": self.category,
            "due_date": self.due_date,
            "created_at": self.created_at or datetime.now().isoformat()[:10],
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: dict) -> TodoItem:
        return TodoItem(
            id=d.get("id", 0),
            title=d.get("title", ""),
            done=d.get("done", False),
            priority=d.get("priority", "medium"),
            category=d.get("category", "general"),
            due_date=d.get("due_date", ""),
            created_at=d.get("created_at", ""),
            notes=d.get("notes", ""),
        )

    @property
    def icon(self) -> str:
        if self.done:
            return "✅"
        return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(self.priority, "🟡")

    @property
    def sort_key(self) -> tuple:
        """排序：未完成 > 已完成；优先级高 > 低；创建时间新 > 旧。"""
        prio = {"high": 0, "medium": 1, "low": 2}
        return (self.done, prio.get(self.priority, 1), -(self.id))


class TodoManager:
    """待办事项管理器。"""
    _instance = None

    def __init__(self):
        self._todos: list[TodoItem] = []
        self._next_id = 1
        self._load()

    @classmethod
    def get(cls) -> TodoManager:
        if cls._instance is None:
            cls._instance = TodoManager()
        return cls._instance

    # ── CRUD ──

    def add(self, title: str, priority: str = "medium",
            category: str = "general", due_date: str = "",
            notes: str = "") -> TodoItem:
        item = TodoItem(
            id=self._next_id,
            title=title,
            priority=priority if priority in ("high", "medium", "low") else "medium",
            category=category or "general",
            due_date=due_date,
            created_at=datetime.now().isoformat()[:10],
            notes=notes,
        )
        self._todos.append(item)
        self._next_id += 1
        self._save()
        return item

    def list(self, category: str = "", include_done: bool = False) -> list[TodoItem]:
        items = self._todos
        if not include_done:
            items = [t for t in items if not t.done]
        if category:
            items = [t for t in items if t.category == category]
        items.sort(key=lambda t: t.sort_key)
        return items

    def done(self, item_id: int) -> bool:
        for t in self._todos:
            if t.id == item_id:
                t.done = True
                self._save()
                return True
        return False

    def undo(self, item_id: int) -> bool:
        for t in self._todos:
            if t.id == item_id:
                t.done = False
                self._save()
                return True
        return False

    def delete(self, item_id: int) -> bool:
        self._todos = [t for t in self._todos if t.id != item_id]
        self._save()
        return True

    def delete_all_pending(self) -> list[TodoItem]:
        """删除所有未完成的待办，返回被删除的列表。"""
        deleted = [t for t in self._todos if not t.done]
        self._todos = [t for t in self._todos if t.done]
        self._save()
        return deleted

    def update(self, item_id: int, **kwargs) -> bool:
        for t in self._todos:
            if t.id == item_id:
                for k, v in kwargs.items():
                    if hasattr(t, k):
                        setattr(t, k, v)
                self._save()
                return True
        return False

    def stats(self) -> dict:
        total = len(self._todos)
        done = sum(1 for t in self._todos if t.done)
        pending = total - done
        high = sum(1 for t in self._todos if t.priority == "high" and not t.done)
        return {"total": total, "done": done, "pending": pending, "high_priority": high}

    def format_list(self, items: list[TodoItem] | None = None) -> str:
        """格式化为可读文本。"""
        if items is None:
            items = self.list()
        if not items:
            return "📋 暂无待办事项"
        lines = [f"📋 待办事项 ({len(items)} 项):"]
        for t in items:
            due = f" 📅{t.due_date}" if t.due_date else ""
            cat = f" [{t.category}]" if t.category != "general" else ""
            lines.append(f"  {t.icon} #{t.id} {t.title}{cat}{due}")
            if t.notes:
                lines.append(f"     📝 {t.notes[:40]}")
        return "\n".join(lines)

    # ── 持久化 ──

    def _load(self):
        if not os.path.exists(TODO_FILE):
            return
        try:
            with open(TODO_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self._todos = [TodoItem.from_dict(d) for d in data.get("items", [])]
            self._next_id = data.get("next_id", 1)
        except Exception:
            self._todos = []
            self._next_id = 1

    def _save(self):
        os.makedirs(os.path.dirname(TODO_FILE), exist_ok=True)
        with open(TODO_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "next_id": self._next_id,
                "items": [t.to_dict() for t in self._todos],
            }, f, ensure_ascii=False, indent=2)

    # ── macOS Reminders 桥接 ──

    @staticmethod
    def sync_to_reminders(title: str, notes: str = "", due_date: str = "") -> str:
        """创建提醒事项，返回提醒 ID。"""
        safe_title = title.replace('"', '\\"').replace("\\", "\\\\")
        safe_notes = notes.replace('"', '\\"').replace("\\", "\\\\")
        props = f'{{name:"{safe_title}", body:"{safe_notes}"}}'
        script = f"""
        tell application "Reminders"
            set newReminder to make new reminder with properties {props}
            if "{due_date}" is not "" then
                set due date of newReminder to date "{due_date} 09:00:00"
            end if
            set idStr to id of newReminder
            return idStr
        end tell"""
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
            rid = r.stdout.strip()
            if rid.startswith("x-apple-reminder"):
                return f"✅ 提醒已创建|{rid}"
            return "✅ 已同步到提醒事项"
        except Exception as e:
            return f"⚠️ 同步失败: {e}"

    @staticmethod
    def _get_reminder_id(todo: TodoItem) -> str | None:
        """从 todo 的 notes 中提取提醒 ID。"""
        if not todo.notes:
            return None
        if todo.notes.startswith("rid:"):
            rid = todo.notes.split("rid:", 1)[1].strip()
            return f"x-apple-reminder://{rid}"
        return None

    @staticmethod
    def sync_complete_reminder(todo: TodoItem) -> str:
        """标记提醒事项为已完成。"""
        rid = TodoManager._get_reminder_id(todo)
        if not rid:
            return "⚠️ 无提醒ID（可能是旧数据，跳过）"
        script = f"""
        tell application "Reminders"
            try
                set target to reminder id "{rid}"
                set completed of target to true
                return "ok"
            on error
                return "not found"
            end try
        end tell"""
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
            return "✅ 提醒已标记完成" if "ok" in r.stdout else "⚠️ 提醒未找到"
        except Exception as e:
            return f"⚠️ 操作失败: {e}"

    @staticmethod
    def sync_delete_reminder(todo: TodoItem) -> str:
        """删除提醒事项。"""
        rid = TodoManager._get_reminder_id(todo)
        if not rid:
            return "⚠️ 无提醒ID（跳过）"
        script = f"""
        tell application "Reminders"
            try
                set target to reminder id "{rid}"
                delete target
                return "ok"
            on error
                return "not found"
            end try
        end tell"""
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
            return "✅ 提醒已删除" if "ok" in r.stdout else "⚠️ 提醒未找到"
        except Exception as e:
            return f"⚠️ 操作失败: {e}"

    @staticmethod
    def list_reminders() -> str:
        """列出 macOS 提醒事项。"""
        script = '''
        tell application "Reminders"
            set output to ""
            try
                set remindersList to every reminder
                repeat with r in remindersList
                    if completed of r is false then
                        set output to output & "  - " & name of r & return
                    end if
                end repeat
            end try
            return output
        end tell'''
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
            result = r.stdout.strip()
            return f"📋 macOS 提醒事项:\n{result}" if result else "📭 暂无提醒事项"
        except Exception:
            return "❌ 无法读取提醒事项"


# ── 快捷入口 ──

def cmd_todo_add(params: dict) -> str:
    """添加待办事项。:param title: 事项内容 :param priority: high/medium/low :param category: 分类 :param due_date: 截止日期 YYYY-MM-DD"""
    title = params.get("title") or params.get("text") or params.get("keyword", "")
    if not title:
        return "❌ 需要 title 参数"
    mgr = TodoManager.get()
    due = params.get("due_date", "")
    item = mgr.add(
        title=title,
        priority=params.get("priority", "medium"),
        category=params.get("category", "general"),
        due_date=due,
        notes=params.get("notes", ""),
    )
    # 同步到 macOS Reminders（含截止日期 + 提取提醒 ID）
    sync = params.get("sync", "true").lower() in ("true", "1", "yes")
    sync_result = ""
    if sync:
        result = mgr.sync_to_reminders(title, params.get("notes", ""), due)
        sync_result = "\n" + (result.split("|")[0] if "|" in result else result)
        # 提取提醒 ID 存入 notes
        if "|" in result:
            rid = result.split("|", 1)[1].strip()
            if rid.startswith("x-apple-reminder"):
                existing = params.get("notes", "")
                rid_short = rid.split("/")[-1].split("?")[0]
                mgr.update(item.id, notes=f"rid:{rid_short}")
    return f"✅ 已添加 #{item.id}: {title} ({item.priority}){sync_result}"


def cmd_todo_list(params: dict) -> str:
    """列出待办事项。:param category: 分类过滤 :param include_done: 是否包含已完成"""
    mgr = TodoManager.get()
    items = mgr.list(
        category=params.get("category", ""),
        include_done=params.get("include_done", "").lower() in ("true", "1", "yes"),
    )
    result = mgr.format_list(items)
    stats = mgr.stats()
    return f"{result}\n📊 总计 {stats['total']} | 待办 {stats['pending']} | 🔴 高优 {stats['high_priority']}"


def cmd_todo_done(params: dict) -> str:
    """标记待办完成。:param id: 事项编号"""
    item_id = int(params.get("id", 0))
    if not item_id:
        return "❌ 需要 id 参数"
    mgr = TodoManager.get()
    if mgr.done(item_id):
        # 同步完成提醒
        todo = next((t for t in mgr._todos if t.id == item_id), None)
        sync = ""
        if todo and todo.notes.startswith("x-apple-reminderkit:"):
            sync = "\n" + mgr.sync_complete_reminder(todo)
        return f"✅ #{item_id} 已标记完成 🎉{sync}"
    return f"❌ 未找到 #{item_id}"


def cmd_todo_undo(params: dict) -> str:
    """撤销完成标记。:param id: 事项编号"""
    item_id = int(params.get("id", 0))
    mgr = TodoManager.get()
    if mgr.undo(item_id):
        # 重新创建提醒
        todo = next((t for t in mgr._todos if t.id == item_id), None)
        sync = ""
        if todo:
            sync = "\n" + mgr.sync_to_reminders(todo.title, todo.notes, todo.due_date)
        return f"↩️ #{item_id} 已恢复为待办{sync}"
    return f"❌ 未找到 #{item_id}"


def cmd_todo_delete(params: dict) -> str:
    """删除待办事项。:param id: 事项编号（0=删除所有待办）"""
    mgr = TodoManager.get()
    item_id = int(params.get("id", 0))
    if item_id == 0:
        deleted = mgr.delete_all_pending()
        if deleted:
            # 同步删除提醒
            sync_results = []
            for t in deleted:
                if t.notes.startswith("x-apple-reminderkit:"):
                    sync_results.append(mgr.sync_delete_reminder(t))
            names = "\n".join(f"  🗑️ #{t.id} {t.title}" for t in deleted)
            sync_txt = "\n" + "\n".join(sync_results) if sync_results else ""
            return f"🗑️ 已删除 {len(deleted)} 项待办:\n{names}{sync_txt}"
        return "📭 没有待办事项需要删除"
    # 单条删除
    todo = next((t for t in mgr._todos if t.id == item_id), None)
    if mgr.delete(item_id):
        sync = ""
        if todo and todo.notes.startswith("x-apple-reminderkit:"):
            sync = "\n" + mgr.sync_delete_reminder(todo)
        return f"🗑️ #{item_id} 已删除{sync}"
    return f"❌ 未找到 #{item_id}"


def cmd_todo_reminders(params: dict) -> str:
    """列出 macOS 提醒事项。"""
    return TodoManager.list_reminders()

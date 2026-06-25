"""Skill Context — 技能注入到 Agent 上下文。

参考 Hermes `prompt_builder.py` 的 `build_skills_system_prompt()`:
- 扫描技能目录，解析 frontmatter
- 按平台/环境过滤
- 构建系统提示片段，注入到 context

KnowAgent 实现:
  SkillContext — 从 _auto/ 目录加载技能，构建上下文片段
  SkillUsageTracker — 跟踪技能使用频率和效果
"""

from __future__ import annotations

import datetime
import json
import os
import re
import time
from pathlib import Path
from typing import Any

AUTO_SKILL_DIR = os.path.expanduser("~/.knowagent/skills/_auto")
USAGE_LOG = os.path.expanduser("~/.knowagent/logs/skill_usage.jsonl")


class SkillContext:
    """技能上下文构建器。

    从自动创建的技能目录加载技能，构建 Agent 可读的上下文片段。
    每次启动时扫描，技能文件变更自动重载。
    """

    def __init__(self, max_skills: int = 10, max_chars: int = 2000):
        self.max_skills = max_skills
        self.max_chars = max_chars
        self._cache: str | None = None
        self._cache_mtime: float = 0
        os.makedirs(AUTO_SKILL_DIR, exist_ok=True)

    def build_prompt_section(self) -> str:
        """构建技能上下文片段，用于注入 system prompt。"""
        skills = self._load_skills()
        if not skills:
            return ""

        # 检查缓存是否有效
        current_mtime = self._dir_mtime()
        if self._cache and current_mtime == self._cache_mtime:
            return self._cache

        parts = ["\n## 🧠 自动技能库\n以下技能是从你的操作历史中自动学习的：\n"]
        char_count = 0

        for skill_name, content in skills[:self.max_skills]:
            section = self._format_skill(skill_name, content)
            if char_count + len(section) > self.max_chars:
                parts.append(f"\n*还有 {len(skills) - len(parts) + 1} 个技能未显示*\n")
                break
            parts.append(section)
            char_count += len(section)

        self._cache = "\n".join(parts)
        self._cache_mtime = current_mtime
        return self._cache

    def find_skill_for_task(self, task_description: str) -> list[dict]:
        """为任务查找匹配的技能。关键词匹配。"""
        results = []
        keywords = re.findall(r'[\w一-鿿]{2,}', task_description.lower())
        for skill_name, content in self._load_skills():
            score = 0
            content_lower = content.lower()
            for kw in keywords:
                if kw in content_lower:
                    score += 1
            if score > 0:
                results.append({
                    "name": skill_name,
                    "score": score,
                    "preview": self._extract_purpose(content),
                })
        results.sort(key=lambda x: -x["score"])
        return results[:5]

    def _load_skills(self) -> list[tuple[str, str]]:
        """加载所有自动技能。"""
        if not os.path.isdir(AUTO_SKILL_DIR):
            return []
        results = []
        for fname in sorted(os.listdir(AUTO_SKILL_DIR)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(AUTO_SKILL_DIR, fname)
            try:
                content = Path(fpath).read_text(encoding="utf-8")
                results.append((fname[:-3], content))
            except Exception:
                continue
        return results

    def _format_skill(self, name: str, content: str) -> str:
        """格式化为上下文片段。"""
        purpose = self._extract_purpose(content)
        steps = self._extract_steps(content)
        tools = self._extract_tools(content)
        lines = [f"\n### {name}"]
        if purpose:
            lines.append(f"  用途: {purpose}")
        if tools:
            lines.append(f"  工具: {', '.join(tools[:5])}")
        if steps:
            lines.append(f"  步骤: {steps}")
        return "\n".join(lines)

    def _extract_purpose(self, content: str) -> str:
        """从技能文件提取用途描述。"""
        m = re.search(r'## 用途\n\n(.+)', content)
        return m.group(1).strip() if m else ""

    def _extract_steps(self, content: str) -> str:
        """从技能文件提取步骤摘要。"""
        steps = re.findall(r'\d+\.\s*(.+?)(?:\n|$)', content)
        return " → ".join(s.strip()[:30] for s in steps[:4]) if steps else ""

    def _extract_tools(self, content: str) -> list[str]:
        """从技能文件提取涉及的工具。"""
        tools = re.findall(r'`([^`]+)`', content)
        return [t for t in tools if not t.startswith(("_", "#"))][:8]

    def _dir_mtime(self) -> float:
        """获取技能目录的最新修改时间。"""
        if not os.path.isdir(AUTO_SKILL_DIR):
            return 0
        try:
            return max(
                os.path.getmtime(os.path.join(AUTO_SKILL_DIR, f))
                for f in os.listdir(AUTO_SKILL_DIR)
                if f.endswith(".md")
            )
        except (ValueError, OSError):
            return 0

    @property
    def count(self) -> int:
        return len(self._load_skills())


class SkillUsageTracker:
    """技能使用跟踪器 — 记录技能被调用的频率和效果。

    用于决定:
    - 哪些技能应该保留/归档
    - 哪些技能需要改进
    - 哪些技能使用最频繁
    """

    def __init__(self):
        self._usage: dict[str, dict] = {}  # skill_name -> stats
        self._load()

    def record_use(self, skill_name: str, success: bool = True) -> None:
        """记录一次技能使用。"""
        now = time.time()
        if skill_name not in self._usage:
            self._usage[skill_name] = {
                "first_used": now,
                "last_used": now,
                "use_count": 0,
                "success_count": 0,
                "fail_count": 0,
            }
        s = self._usage[skill_name]
        s["last_used"] = now
        s["use_count"] += 1
        if success:
            s["success_count"] += 1
        else:
            s["fail_count"] += 1
        self._save()

    def get_stats(self, skill_name: str) -> dict | None:
        return self._usage.get(skill_name)

    def top_skills(self, n: int = 5) -> list[tuple[str, dict]]:
        """使用频率最高的技能。"""
        sorted_skills = sorted(
            self._usage.items(),
            key=lambda x: (-x[1]["use_count"], -x[1]["last_used"]),
        )
        return sorted_skills[:n]

    def stale_skills(self, days: int = 30) -> list[str]:
        """超过 N 天未使用的技能。"""
        cutoff = time.time() - days * 86400
        return [
            name for name, s in self._usage.items()
            if s["last_used"] < cutoff and s["use_count"] <= 3
        ]

    def _load(self) -> None:
        if not os.path.exists(USAGE_LOG):
            return
        try:
            with open(USAGE_LOG) as f:
                for line in f:
                    entry = json.loads(line.strip())
                    self.record_use(entry["skill"], entry.get("success", True))
        except Exception:
            pass

    def _save(self) -> None:
        os.makedirs(os.path.dirname(USAGE_LOG), exist_ok=True)
        try:
            with open(USAGE_LOG, "w") as f:
                for name, stats in self._usage.items():
                    f.write(json.dumps({"skill": name, **stats}, ensure_ascii=False) + "\n")
        except Exception:
            pass

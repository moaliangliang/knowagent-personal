"""Self-Improvement — 自主技能创建与自我进化循环。

参考 Hermes Agent 的 curator + background_review 设计：
- Hermes 每 15 步触发背景审查，自动创建/精炼技能文件
- 技能随使用进化，模型没变但代理变聪明

KnowAgent 实现:
  1. TurnRecorder      — 记录每轮执行历史
  2. SkillCreator      — 复杂任务完成后自动创建技能
  3. SkillRefiner      — 根据用户反馈精炼现有技能
  4. SelfInspector     — 定期自我审查 (每 N 轮)

用法:
    from knowagent_personal.harness.self_improvement import SelfImprovementLoop
    loop = SelfImprovementLoop()
    loop.record_turn(tool_history, user_input, response)
    loop.maybe_review()  # 自动判断是否需要审查
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("knowagent.self_improvement")

# ── 配置常量 ─────────────────────────────────────────────

SKILL_DIR = os.path.expanduser("~/.knowagent/skills")
AUTO_SKILL_DIR = os.path.join(SKILL_DIR, "_auto")  # 自动生成的技能
REVIEW_INTERVAL = 10          # 每 N 轮执行一次自我审查
COMPLEX_THRESHOLD = 5         # ≥ N 次工具调用视为"复杂任务"
MIN_IDLE_SECONDS = 10         # 审查前至少空闲 N 秒


# ═══════════════════════════════════════════════════════════
# 1. TurnRecorder — 执行历史记录
# ═══════════════════════════════════════════════════════════


@dataclass
class ToolCallRecord:
    """一次工具调用记录。"""
    tool_name: str
    params: dict
    result: str
    success: bool
    duration: float
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class TurnRecord:
    """一轮对话/执行记录。"""
    user_input: str
    response: str = ""
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    timestamp: float = 0.0
    duration: float = 0.0
    success: bool = True

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    @property
    def is_complex(self) -> bool:
        """是否复杂任务（≥ COMPLEX_THRESHOLD 次工具调用）。"""
        return len(self.tool_calls) >= COMPLEX_THRESHOLD

    @property
    def had_errors(self) -> bool:
        """是否有工具调用失败。"""
        return any(not tc.success for tc in self.tool_calls)

    @property
    def summary(self) -> str:
        """生成可读摘要。"""
        parts = [f"[{datetime.datetime.fromtimestamp(self.timestamp).strftime('%H:%M')}]"]
        parts.append(f"用户: {self.user_input[:60]}")
        if self.tool_calls:
            tools = ", ".join(tc.tool_name for tc in self.tool_calls)
            parts.append(f"工具: [{tools}]")
        parts.append(f"结果: {'✅' if self.success else '❌'}")
        return " | ".join(parts)


class TurnRecorder:
    """记录对话轮次历史，用于后续审查。"""

    def __init__(self, max_history: int = 100):
        self._turns: list[TurnRecord] = []
        self._max_history = max_history
        self._current_turn: TurnRecord | None = None

    def start_turn(self, user_input: str) -> None:
        """开始记录一轮。"""
        self._current_turn = TurnRecord(user_input=user_input, timestamp=time.time())

    def record_tool_call(self, tool_name: str, params: dict,
                         result: str, success: bool, duration: float) -> None:
        """记录一次工具调用。"""
        if self._current_turn is None:
            return
        self._current_turn.tool_calls.append(ToolCallRecord(
            tool_name=tool_name, params=params, result=str(result)[:500],
            success=success, duration=duration,
        ))

    def end_turn(self, response: str, success: bool = True) -> TurnRecord | None:
        """结束一轮，返回记录。"""
        if self._current_turn is None:
            return None
        self._current_turn.response = response
        self._current_turn.duration = time.time() - self._current_turn.timestamp
        self._current_turn.success = success
        turn = self._current_turn
        self._turns.append(turn)
        if len(self._turns) > self._max_history:
            self._turns = self._turns[-self._max_history:]
        self._current_turn = None
        return turn

    def recent_turns(self, n: int = 5) -> list[TurnRecord]:
        """最近 N 轮。"""
        return self._turns[-n:]

    @property
    def total_turns(self) -> int:
        return len(self._turns)

    def clear(self) -> None:
        self._turns.clear()
        self._current_turn = None


# ═══════════════════════════════════════════════════════════
# 2. SkillCreator — 自动创建技能
# ═══════════════════════════════════════════════════════════


class SkillCreator:
    """从复杂执行历史自动创建技能。

    触发条件:
    - 单轮 ≥ COMPLEX_THRESHOLD 次工具调用
    - 工具调用全部成功
    - 该模式尚未被已有技能覆盖
    """

    def __init__(self):
        os.makedirs(AUTO_SKILL_DIR, exist_ok=True)

    def should_create(self, turn: TurnRecord) -> bool:
        """判断是否值得为这轮创建技能。"""
        if not turn.is_complex:
            return False
        if turn.had_errors:
            return False
        # 检查是否已有类似技能
        existing = self._list_auto_skills()
        tool_set = set(tc.tool_name for tc in turn.tool_calls)
        for skill_name, skill_text in existing:
            if any(t in skill_text for t in tool_set):
                return False  # 已有类似技能
        return True

    def create_from_turn(self, turn: TurnRecord) -> str | None:
        """从一轮执行历史创建技能文件。"""
        if not self.should_create(turn):
            return None

        # 提取关键信息
        tool_chain = []
        for tc in turn.tool_calls:
            tool_chain.append(f"  - `{tc.tool_name}`: params={_summarize_params(tc.params)}")

        # 从用户输入提取技能名称
        skill_name = self._generate_name(turn.user_input)

        # 生成技能描述
        purpose = turn.user_input[:100].strip()
        steps = "\n".join(f"{i+1}. Execute `{tc.tool_name}` with {_summarize_params(tc.params)}"
                         for i, tc in enumerate(turn.tool_calls))

        skill_content = textwrap.dedent(f"""\
        # {skill_name}

        > 自动从对话创建 — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

        ## 用途

        {purpose}

        ## 步骤

        {steps}

        ## 涉及工具

        {chr(10).join(f"- `{tc.tool_name}`" for tc in turn.tool_calls)}

        ## 参数说明

        | 步骤 | 工具 | 参数 |
        |------|------|------|
        {chr(10).join(f"| {i+1} | `{tc.tool_name}` | {_summarize_params(tc.params)} |" for i, tc in enumerate(turn.tool_calls))}

        ---
        _自动创建于 {datetime.datetime.now().isoformat()}_
        """)

        # 写入文件
        filepath = os.path.join(AUTO_SKILL_DIR, f"{skill_name}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(skill_content)

        logger.info(f"自创技能: {skill_name} ({len(turn.tool_calls)} 步)")
        return skill_name

    def create_from_tool_pattern(self, pattern_name: str, tools: list[dict],
                                 description: str) -> str:
        """从工具调用模式创建技能（供外部调用）。"""
        skill_content = textwrap.dedent(f"""\
        # {pattern_name}

        > 自动创建 — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

        ## 用途

        {description}

        ## 步骤

        {chr(10).join(f"{i+1}. Execute `{t['tool']}`" for i, t in enumerate(tools))}

        ## 涉及工具

        {chr(10).join(f"- `{t['tool']}`" for t in tools)}
        ---
        _自动创建_
        """)

        safe_name = re.sub(r'[^\w\-_]', '_', pattern_name.lower())
        filepath = os.path.join(AUTO_SKILL_DIR, f"{safe_name}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(skill_content)

        return safe_name

    def _generate_name(self, user_input: str) -> str:
        """从用户输入生成技能名。"""
        # 取前 4 个中文字或前 6 个英文字符
        cleaned = re.sub(r'[^\w一-鿿]', '', user_input)[:12]
        if not cleaned:
            cleaned = f"skill_{int(time.time())}"
        return cleaned.lower()

    def _list_auto_skills(self) -> list[tuple[str, str]]:
        """列出已创建的自动技能。"""
        if not os.path.isdir(AUTO_SKILL_DIR):
            return []
        results = []
        for fname in sorted(os.listdir(AUTO_SKILL_DIR)):
            if fname.endswith(".md"):
                fpath = os.path.join(AUTO_SKILL_DIR, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        content = f.read()
                    results.append((fname[:-3], content))
                except Exception:
                    continue
        return results

    @property
    def count(self) -> int:
        return len(self._list_auto_skills())


# ═══════════════════════════════════════════════════════════
# 3. SkillRefiner — 技能精炼
# ═══════════════════════════════════════════════════════════


class SkillRefiner:
    """基于用户反馈精炼现有技能。

    用户反馈方式:
    - 隐式: 执行成功/失败的比率
    - 显式: feedback("技能名", "有用/无用/需改进")
    """

    def __init__(self):
        self._feedback_log: list[dict] = []

    def record_feedback(self, skill_name: str, rating: str,
                        comment: str = "") -> None:
        """记录用户对技能的反馈。"""
        entry = {
            "skill": skill_name,
            "rating": rating,  # "helpful" | "not_helpful" | "needs_improvement"
            "comment": comment,
            "timestamp": time.time(),
        }
        self._feedback_log.append(entry)
        self._persist_feedback()

        # 负面反馈 → 尝试精炼
        if rating == "needs_improvement" and comment:
            self._patch_skill(skill_name, comment)

        logger.info(f"技能反馈 [{skill_name}]: {rating}")

    def refine_from_turn(self, turn: TurnRecord) -> list[str]:
        """从执行历史中发现技能改进点。"""
        improvements = []
        if not turn.tool_calls:
            return improvements

        # 检查成功率
        success_rate = sum(1 for tc in turn.tool_calls if tc.success) / len(turn.tool_calls)
        if success_rate < 0.8 and len(turn.tool_calls) >= 3:
            # 低成功率 → 建议创建新技能记录失败模式
            improvements.append(f"发现执行模式成功率仅 {success_rate:.0%}")

        # 检查重复错误
        errors = [tc for tc in turn.tool_calls if not tc.success]
        error_tools = set(tc.tool_name for tc in errors)
        if error_tools:
            for tool in error_tools:
                improvements.append(f"工具 `{tool}` 执行失败，建议检查参数或 Windchill 状态")

        return improvements

    def _patch_skill(self, skill_name: str, comment: str) -> None:
        """根据反馈修补技能文件。"""
        # 在自动技能目录查找
        fpath = os.path.join(AUTO_SKILL_DIR, f"{skill_name}.md")
        if not os.path.exists(fpath):
            # 在用户技能目录查找
            fpath = os.path.join(SKILL_DIR, f"{skill_name}.py")
            if not os.path.exists(fpath):
                return

        if fpath.endswith(".md"):
            try:
                with open(fpath, "a", encoding="utf-8") as f:
                    f.write(f"\n## 改进记录\n\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {comment}\n")
            except Exception:
                pass

    def _persist_feedback(self) -> None:
        """持久化反馈日志。"""
        log_file = os.path.expanduser("~/.knowagent/logs/skill_feedback.jsonl")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(self._feedback_log[-1], ensure_ascii=False) + "\n")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# 4. SelfInspector — 定期自我审查
# ═══════════════════════════════════════════════════════════


class SelfInspector:
    """定期自我审查 — 每 N 轮执行一次。

    审查内容:
    1. 是否有可自动化的重复模式 → 创建技能
    2. 是否有经常失败的工具 → 记录问题
    3. 是否有不再使用的技能 → 建议清理
    """

    def __init__(self, turn_recorder: TurnRecorder,
                 skill_creator: SkillCreator,
                 skill_refiner: SkillRefiner):
        self.recorder = turn_recorder
        self.creator = skill_creator
        self.refiner = skill_refiner
        self._last_review_at = 0
        self._review_count = 0

    @property
    def should_review(self) -> bool:
        """是否应该执行审查。"""
        if self.recorder.total_turns < REVIEW_INTERVAL:
            return False
        if self.recorder.total_turns - self._last_review_at < REVIEW_INTERVAL:
            return False
        return True

    def review(self) -> list[str]:
        """执行自我审查，返回改进建议列表。"""
        if not self.should_review:
            return []

        self._review_count += 1
        self._last_review_at = self.recorder.total_turns
        findings: list[str] = []

        # 1. 检查近期轮次中有无可自动化的模式
        recent = self.recorder.recent_turns(REVIEW_INTERVAL)
        complex_turns = [t for t in recent if t.is_complex and not t.had_errors]

        # 检查高频工具组合
        tool_combos: dict[str, int] = {}
        for turn in recent:
            key = " → ".join(tc.tool_name for tc in turn.tool_calls)
            if key and len(turn.tool_calls) >= 2:
                tool_combos[key] = tool_combos.get(key, 0) + 1

        for combo, count in sorted(tool_combos.items(), key=lambda x: -x[1]):
            if count >= 2:
                # 重复出现的工具链 → 建议创建技能
                tools_in_combo = combo.split(" → ")
                safe_name = "_".join(t.split("_")[0] if "_" in t else t for t in tools_in_combo[:3])
                skill_name = self.creator.create_from_tool_pattern(
                    f"auto_{safe_name}_{self._review_count}",
                    [{"tool": t} for t in tools_in_combo],
                    f"自动从重复模式创建: {combo}",
                )
                findings.append(f"📝 发现重复模式: {combo} → 创建技能 [{skill_name}]")

        # 2. 检查复杂任务
        for turn in complex_turns[:3]:
            skill_name = self.creator.create_from_turn(turn)
            if skill_name:
                findings.append(f"📝 复杂任务已编码为技能: {skill_name}")

        # 3. 检查错误模式
        error_tools: dict[str, int] = {}
        for turn in recent:
            for tc in turn.tool_calls:
                if not tc.success:
                    error_tools[tc.tool_name] = error_tools.get(tc.tool_name, 0) + 1
        for tool, count in sorted(error_tools.items(), key=lambda x: -x[1]):
            if count >= 2:
                findings.append(f"⚠️ 工具 `{tool}` 近期失败 {count} 次")

        # 4. 汇总
        if findings:
            summary = f"\n🔍 第 {self._review_count} 次自我审查 (第 {self.recorder.total_turns} 轮):"
            for f in findings:
                summary += f"\n  {f}"
            logger.info(summary)
            print(summary)

        return findings


# ═══════════════════════════════════════════════════════════
# 5. SelfImprovementLoop — 整合入口
# ═══════════════════════════════════════════════════════════


class SelfImprovementLoop:
    """自主进化循环 — 整合记录、创建、精炼、审查。

    用法:
        loop = SelfImprovementLoop()
        # 在每次工具调用时:
        loop.record_tool_call(...)
        # 在每轮结束时:
        loop.end_turn(user_input, response)
        # 自动触发审查（每 REVIEW_INTERVAL 轮）:
        findings = loop.maybe_review()
    """

    def __init__(self):
        self.recorder = TurnRecorder()
        self.creator = SkillCreator()
        self.refiner = SkillRefiner()
        self.inspector = SelfInspector(self.recorder, self.creator, self.refiner)

    def start_turn(self, user_input: str) -> None:
        """开始记录一轮对话。"""
        self.recorder.start_turn(user_input)

    def record_tool_call(self, tool_name: str, params: dict,
                         result: str, success: bool, duration: float = 0.0) -> None:
        """记录一次工具调用。"""
        self.recorder.record_tool_call(tool_name, params, result, success, duration)

    def end_turn(self, user_input: str, response: str,
                 success: bool = True) -> TurnRecord | None:
        """结束当前轮次。"""
        turn = self.recorder.end_turn(response, success)
        if turn and turn.is_complex and not turn.had_errors and self.creator.should_create(turn):
            created = self.creator.create_from_turn(turn)
            if created:
                logger.info(f"自创技能: {created}")
        return turn

    def feedback(self, skill_name: str, rating: str, comment: str = "") -> None:
        """记录用户反馈。"""
        self.refiner.record_feedback(skill_name, rating, comment)

    def maybe_review(self) -> list[str]:
        """检查并执行自我审查。"""
        if self.inspector.should_review:
            return self.inspector.review()
        return []

    def suggestions(self, turn: TurnRecord | None = None) -> list[str]:
        """获取改进建议。"""
        if turn is None:
            turn = self.recorder.recent_turns(1)[0] if self.recorder._turns else None
        if turn is None:
            return []
        return self.refiner.refine_from_turn(turn)

    @property
    def stats(self) -> dict:
        """统计信息。"""
        return {
            "total_turns": self.recorder.total_turns,
            "auto_skills": self.creator.count,
            "reviews_done": self.inspector._review_count,
            "feedbacks": len(self.refiner._feedback_log),
        }


# ── 辅助函数 ─────────────────────────────────────────────


def _summarize_params(params: dict, max_len: int = 40) -> str:
    """摘要化参数（避免日志过长）。"""
    parts = []
    for k, v in params.items():
        if isinstance(v, str) and len(v) > max_len:
            parts.append(f"{k}={v[:max_len]}...")
        elif isinstance(v, str):
            parts.append(f"{k}={v}")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts) if parts else "(无参数)"

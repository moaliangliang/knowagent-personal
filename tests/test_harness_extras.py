"""Harness 扩展模块测试 — gateway, self_improvement, skill_context

覆盖模块:
  gateway.py           — 消息协议、WebSocket 适配器
  self_improvement.py  — 自我改进循环、TurnRecorder、SkillCreator
  skill_context.py     — 技能上下文构建、使用追踪
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════════
# gateway.py — 消息网关
# ═══════════════════════════════════════════════════════════

class TestGateway:
    """Gateway 消息协议与适配器测试"""

    def test_agent_message_from_dict(self):
        """AgentMessage 反序列化"""
        from zhixing.harness.gateway import AgentMessage
        data = {
            "type": "command",
            "content": "系统状态",
            "params": {},
            "source": "cli",
        }
        msg = AgentMessage.from_dict(data)
        assert msg.type == "command"
        assert msg.content == "系统状态"
        assert msg.source == "cli"

    def test_agent_message_minimal(self):
        """AgentMessage 最小字段"""
        from zhixing.harness.gateway import AgentMessage
        msg = AgentMessage.from_dict({"type": "chat"})
        assert msg.type == "chat"
        assert msg.content == ""
        assert msg.params == {}
        assert msg.source == "unknown"  # from_dict 默认值

    def test_agent_message_creation(self):
        """直接构造 AgentMessage"""
        from zhixing.harness.gateway import AgentMessage
        msg = AgentMessage(type="system", content="hello")
        assert msg.type == "system"
        assert msg.content == "hello"

    def test_websocket_adapter_import(self):
        """WebSocketAdapter 可导入和实例化"""
        from zhixing.harness.gateway import WebSocketAdapter
        adapter = WebSocketAdapter(host="127.0.0.1", port=0)
        assert adapter.host == "127.0.0.1"

    def test_websocket_adapter_lifecycle(self):
        """WebSocketAdapter 实例化（start/stop 是 async coroutine）"""
        from zhixing.harness.gateway import WebSocketAdapter
        adapter = WebSocketAdapter(host="127.0.0.1", port=0)
        assert adapter.host == "127.0.0.1"
        assert adapter.port == 0

    def test_gateway_creation(self):
        """Gateway 类可实例化"""
        from zhixing.harness.gateway import Gateway
        gateway = Gateway(agent=None)
        assert gateway is not None
        assert hasattr(gateway, "register")
        assert hasattr(gateway, "run")

    def test_adapter_registration(self):
        """适配器注册到 Gateway"""
        from zhixing.harness.gateway import Gateway, WebSocketAdapter
        gateway = Gateway(agent=None)
        adapter = WebSocketAdapter(host="127.0.0.1", port=0)
        gateway.register(adapter)
        assert len(gateway._adapters) >= 1

    def test_platform_adapter_base(self):
        """PlatformAdapter 基类接口"""
        from zhixing.harness.gateway import PlatformAdapter
        assert hasattr(PlatformAdapter, "start")
        assert hasattr(PlatformAdapter, "stop")

    def test_agent_message_defaults(self):
        """AgentMessage 默认值"""
        from zhixing.harness.gateway import AgentMessage
        msg = AgentMessage(type="")
        assert msg.type == ""
        assert msg.content == ""
        assert msg.params == {}


# ═══════════════════════════════════════════════════════════
# self_improvement.py — 自我改进
# ═══════════════════════════════════════════════════════════

class TestSelfImprovement:
    def test_turn_recorder_start_end(self):
        """TurnRecorder: start_turn → record_tool_call → end_turn"""
        from zhixing.harness.self_improvement import TurnRecorder
        recorder = TurnRecorder()
        assert recorder.total_turns == 0

        recorder.start_turn("测试输入")
        recorder.record_tool_call(
            tool_name="system_status",
            params={},
            result="CPU: OK",
            success=True,
            duration=0.5,
        )
        recorder.end_turn(response="系统正常", success=True)

        assert recorder.total_turns == 1
        recent = recorder.recent_turns(1)
        assert len(recent) == 1
        assert recent[0].user_input == "测试输入"
        assert len(recent[0].tool_calls) == 1

    def test_turn_recorder_multiple_turns(self):
        """TurnRecorder 多轮记录"""
        from zhixing.harness.self_improvement import TurnRecorder
        recorder = TurnRecorder()
        for i in range(3):
            recorder.start_turn(f"输入_{i}")
            recorder.record_tool_call(
                tool_name="test_tool",
                params={"idx": i},
                result="ok",
                success=True,
                duration=0.1,
            )
            recorder.end_turn(f"回复_{i}")
        assert recorder.total_turns == 3

    def test_turn_recorder_clear(self):
        """TurnRecorder 清空"""
        from zhixing.harness.self_improvement import TurnRecorder
        recorder = TurnRecorder()
        recorder.start_turn("test")
        recorder.end_turn("response")
        assert recorder.total_turns == 1
        recorder.clear()
        assert recorder.total_turns == 0

    def test_turn_recorder_max_history(self):
        """TurnRecorder 历史上限"""
        from zhixing.harness.self_improvement import TurnRecorder
        recorder = TurnRecorder(max_history=2)
        for i in range(5):
            recorder.start_turn(f"输入_{i}")
            recorder.end_turn(f"回复_{i}")
        assert recorder.total_turns == 2  # 只保留最近 2 轮

    def test_turn_record_dataclass(self):
        """TurnRecord 数据类属性"""
        from zhixing.harness.self_improvement import TurnRecord
        record = TurnRecord(user_input="test")
        assert record.user_input == "test"
        assert len(record.tool_calls) == 0
        assert record.response == ""
        assert record.success is True

    def test_turn_record_is_complex(self):
        """TurnRecord.is_complex 判断"""
        from zhixing.harness.self_improvement import TurnRecord, ToolCallRecord
        import time

        simple = TurnRecord(user_input="hi", timestamp=time.time())
        assert simple.is_complex is False  # 0 次工具调用

        complex_rec = TurnRecord(user_input="复杂任务", timestamp=time.time())
        for i in range(6):  # COMPLEX_THRESHOLD = 5
            complex_rec.tool_calls.append(ToolCallRecord(
                tool_name="tool", params={}, result="ok",
                success=True, duration=0.1,
            ))
        assert complex_rec.is_complex is True

    def test_skill_creator_init(self):
        """SkillCreator 初始化"""
        from zhixing.harness.self_improvement import SkillCreator
        creator = SkillCreator()
        assert creator is not None

    def test_self_improvement_loop(self):
        """SelfImprovementLoop 完整流程"""
        from zhixing.harness.self_improvement import SelfImprovementLoop
        loop = SelfImprovementLoop()
        assert loop is not None
        assert hasattr(loop, "start_turn")
        assert hasattr(loop, "record_tool_call")
        assert hasattr(loop, "end_turn")
        assert hasattr(loop, "maybe_review")

    def test_loop_start_end_turn(self):
        """SelfImprovementLoop: start → record → end"""
        from zhixing.harness.self_improvement import SelfImprovementLoop
        loop = SelfImprovementLoop()
        loop.start_turn("你好")
        loop.record_tool_call("system_status", {}, "ok", True, 0.2)
        turn = loop.end_turn("你好", "系统正常")
        assert turn is not None
        assert turn.user_input == "你好"
        assert len(turn.tool_calls) == 1
        assert loop.stats["total_turns"] == 1

    def test_loop_maybe_review_early(self):
        """maybe_review 在早期轮次返回空列表"""
        from zhixing.harness.self_improvement import SelfImprovementLoop
        loop = SelfImprovementLoop()
        findings = loop.maybe_review()
        assert isinstance(findings, list)

    def test_loop_feedback(self):
        """feedback 记录反馈"""
        from zhixing.harness.self_improvement import SelfImprovementLoop
        loop = SelfImprovementLoop()
        # 不崩溃即可
        loop.feedback("test_skill", "good", "工作正常")


# ═══════════════════════════════════════════════════════════
# skill_context.py — 技能上下文
# ═══════════════════════════════════════════════════════════

class TestSkillContext:
    def test_skill_context_init(self):
        """SkillContext 初始化"""
        from zhixing.harness.skill_context import SkillContext
        ctx = SkillContext(max_skills=5, max_chars=500)
        assert ctx is not None
        assert ctx.max_skills == 5
        assert ctx.max_chars == 500

    def test_build_prompt_section(self):
        """build_prompt_section 返回字符串"""
        from zhixing.harness.skill_context import SkillContext
        ctx = SkillContext()
        result = ctx.build_prompt_section()
        assert isinstance(result, str)

    def test_find_skill_for_task(self):
        """find_skill_for_task 返回列表"""
        from zhixing.harness.skill_context import SkillContext
        ctx = SkillContext()
        result = ctx.find_skill_for_task("screenshot")
        assert isinstance(result, list)

    def test_count(self):
        """count 属性返回整数"""
        from zhixing.harness.skill_context import SkillContext
        ctx = SkillContext()
        count = ctx.count  # 注意: @property
        assert isinstance(count, int)
        assert count >= 0

    def test_skill_usage_tracker_init(self):
        """SkillUsageTracker 初始化"""
        from zhixing.harness.skill_context import SkillUsageTracker
        tracker = SkillUsageTracker()
        assert tracker is not None

    def test_record_use(self):
        """record_use 记录不崩溃"""
        from zhixing.harness.skill_context import SkillUsageTracker
        tracker = SkillUsageTracker()
        tracker.record_use("test_skill", success=True)
        tracker.record_use("test_skill_2", success=False)
        stats = tracker.get_stats("test_skill")
        assert stats is not None
        assert stats["use_count"] >= 1

    def test_top_skills(self):
        """top_skills 返回列表"""
        from zhixing.harness.skill_context import SkillUsageTracker
        tracker = SkillUsageTracker()
        for i in range(5):
            tracker.record_use(f"skill_{i}", success=True)
        top = tracker.top_skills(n=3)
        assert isinstance(top, list)

    def test_stale_skills(self):
        """stale_skills 返回列表"""
        from zhixing.harness.skill_context import SkillUsageTracker
        tracker = SkillUsageTracker()
        result = tracker.stale_skills(days=1)
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import traceback

    tests = []
    for name, obj in list(globals().items()):
        if name.startswith("Test"):
            for mname in dir(obj):
                if mname.startswith("test_"):
                    tests.append((f"{name}.{mname}", getattr(obj(), mname)))

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            print(f"     {traceback.format_exc().split(chr(10))[-3]}")
            failed += 1

    total = passed + failed
    print(f"\n{'=' * 50}")
    print(f"  结果: {passed}/{total} 通过", end="")
    if failed:
        print(f", {failed} 失败")
    else:
        print()
    print(f"{'=' * 50}")

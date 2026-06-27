"""知行 AI Orchestrator — 自然语言 → 意图解析 → 工具调用 → 结果合成。

核心流程：
  用户输入 → LLM 解析意图 → 执行工具 → 结果送回 LLM → 合成回复

使用示例：
    orchestrator = Orchestrator()
    result = await orchestrator.process("帮我写今天的日报", history=[])
"""

import json
import os
from typing import Any

from zhixing.agent.llm_client import LLMClient
from zhixing.agent.tools import get_tool_definitions, COMMANDS

# ── System Prompt ──────────────────────────────────

SYSTEM_PROMPT = """你是一个 Mac 桌面 AI 助手「知行」。你的任务是理解用户的中文自然语言指令，将指令拆解为可执行的系统操作。

## 核心原则

1. 用户不需要懂技术，用日常语言描述需求即可。不要输出技术细节。
2. 如果需要多个操作才能完成用户请求，一步步来，执行完一个再执行下一个。
3. 执行操作前，先告诉用户你要做什么，让用户有心理预期。
4. 如果某个操作失败，给出友好的错误提示，不要直接抛异常。
5. 如果用户指令超出你的能力范围，明确告诉用户你不能做什么。

## 工具调用规则

- 总是使用简体中文回复用户。
- 每次调用一个工具，等结果返回后再决定下一步。
- 工具调用结果会以 system 角色的消息返回给你，据此判断下一步。
- 任务完成后，给用户一个清晰的总结。
- 如果用户只是聊天（问候、闲聊），直接回复，不需要调用任何工具。
- 如果用户意图不明确，主动询问澄清。
"""


# ── 执行上下文 ────────────────────────────────────

class ToolResult:
    """一次工具调用的结果记录。"""
    def __init__(self, name: str, args: dict, output: str, success: bool):
        self.name = name
        self.args = args
        self.output = output
        self.success = success

    def to_message(self) -> dict:
        """转换为 LLM 可读取的 tool result 消息。"""
        prefix = "✅" if self.success else "❌"
        return {
            "role": "tool",
            "content": f"{prefix} {self.name}({json.dumps(self.args, ensure_ascii=False)}):\n{self.output[:2000]}",
        }


# ── Orchestrator ──────────────────────────────────

# 允许 Orchestrator 调用的命令白名单（核心高频命令）
CORE_COMMANDS = {
    # 系统
    "system_status", "battery_status", "wifi_status", "notification",
    "speak", "open_app", "open_url", "lock_screen",
    # 文件
    "file_list", "file_search", "file_grep", "trash",
    # 剪贴板
    "clipboard_read", "clipboard_write",
    # 日历
    "calendar",
    # 邮件
    "mail_read", "mail_master", "mail_send",
    # 音乐
    "music_search_online", "music_play", "music_next", "music_stop",
    # 待办
    "todo_add", "todo_list", "todo_done", "todo_delete", "todo_reminders",
    # 键盘/输入
    "keyboard_type", "keyboard_press",
    # UI
    "ui_tree", "ui_click", "ui_find",
    # 截图
    "screenshot", "screenshot_analyze",
    # 提醒/笔记/联系人
    "reminder_add", "notes_list", "contacts_search",
    # 翻译
    "translate",
    # 联网
    "http_request", "speedtest",
}


class Orchestrator:
    """自然语言指令编排器。"""

    def __init__(self, llm_client: LLMClient | None = None):
        if llm_client:
            self.llm = llm_client
        else:
            # 优先级: env > config.yaml > 空
            from zhixing.config import Config
            cfg = Config()
            default_key = (
                os.environ.get("ZHIXING_API_KEY", "")
                or cfg.get("llm.api_key", "")
            )
            default_provider = (
                os.environ.get("ZHIXING_API_PROVIDER", "")
                or cfg.get("llm.provider", "deepseek")
            )
            default_base = (
                os.environ.get("ZHIXING_API_BASE", "")
                or cfg.get("llm.base_url", "")
            )
            self.llm = LLMClient(
                api_key=default_key,
                provider=default_provider,
                api_base=default_base,
            )
        self._tool_defs = None  # 懒加载

    def get_tools(self) -> list[dict]:
        """获取 LLM 可调用的工具定义（仅限白名单内）。"""
        if self._tool_defs is None:
            all_defs = get_tool_definitions()
            self._tool_defs = [
                d for d in all_defs
                if d["function"]["name"] in CORE_COMMANDS
            ]
        return self._tool_defs

    def execute_tool(self, name: str, args: dict) -> ToolResult:
        """执行一个工具调用，返回结果。"""
        handler = COMMANDS.get(name)
        if not handler:
            return ToolResult(
                name=name, args=args,
                output=f"命令 {name} 不存在",
                success=False,
            )

        try:
            output = handler(args)
            return ToolResult(
                name=name, args=args,
                output=str(output),
                success=True,
            )
        except Exception as e:
            return ToolResult(
                name=name, args=args,
                output=str(e),
                success=False,
            )

    async def process(
        self,
        user_input: str,
        history: list[dict] | None = None,
        max_tool_rounds: int = 5,
    ) -> dict:
        """处理用户输入并返回最终回复。

        Args:
            user_input: 用户输入的文本
            history: 历史对话 (OpenAI 格式, [{role, content}, ...])
            max_tool_rounds: 最大工具调用轮数（防止无限循环）

        Returns:
            {"reply": str, "tool_calls": [...], "error": bool}
        """
        messages = list(history or [])
        messages.append({"role": "user", "content": user_input})

        tool_calls_log = []
        round_count = 0

        while round_count < max_tool_rounds:
            round_count += 1

            # 1. 调用 LLM
            response = await self.llm.chat(
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
                tools=self.get_tools(),
                temperature=0.3,
            )

            if response.get("error"):
                return {
                    "reply": response.get("message", "❌ AI 响应失败"),
                    "tool_calls": tool_calls_log,
                    "error": True,
                }

            assistant_msg = response.get("choices", [{}])[0].get("message", {})
            content = assistant_msg.get("content", "")
            messages.append(assistant_msg)

            # 2. 检查是否有工具调用
            tool_calls = LLMClient.parse_tool_calls(response)

            if not tool_calls:
                # 没有工具调用 → LLM 直接回复文字
                return {
                    "reply": content or "好的，已处理完成。",
                    "tool_calls": tool_calls_log,
                    "error": False,
                }

            # 3. 执行工具调用
            for tc in tool_calls:
                result = self.execute_tool(tc["name"], tc["arguments"])
                tool_calls_log.append({
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                    "output": result.output[:200],
                    "success": result.success,
                })
                messages.append(result.to_message())

            # 4. 继续循环，让 LLM 决定下一步

        # 达到最大轮数，强制返回
        final = await self.llm.chat(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            temperature=0.5,
        )
        reply = LLMClient.get_reply(final) or "已完成所有操作。"
        return {
            "reply": reply,
            "tool_calls": tool_calls_log,
            "error": False,
        }

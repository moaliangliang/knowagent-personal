"""知行 AI Orchestrator — 自然语言 → 意图解析 → 工具调用 → 结果合成。

核心流程：
  用户输入 → 场景识别 → 场景引导 → LLM 解析 → 执行工具 → 合成回复

使用示例：
    orchestrator = Orchestrator()
    result = await orchestrator.process("帮我写今天的日报")
"""

import json
import os
import re
from typing import Any

from zhixing.agent.llm_client import LLMClient
from zhixing.agent.tools import get_tool_definitions, COMMANDS

# ── 场景识别 ──────────────────────────────────────

SCENE_PATTERNS: dict[str, list[str]] = {
    "daily_report": [
        r"日报", r"日报", r"工作汇报", r"工作总结", r"周报", r"月报",
        r"今天做了什么", r"今天的日报", r"写日报",
    ],
    "file_organize": [
        r"整理", r"归类", r"归档", r"分类", r"文件",
        r"桌面", r"下载", r"文件夹",
    ],
    "quick_email": [
        r"邮件", r"邮箱", r"收件箱", r"发邮件", r"回复",
        r"mail", r"email", r"inbox",
    ],
    "meeting_summary": [
        r"会议", r"开会", r"日程", r"日历", r"今天.*安排",
        r"meeting", r"calendar", r"日程",
    ],
    "system_query": [
        r"系统", r"状态", r"CPU", r"内存", r"磁盘", r"电池",
        r"网络", r"WiFi", r"进程", r"性能",
    ],
    "ai_assistant": [
        r"翻译", r"润色", r"总结", r"摘要", r"改写",
        r"翻译一下", r"翻成", r"英文怎么说",
    ],
}


def detect_scene(user_input: str) -> str:
    """检测用户输入属于哪个场景。"""
    for scene, patterns in SCENE_PATTERNS.items():
        for p in patterns:
            if re.search(p, user_input, re.IGNORECASE):
                return scene
    return "general"


# ── 场景 Prompt ───────────────────────────────────

SCENE_PROMPTS: dict[str, str] = {
    "daily_report": """## 场景：日报助手

用户的诉求是「写日报/周报/工作总结」。你需要按以下步骤执行：

### 步骤
1. 先告知用户"正在读取今天的日历、邮件和待办事项"
2. 调用 calendar() 获取今天的日程安排
3. 调用 mail_read(limit=5) 获取今日邮件
4. 调用 todo_list() 获取待办事项
5. 根据获取的信息，生成一份结构化的日报草稿

### 日报格式
```
📋 日报 — YYYY-MM-DD
━━━━━━━━━━━━━━━━━━
📅 今日日程
  • 09:00-10:00 团队晨会
  • 14:00-15:00 项目评审

📧 今日邮件（3封）
  • 张三 - 关于Q2计划（待回复）
  • 李四 - 会议纪要

✅ 今日完成
  • ...

📝 待办事项
  • 待完成 #1 ...

━━━━━━━━━━━━━━━━━━
[复制日报] [发送邮件]
```

生成后询问用户是否需要修改或直接发送。
""",

    "file_organize": """## 场景：文件整理助手

用户的诉求是「整理文件/归档/分类」。按以下步骤执行：

### 步骤
1. 先询问用户想整理哪个文件夹（默认 ~/Desktop）
2. 调用 file_list(path=...) 列出文件
3. 根据文件类型分类：
   - 图片: .png .jpg .jpeg .gif .webp
   - 文档: .pdf .doc .docx .xlsx .pptx
   - 压缩包: .zip .tar .gz .rar
   - 视频: .mp4 .mov .avi .mkv
   - 代码: .py .js .ts .html .css .json .md
4. 展示分类结果给用户确认
5. 用户确认后，调用相应的命令执行

输出格式：
```
📁 桌面文件整理 — 共 24 个文件
━━━━━━━━━━━━━━━━━━
🖼 图片 (8个) → 移动到 ~/Desktop/图片/
📄 文档 (6个) → 移动到 ~/Desktop/文档/
📦 压缩包 (3个) → 移动到 ~/Desktop/归档/
💻 代码 (4个) → 移动到 ~/Desktop/代码/
❓ 其他 (3个) → 保持不动

是否执行以上整理？ [确认执行] [修改]
```
""",

    "quick_email": """## 场景：快捷邮件

用户的诉求是「查看/回复/发送邮件」。按以下步骤执行：

### 查看邮件
1. 调用 mail_read(limit=5) 获取收件箱
2. 展示邮件列表，标记未读

### 回复邮件
1. 先调用 mail_read() 获取相关邮件内容
2. 根据用户要求生成回复草稿
3. 展示给用户确认
4. 调用 mail_send() 发送

### 发送新邮件
1. 确认收件人、主题、正文
2. 调用 mail_send(to=, subject=, body=) 发送

输出格式：
```
📧 收件箱
━━━━━━━━━━━━━━━━━━
📩 张三 - Q2计划更新 - 10:00
  "方案已更新，请查收附件"
📩 李四 - 会议纪要 - 昨天
  "昨日评审的会议纪要如下..."

━━━━━━━━━━━━━━━━━━
回复哪封邮件？或输入"发邮件给..."
```
""",

    "meeting_summary": """## 场景：会议摘要

用户的诉求是「查看日程/准备会议/了解今日安排」。按以下步骤执行：

### 步骤
1. 调用 calendar() 获取今日日程
2. 调用 mail_read(limit=3) 获取今日相关邮件
3. 调用 todo_list() 获取待办
4. 合成今日安排摘要

### 格式
```
📅 今日安排 — YYYY-MM-DD
━━━━━━━━━━━━━━━━━━
⏰ 日程
  • 10:00 团队晨会 (1h)
    参与人: 张三、李四
  • 14:00 产品评审 (2h) ← 需准备

📌 需要准备
  • 评审文档（来自邮件「产品评审材料 v2」）
  • #3 待办: 更新项目进度表

━━━━━━━━━━━━━━━━━━
```
""",

    "system_query": """## 场景：系统查询

用户的诉求是「查看电脑状态/性能/信息」。直接调用对应的系统命令即可。

### 映射
- "系统状态" / "看看电脑" → system_status()
- "电池" / "电量" → battery_status()
- "网络" / "WiFi" → wifi_status()

输出尽可能简洁直观，用 emoji 开头，不要加额外解释。
""",

    "ai_assistant": """## 场景：AI 助手

用户的诉求是「翻译/润色/改写/总结文本」。这类需求通常不需要调用系统工具。

### 处理方式
1. 如果用户提供了文本内容，直接处理
2. 如果用户没有提供文本但有剪贴板内容，调用 clipboard_read() 读取
3. 直接给出处理结果

### 翻译
- 默认翻译为中/英互译
- 如果用户说"翻成日文"，则翻译为日文
- 保留原文格式

### 润色
- 修正语法错误
- 优化表达
- 保持原意

### 总结/摘要
- 提取关键信息
- 保持简洁
- 用列表形式呈现
""",
}


# ── 基础 System Prompt ────────────────────────────

BASE_SYSTEM_PROMPT = """你是一个 Mac 桌面 AI 助手「知行」。你的任务是理解用户的中文自然语言指令，将指令拆解为可执行的系统操作。

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

CORE_COMMANDS = {
    "system_status", "battery_status", "wifi_status", "notification",
    "speak", "open_app", "open_url", "lock_screen",
    "file_list", "file_search", "file_grep", "trash",
    "clipboard_read", "clipboard_write",
    "calendar",
    "mail_read", "mail_master", "mail_send",
    "music_search_online", "music_play", "music_next", "music_stop",
    "todo_add", "todo_list", "todo_done", "todo_delete", "todo_reminders",
    "keyboard_type", "keyboard_press",
    "ui_tree", "ui_click", "ui_find",
    "screenshot", "screenshot_analyze",
    "reminder_add", "notes_list", "contacts_search",
    "translate",
    "http_request", "speedtest",
}


class Orchestrator:
    """自然语言指令编排器，带场景感知能力。"""

    def __init__(self, llm_client: LLMClient | None = None):
        if llm_client:
            self.llm = llm_client
        else:
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
        self._tool_defs = None

    def get_tools(self) -> list[dict]:
        if self._tool_defs is None:
            all_defs = get_tool_definitions()
            self._tool_defs = [
                d for d in all_defs
                if d["function"]["name"] in CORE_COMMANDS
            ]
        return self._tool_defs

    def execute_tool(self, name: str, args: dict) -> ToolResult:
        handler = COMMANDS.get(name)
        if not handler:
            return ToolResult(name=name, args=args, output=f"命令 {name} 不存在", success=False)
        try:
            output = handler(args)
            return ToolResult(name=name, args=args, output=str(output), success=True)
        except Exception as e:
            return ToolResult(name=name, args=args, output=str(e), success=False)

    def _build_system_prompt(self, user_input: str) -> str:
        """构建场景感知的系统提示。"""
        scene = detect_scene(user_input)
        scene_prompt = SCENE_PROMPTS.get(scene, "")
        if scene_prompt:
            return BASE_SYSTEM_PROMPT + "\n\n" + scene_prompt
        return BASE_SYSTEM_PROMPT

    async def process(
        self,
        user_input: str,
        history: list[dict] | None = None,
        max_tool_rounds: int = 5,
    ) -> dict:
        """处理用户输入并返回最终回复。"""
        messages = list(history or [])
        messages.append({"role": "user", "content": user_input})

        tool_calls_log = []
        round_count = 0
        system_prompt = self._build_system_prompt(user_input)

        while round_count < max_tool_rounds:
            round_count += 1

            response = await self.llm.chat(
                messages=[{"role": "system", "content": system_prompt}, *messages],
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

            tool_calls = LLMClient.parse_tool_calls(response)

            if not tool_calls:
                return {
                    "reply": content or "好的，已处理完成。",
                    "tool_calls": tool_calls_log,
                    "error": False,
                }

            for tc in tool_calls:
                result = self.execute_tool(tc["name"], tc["arguments"])
                tool_calls_log.append({
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                    "output": result.output[:200],
                    "success": result.success,
                })
                messages.append(result.to_message())

        final = await self.llm.chat(
            messages=[{"role": "system", "content": system_prompt}, *messages],
            temperature=0.5,
        )
        reply = LLMClient.get_reply(final) or "已完成所有操作。"
        return {"reply": reply, "tool_calls": tool_calls_log, "error": False}

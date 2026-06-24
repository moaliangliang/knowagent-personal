"""Agent core - LLM tool-calling loop for local execution."""

import json
import time
import uuid
from typing import Any

from knowagent_personal.agent.tools import COMMANDS, get_tool_definitions

SYSTEM_PROMPT = """你是 Mac Agent Personal，一个本地运行的 Mac 桌面 AI 助手。
你有 70 多个本地命令可以控制 Mac 系统，包括：

- 系统状态查询（CPU/内存/磁盘/网络/电池/WiFi）
- 系统控制（屏幕亮度、音量、睡眠、关机、重启、屏保、专注模式）
- 音乐控制（Apple Music 搜索、播放、音量、下一首）
- 邮件读取和发送（Mail.app + 邮箱大师）
- 截图和 OCR 文字识别（截屏分析 + 文件 OCR）
- 剪贴板读写及历史记录
- 日历事件查询
- UI 自动化（查看界面树、查找元素、点击按钮）
- 键盘模拟（输入文字、按键）
- 文件浏览、文件搜索（Spotlight）、文件内容搜索（grep）
- 文件压缩/解压、图片格式转换、重复文件检测
- 联系人搜索
- 提醒事项添加
- 备忘录查看
- 语音朗读
- 语音输入（听用户说话）
- 屏幕锁定
- 多步工作流执行
- 个人知识库搜索（查询索引过的本地文档/笔记）
- VPN 管理（深信服 aTrust / FortiGate 连接检测、代理管理）
- 网络工具（公网 IP、网速测试、HTTP 请求、文件下载、Whois、Ping、端口检查）
- 开发工具（Homebrew 管理、进程管理、Docker）
- 媒体处理（录屏、录音、视频信息提取）
- 效率工具（倒计时/番茄钟、文本翻译、快捷指令调用）
- AI 对话、文本摘要、代码审查、图片生成
- 系统监控（磁盘空间预警、电池健康度、CPU 温度）

规则：
1. 在需要执行操作时，请使用提供的工具。
2. 如果用户询问关于他们自己的文档、笔记、知识库的问题，优先使用 knowledge_retrieve 工具。
3. 如果用户只是问候或提问，直接友好回复。
4. 回复要简洁，用中文。
5. 如果某工具执行失败，告知用户并提供替代方案。"""


class Agent:
    """Local AI Agent with tool-calling loop, memory persistence, and RAG."""

    def __init__(self, llm_client, config):
        self.llm = llm_client
        self.config = config
        self.tools = COMMANDS
        self.tool_definitions = get_tool_definitions()
        self.conversation_history: list[dict[str, Any]] = []
        self.max_tool_turns = 5
        self.conversation_id = str(uuid.uuid4())[:8]
        self.rag = None

        # 注意: RAG 改为懒加载，启动时不初始化（避免 ChromaDB 加载过慢）
        # 首次需要时通过 _ensure_rag() 自动初始化

        # Load conversation history from SQLite
        self._load_history()

    def _ensure_rag(self):
        """懒加载 RAG（需要时才初始化）"""
        if self.rag is not None:
            return True
        try:
            from knowagent_personal.memory.rag import PersonalRAG
            self.rag = PersonalRAG(self.config)
            if self.rag.init():
                from knowagent_personal.agent.tools import set_rag
                set_rag(self.rag)
                return True
        except Exception:
            self.rag = None
        return False

    def _load_history(self):
        """Load recent conversation history from SQLite."""
        try:
            from knowagent_personal.memory.db import init_db, get_recent_messages

            init_db()
            for msg in get_recent_messages(limit=20):
                role = msg["role"]
                content = msg.get("content", "")
                if content:
                    self.conversation_history.append(
                        {"role": role, "content": content}
                    )
        except Exception:
            pass

    def _save_message(self, role: str, content: str | None = None):
        """Save a message to SQLite."""
        try:
            from knowagent_personal.memory.db import save_message

            save_message(role, content)
        except Exception:
            pass

    def process(self, user_input: str) -> str:
        """Process user input through the LLM tool-calling loop."""
        start_time = time.time()

        # Save user message to SQLite
        self._save_message("user", user_input)

        self.conversation_history.append({
            "role": "user",
            "content": user_input,
        })

        messages = self._build_messages()

        for turn in range(self.max_tool_turns):
            try:
                response = self.llm.chat(messages, tools=self.tool_definitions)
            except (ConnectionError, TimeoutError, ValueError) as e:
                error_msg = f"❌ {e}"
                self.conversation_history.pop()
                return error_msg
            except Exception as e:
                self.conversation_history.pop()
                return f"❌ LLM 调用失败: {e}"

            message = response["choices"][0]["message"]

            if "tool_calls" in message and message["tool_calls"]:
                for tc in message["tool_calls"]:
                    func_name = tc["function"]["name"]
                    try:
                        func_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        func_args = {}

                    # Execute tool
                    result = self._execute_tool(func_name, func_args)

                    # Add assistant message with tool call
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tc],
                    })
                    # Add tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": str(result),
                    })
            else:
                # Final text response
                reply = message.get("content", "") or ""
                self.conversation_history.append({
                    "role": "assistant",
                    "content": reply,
                })
                # Save assistant response to SQLite
                self._save_message("assistant", reply)
                elapsed = time.time() - start_time
                if elapsed > 1:
                    return f"{reply}\n\n⏱ {elapsed:.1f}s"
                return reply

        # Max turns reached - clean up
        self.conversation_history.pop()
        return "❌ 处理次数过多（超过5轮工具调用），请简化需求或重试。"

    def _execute_tool(self, name: str, params: dict) -> str:
        """Execute a tool by name with params dict."""
        handler = self.tools.get(name)
        if not handler:
            return f"❌ 未知命令: {name}"

        try:
            result = handler(params)
            return str(result)
        except Exception as e:
            return f"❌ 执行 {name} 失败: {e}"

    def _build_messages(self) -> list[dict]:
        """Build message array with system prompt + conversation history."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        # Include last 20 turns for context (~40 messages)
        messages.extend(self.conversation_history[-40:])
        return messages

    def local_chat(self, text: str) -> str:
        """Fallback when no LLM available."""
        t = text.lower()
        if any(k in t for k in ["你是谁", "你叫什么", "what are you"]):
            return (
                "🤖 Mac Agent Personal — 你的本地 Mac 桌面 AI 助手\n"
                "可以控制音乐、截图、OCR识别、UI自动化、查看系统状态等"
            )
        if any(k in t for k in ["能力", "能做什么", "功能", "capabilities"]):
            cmds = ", ".join(sorted(self.tools.keys()))
            return f"📋 我具备 {len(self.tools)} 个命令:\n  {cmds}"
        if any(k in t for k in ["大模型", "模型", "ai", "llm"]):
            return (
                "🧠 AI 引擎:\n"
                "  对话: Ollama (本地运行)\n"
                "  命令执行: 本地离线 (30+ 内置命令)\n"
                "  OCR: macOS 原生 Vision 框架\n"
                "  UI 自动化: Swift AX API"
            )
        return (
            "🤔 没理解你的意思\n"
            "试试直接说命令：播放周杰伦的歌 / 系统状态 / 截图 / 帮助\n"
            "或者确保 Ollama 正在运行以获得 AI 对话能力"
        )

"""知行 LLM 客户端 — 统一 DeepSeek / OpenAI / Ollama API 调用。

支持两种模式：
  - 用户自备 Key：用户在设置页输入 API Key
  - 知行托管：默认内置，送 50 次/月免费额度

使用示例：
    client = LLMClient(api_key="sk-...", provider="deepseek")
    response = await client.chat(
        messages=[{"role": "user", "content": "你好"}],
        tools=tool_definitions,
    )
"""

import json
import os
import time
from typing import Any

import httpx

# ── 默认配置 ──────────────────────────────────────

DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "ollama": "qwen3:8b",
}

# 知行托管 API（轻量代理，仅转发 + 用量统计）
ZHIXING_API_BASE = os.environ.get(
    "ZHIXING_API_BASE", "https://api.zhixing.ai/v1"
)


class LLMClient:
    """LLM API 客户端，支持流式和非流式调用。"""

    def __init__(
        self,
        api_key: str = "",
        provider: str = "deepseek",
        api_base: str = "",
        model: str = "",
        timeout: int = 30,
    ):
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base or self._default_base(provider)
        self.model = model or DEFAULT_MODELS.get(provider, "deepseek-chat")
        self.timeout = timeout

    @staticmethod
    def _default_base(provider: str) -> str:
        bases = {
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
            "ollama": "http://localhost:11434/v1",
        }
        return bases.get(provider, bases["deepseek"])

    def _build_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key.startswith("sk-"):
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> dict:
        """调用 LLM 并返回响应。

        Args:
            messages: OpenAI 格式消息列表
            tools: OpenAI 工具定义列表（复用 tools.py 的 get_tool_definitions()）
            temperature: 温度参数，工具调用场景建议 0.3
            max_tokens: 最大输出 token
            stream: 是否流式输出

        Returns:
            OpenAI 格式响应 dict，或流式模式下逐块返回
        """
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        headers = self._build_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                return {
                    "error": True,
                    "message": "⏱ AI 响应超时，请稍后重试",
                }
            except httpx.HTTPStatusError as e:
                return {
                    "error": True,
                    "message": f"❌ API 请求失败 (HTTP {e.response.status_code})",
                }
            except Exception as e:
                return {
                    "error": True,
                    "message": f"❌ 网络错误: {str(e)}",
                }

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ):
        """流式调用 LLM，适用于打字机效果。"""
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        headers = self._build_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=body,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data.strip() == "[DONE]":
                                break
                            yield json.loads(data)
            except Exception:
                yield {"error": True, "message": "❌ 流式响应中断"}

    @staticmethod
    def parse_tool_calls(response: dict) -> list[dict]:
        """从 LLM 响应中提取工具调用。

        Returns:
            [{"name": "cmd_name", "arguments": {"key": "val"}}, ...]
        """
        choices = response.get("choices", [])
        if not choices:
            return []

        message = choices[0].get("message", {})
        tool_calls = message.get("tool_calls", [])

        parsed = []
        for tc in tool_calls:
            func = tc.get("function", {})
            try:
                args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            parsed.append({
                "id": tc.get("id", ""),
                "name": func.get("name", ""),
                "arguments": args,
            })
        return parsed

    @staticmethod
    def get_reply(response: dict) -> str:
        """从 LLM 响应中提取文字回复。"""
        choices = response.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

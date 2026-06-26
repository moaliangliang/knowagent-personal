"""LLM Client - Ollama and OpenAI-compatible API with tool calling support."""

import json
import os
import time
from typing import Any

import requests


class LLMClient:
    """Unified client for local Ollama or OpenAI-compatible API."""

    def __init__(self, config):
        self.provider = config.get("llm.provider", "ollama")
        self.ollama_url = config.get("llm.ollama_url", "http://localhost:11434")
        self.model = config.get("llm.model", "qwen2.5:7b")
        self.api_key = config.get("llm.api_key", "")
        self.base_url = config.get("llm.base_url", "")
        # Proxy settings
        self._proxies = config.get_proxies()
        self._apply_proxy_env()

    def _apply_proxy_env(self):
        """Set HTTP_PROXY/HTTPS_PROXY env vars so requests & openai lib both pick them up."""
        if not self._proxies:
            # Clear if proxy was previously set but now disabled
            for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy"):
                os.environ.pop(var, None)
            return
        if "http" in self._proxies:
            os.environ["HTTP_PROXY"] = self._proxies["http"]
            os.environ["http_proxy"] = self._proxies["http"]
        if "https" in self._proxies:
            os.environ["HTTPS_PROXY"] = self._proxies["https"]
            os.environ["https_proxy"] = self._proxies["https"]
        if self._proxies.get("no_proxy"):
            os.environ["NO_PROXY"] = self._proxies["no_proxy"]
            os.environ["no_proxy"] = self._proxies["no_proxy"]

    def check_available(self) -> tuple[bool, str]:
        """Check if LLM is reachable. Returns (ok, message)."""
        if self.provider == "ollama":
            return self._check_ollama()
        else:
            return self._check_openai()

    def _check_ollama(self) -> tuple[bool, str]:
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=3, proxies=self._proxies)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                if self.model in models:
                    return True, f"Ollama 已连接 (模型 {self.model} 已就绪)"
                else:
                    return (
                        False,
                        f"Ollama 已连接但模型 '{self.model}' 未找到。"
                        f"可用模型: {', '.join(models[:5])}"
                        f"\n  请运行: ollama pull {self.model}",
                    )
            return False, f"Ollama 返回状态码 {r.status_code}"
        except requests.ConnectionError:
            return False, (
                f"无法连接 Ollama ({self.ollama_url})。\n"
                f"  安装: brew install ollama\n"
                f"  启动: ollama serve\n"
                f"  拉取模型: ollama pull {self.model}"
            )
        except Exception as e:
            return False, f"检查 Ollama 失败: {e}"

    def _check_openai(self) -> tuple[bool, str]:
        try:
            import openai
        except ImportError:
            return False, "需要安装 openai 库: pip install openai"
        try:
            client = openai.OpenAI(
                api_key=self.api_key or "sk-dummy",
                base_url=self.base_url or None,
            )
            client.models.list()
            return True, f"API 已连接 (模型: {self.model})"
        except Exception as e:
            return False, f"API 连接失败: {e}"

    def chat(self, messages: list, tools: list[dict] | None = None) -> dict[str, Any]:
        """Send chat request with optional tool definitions.
        Returns normalized OpenAI-format response dict."""
        if self.provider == "ollama":
            return self._chat_ollama(messages, tools)
        else:
            return self._chat_openai(messages, tools)

    def _chat_ollama(
        self, messages: list, tools: list[dict] | None
    ) -> dict[str, Any]:
        url = f"{self.ollama_url}/v1/chat/completions"
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(url, json=payload, timeout=120, proxies=self._proxies)
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError:
            raise ConnectionError(
                f"无法连接到 Ollama ({self.ollama_url})。\n"
                f"  确保 Ollama 已启动: ollama serve"
            )
        except requests.Timeout:
            raise TimeoutError(
                "Ollama 响应超时（2分钟），模型可能仍在加载或推理中。"
            )
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise ValueError(
                    f"模型 '{self.model}' 未找到。请运行: ollama pull {self.model}"
                )
            raise

    def _chat_openai(
        self, messages: list, tools: list[dict] | None
    ) -> dict[str, Any]:
        try:
            import openai
        except ImportError:
            raise ImportError("需要 openai 库: pip install 'zhixing[openai]'")

        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url or None,
        )
        kwargs: dict = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools

        completion = client.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        message = choice.message

        # Normalize to plain dict
        result: dict[str, Any] = {
            "choices": [
                {
                    "message": {
                        "role": message.role,
                        "content": message.content or "",
                    }
                }
            ]
        }
        if message.tool_calls:
            result["choices"][0]["message"]["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        return result

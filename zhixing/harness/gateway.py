"""Gateway — 平台无关的消息网关。

参考 Hermes `gateway/platforms/` 设计：
- 抽象 `PlatformAdapter` 基类
- 每个平台一个适配器实现
- Gateway 管理所有适配器的生命周期

用法:
    from zhixing.harness.gateway import Gateway, WebSocketAdapter
    from zhixing.agent.core import Agent

    agent = Agent(llm, config)
    gateway = Gateway(agent)

    # 注册多个平台适配器
    gateway.register(WebSocketAdapter(host="0.0.0.0", port=8000))
    # gateway.register(TelegramAdapter(token="..."))  # 未来扩展

    gateway.run()  # 阻塞运行所有适配器
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ── 消息协议 ─────────────────────────────────────────────


@dataclass
class AgentMessage:
    """Agent 消息统一格式。"""
    type: str                    # "command" | "chat" | "system"
    content: str = ""
    params: dict = field(default_factory=dict)
    message_id: str = ""
    source: str = ""             # 来源平台标识

    @classmethod
    def from_dict(cls, data: dict) -> AgentMessage:
        return cls(
            type=data.get("type", "chat"),
            content=data.get("content", ""),
            params=data.get("params", {}),
            message_id=data.get("id", ""),
            source=data.get("source", "unknown"),
        )

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "content": self.content,
            "params": self.params,
            "id": self.message_id,
            "source": self.source,
        }


@dataclass
class AgentResponse:
    """Agent 响应统一格式。"""
    success: bool
    output: str = ""
    error: str = ""
    message_id: str = ""
    duration: float = 0.0

    def to_dict(self) -> dict:
        return {
            "type": "result" if self.success else "error",
            "data": self.output if self.success else "",
            "error": self.error if not self.success else "",
            "id": self.message_id,
        }


# ── 平台适配器基类 ───────────────────────────────────────


class PlatformAdapter(ABC):
    """平台适配器抽象基类。

    每个平台（WebSocket、CLI、Telegram、Webhook 等）实现此接口。
    """

    def __init__(self, name: str):
        self.name = name
        self.gateway: Gateway | None = None
        self._running = False

    @abstractmethod
    async def start(self):
        """启动适配器（进入消息循环）。"""
        ...

    @abstractmethod
    async def stop(self):
        """停止适配器。"""
        ...

    @abstractmethod
    async def send(self, response: AgentResponse):
        """发送响应到平台。"""
        ...

    def process_message(self, msg: AgentMessage) -> AgentResponse:
        """处理消息（由 Gateway 调用）。"""
        if self.gateway is None:
            return AgentResponse(success=False, error="Gateway 未连接")
        return self.gateway.route(msg)

    @property
    def is_running(self) -> bool:
        return self._running


# ── WebSocket 适配器 ──────────────────────────────────────


class WebSocketAdapter(PlatformAdapter):
    """WebSocket 平台适配器。

    替换原有的 agent.py WebSocket 客户端。
    支持 JSON 消息协议和心跳检测。
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000,
                 path: str = "/ws/agent"):
        super().__init__(name="websocket")
        self.host = host
        self.port = port
        self.path = path
        self._server = None
        self._connections: set = set()

    async def start(self):
        """启动 WebSocket 服务器。"""
        import websockets
        self._running = True
        async def handler(websocket):
            self._connections.add(websocket)
            try:
                async for raw in websocket:
                    try:
                        data = json.loads(raw)
                        msg = AgentMessage.from_dict(data)
                        msg.source = "websocket"
                        response = self.process_message(msg)
                        await websocket.send(
                            json.dumps(response.to_dict(), ensure_ascii=False)
                        )
                    except json.JSONDecodeError:
                        await websocket.send(
                            json.dumps({"type": "error", "data": "无效的 JSON 格式"})
                        )
            finally:
                self._connections.discard(websocket)

        self._server = await websockets.serve(
            handler, self.host, self.port,
            ping_interval=30, ping_timeout=10,
        )
        logger.info(f"WebSocket 服务器已启动: ws://{self.host}:{self.port}{self.path}")

    async def stop(self):
        """停止 WebSocket 服务器。"""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for ws in set(self._connections):
            await ws.close()
        self._connections.clear()

    async def send(self, response: AgentResponse):
        """广播响应到所有 WebSocket 连接。"""
        if not self._connections:
            return
        payload = json.dumps(response.to_dict(), ensure_ascii=False)
        for ws in set(self._connections):
            try:
                await ws.send(payload)
            except Exception:
                self._connections.discard(ws)


class WebSocketClientAdapter(PlatformAdapter):
    """WebSocket 客户端适配器（连接远程服务器）。

    替代原 mac_agent/agent.py 中的 WebSocket 客户端。
    """

    def __init__(self, server_url: str = "http://localhost:8000",
                 user_id: str = "", reconnect_delay: int = 10):
        super().__init__(name="ws_client")
        self.server_url = server_url
        self.user_id = user_id or os.environ.get("USER", "agent")
        self.reconnect_delay = reconnect_delay
        self._ws = None

    async def start(self):
        """启动客户端，连接到远程服务器。"""
        import websockets
        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws/agent"

        while not self._running:
            self._running = True
            try:
                async with websockets.connect(ws_url) as ws:
                    self._ws = ws
                    await ws.send(json.dumps({
                        "type": "register",
                        "info": {
                            "system": os.uname().sysname or "macOS",
                            "hostname": os.uname().nodename,
                            "user": self.user_id,
                            "version": "2.0.0",
                        },
                    }))
                    reg = json.loads(await ws.recv())
                    agent_id = reg.get("agent_id", "?")
                    logger.info(f"已连接至服务器, Agent ID: {agent_id}")

                    async for raw in ws:
                        data = json.loads(raw)
                        if data.get("type") == "ping":
                            continue
                        msg = AgentMessage.from_dict(data)
                        msg.source = "remote"
                        response = self.process_message(msg)
                        await ws.send(
                            json.dumps(response.to_dict(), ensure_ascii=False)
                        )
            except (ConnectionRefusedError, OSError):
                logger.warning(f"服务器未就绪，{self.reconnect_delay}秒后重连...")
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"连接异常: {e}")
                await asyncio.sleep(self.reconnect_delay)

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()

    async def send(self, response: AgentResponse):
        if self._ws:
            try:
                await self._ws.send(
                    json.dumps(response.to_dict(), ensure_ascii=False)
                )
            except Exception:
                pass


# ── CLI 适配器 ──────────────────────────────────────────


class CLIAdapter(PlatformAdapter):
    """命令行适配器（替代原有的 repl.py）。

    支持交互式 REPL 模式和单命令模式。
    """

    def __init__(self, prompt: str = "› "):
        super().__init__(name="cli")
        self.prompt = prompt
        self._loop = asyncio.new_event_loop()

    async def start(self):
        """启动 CLI 循环。"""
        self._running = True
        print(f"🤖 Agent CLI ({self.gateway.agent.harness_status()['tools']['total']} tools)")
        print("输入 help 查看帮助, exit 退出\n")
        while self._running:
            try:
                line = await self._async_input()
                if not line or not line.strip():
                    continue
                if line.strip().lower() in ("exit", "quit"):
                    break
                msg = AgentMessage(
                    type="chat" if " " not in line.strip() else "command",
                    content=line.strip(),
                    source="cli",
                )
                response = self.process_message(msg)
                if response.output:
                    print(response.output)
                if response.error:
                    print(f"❌ {response.error}")
            except (EOFError, KeyboardInterrupt):
                break
        self._running = False

    async def stop(self):
        self._running = False

    async def send(self, response: AgentResponse):
        if response.output:
            print(response.output)
        if response.error:
            print(f"❌ {response.error}")

    async def _async_input(self) -> str:
        """异步读入一行。"""
        import sys
        return await self._loop.run_in_executor(None, sys.stdin.readline)


# ── Gateway 管理器 ─────────────────────────────────────────


class Gateway:
    """消息网关 — 管理多个平台适配器的生命周期。

    将 Agent 连接到任意数量的平台（WebSocket + CLI + …）。
    """

    def __init__(self, agent):
        self.agent = agent
        self._adapters: dict[str, PlatformAdapter] = {}
        self._events = agent._harness.events if hasattr(agent, '_harness') else None

    def register(self, adapter: PlatformAdapter) -> None:
        """注册一个平台适配器。"""
        adapter.gateway = self
        self._adapters[adapter.name] = adapter
        logger.info(f"平台适配器已注册: {adapter.name}")

    def unregister(self, name: str) -> None:
        """卸载一个平台适配器。"""
        adapter = self._adapters.pop(name, None)
        if adapter:
            adapter.gateway = None

    def get(self, name: str) -> PlatformAdapter | None:
        """获取已注册的适配器。"""
        return self._adapters.get(name)

    def route(self, msg: AgentMessage) -> AgentResponse:
        """路由消息到 Agent 进行处理。"""
        import time as _time
        start = _time.time()

        try:
            if msg.type == "command":
                output = self.agent._execute_tool(msg.content, msg.params)
            else:
                output = self.agent.process(msg.content)

            return AgentResponse(
                success=True,
                output=str(output) if output else "✅ 完成",
                message_id=msg.message_id,
                duration=_time.time() - start,
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                error=str(e),
                message_id=msg.message_id,
            )

    def run(self):
        """启动所有适配器（阻塞）。"""
        import asyncio

        async def _run_all():
            tasks = []
            for adapter in self._adapters.values():
                tasks.append(asyncio.create_task(adapter.start()))
            if tasks:
                await asyncio.gather(*tasks)

        try:
            asyncio.run(_run_all())
        except KeyboardInterrupt:
            logger.info("正在关闭网关...")
        finally:
            self.stop()

    def stop(self):
        """停止所有适配器。"""
        for adapter in self._adapters.values():
            try:
                asyncio.run(adapter.stop())
            except Exception:
                pass
        logger.info("网关已关闭")

    @property
    def status(self) -> dict:
        """网关状态。"""
        return {
            "adapters": {
                name: {
                    "type": type(ad).__name__,
                    "running": adapter.is_running,
                }
                for name, adapter in self._adapters.items()
            }
        }

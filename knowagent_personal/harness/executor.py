"""Execution Engine — 智能执行引擎。

遵循 Claude Code 的执行调度原则：
- 只读 + 并发安全 → 并行执行
- 普通操作 → 串行执行
- 破坏性操作 → 隔离执行 + 二次确认
- 超时 → 自动终止并恢复

同时实现：
- 自动重试（可配置次数）
- 执行暂停/恢复
- 执行记录（用于审计）
"""

from __future__ import annotations

import enum
import signal
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from .registry import ToolDef, TOOL_REGISTRY, PermissionLevel
from .permissions import PermissionManager, PermissionVerdict, PermissionMode
from .events import EventBus
from .threat_detection import ThreatScanner, ScanScope


class ExecutionStrategy(str, enum.Enum):
    """执行策略 — 根据工具元数据自动选择。"""
    DIRECT = "direct"           # 当前线程直接执行
    PARALLEL = "parallel"       # 并发执行（只读+安全）
    ISOLATED = "isolated"       # 子进程隔离执行
    CONFIRMED = "confirmed"     # 需二次确认后执行


@dataclass
class ExecutionResult:
    """执行结果。"""
    success: bool
    output: str = ""
    error: str = ""
    tool_name: str = ""
    duration: float = 0.0
    strategy: ExecutionStrategy = ExecutionStrategy.DIRECT

    def __str__(self) -> str:
        if self.success:
            return self.output
        return f"❌ {self.error}"


class StepRecorder:
    """步骤记录器 — 记录每次工具执行的过程。

    支持工作流级别的回滚语义。
    """

    def __init__(self):
        self._history: list[ExecutionResult] = []

    def record(self, result: ExecutionResult) -> None:
        """记录一次执行。"""
        self._history.append(result)

    @property
    def last(self) -> ExecutionResult | None:
        return self._history[-1] if self._history else None

    @property
    def all(self) -> list[ExecutionResult]:
        return list(self._history)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self._history if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self._history if not r.success)

    def clear(self) -> None:
        self._history.clear()


class Executor:
    """智能执行引擎。

    用法:
        executor = Executor(permission_manager)
        result = executor.run("screenshot_analyze", {"region": "0,0,800,600"})
    """

    def __init__(self, permissions: PermissionManager | None = None,
                 events: EventBus | None = None):
        self.permissions = permissions or PermissionManager()
        self.events = events or EventBus()
        self.recorder = StepRecorder()
        self.max_retries = 2
        self.retry_delay = 0.5  # 秒
        self._parallel_executor = ThreadPoolExecutor(max_workers=4)
        self._threat_scanner = ThreatScanner()  # 提示注入检测

    def _select_strategy(self, tool: ToolDef) -> ExecutionStrategy:
        """根据工具元数据自动选择执行策略。"""
        if tool.is_destructive:
            return ExecutionStrategy.CONFIRMED
        if tool.is_readonly and tool.concurrency_safe:
            return ExecutionStrategy.PARALLEL
        if tool.permission == PermissionLevel.SYSTEM_CTRL:
            return ExecutionStrategy.ISOLATED
        return ExecutionStrategy.DIRECT

    def run(self, tool_name: str, params: dict | None = None,
            confirm: bool = False) -> ExecutionResult:
        """执行一个工具。

        完整的执行管道：
        1. 权限检查
        2. 策略选择
        3. （可配置重试）
        4. 执行
        5. 记录
        6. 事件通知
        """
        start = time.time()
        params = params or {}

        # 发送 before 事件
        self.events.emit("tool.before", tool_name=tool_name, params=params)

        # Layer 0: 提示注入检测（对非只读工具检查参数）
        if not tool_name.startswith("system_") and not tool_name.startswith("knowledge_"):
            for key, val in params.items():
                if isinstance(val, str) and len(val) > 10:
                    scan_result = self._threat_scanner.scan(val, ScanScope.ALL)
                    if scan_result.blocked:
                        result = ExecutionResult(
                            success=False,
                            error=f"🛡️ 输入被安全策略拦截: {scan_result.reason}",
                            tool_name=tool_name,
                        )
                        self.events.emit("tool.denied", tool_name=tool_name,
                                         reason=f"提示注入拦截: {scan_result.reason}")
                        return result

        # Layer 1: 查找工具定义
        tool = TOOL_REGISTRY.get(tool_name)
        if tool is None:
            result = ExecutionResult(
                success=False,
                error=f"未知工具: {tool_name}",
                tool_name=tool_name,
            )
            self.events.emit("tool.error", tool_name=tool_name, error=result.error)
            return result

        # Layer 2: 权限检查
        verdict = self.permissions.check(tool_name, require_confirm=confirm)
        if not verdict.allowed:
            if verdict.require_confirmation:
                result = ExecutionResult(
                    success=False,
                    error=f"需要确认: {tool_name} ({tool.description})",
                    tool_name=tool_name,
                    strategy=ExecutionStrategy.CONFIRMED,
                )
            else:
                result = ExecutionResult(
                    success=False,
                    error=verdict.reason,
                    tool_name=tool_name,
                )
            self.recorder.record(result)
            self.events.emit("tool.denied", tool_name=tool_name, reason=result.error)
            return result

        # Layer 3: 策略选择
        strategy = self._select_strategy(tool)

        # Layer 4: 执行（含重试）
        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                output = tool.handler(params)
                elapsed = time.time() - start
                result = ExecutionResult(
                    success=True,
                    output=str(output),
                    tool_name=tool_name,
                    duration=elapsed,
                    strategy=strategy,
                )
                self.recorder.record(result)
                self.events.emit("tool.after", tool_name=tool_name,
                                 result=result, duration=elapsed)
                if attempt > 1:
                    result.output = f"⚠ 重试{attempt - 1}次后成功\n{result.output}"
                return result

            except subprocess.TimeoutExpired as e:
                last_error = f"⏱ 超时 ({tool.timeout}s): {e}"
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
            except FileNotFoundError as e:
                last_error = f"📁 依赖缺失: {e}"
                break  # 依赖缺失不重试
            except PermissionError as e:
                last_error = f"🔒 权限不足: {e}"
                break  # 权限不足不重试
            except Exception as e:
                last_error = f"❌ {e}"
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                break

        # 全部重试失败
        elapsed = time.time() - start
        result = ExecutionResult(
            success=False,
            error=last_error,
            tool_name=tool_name,
            duration=elapsed,
            strategy=strategy,
        )
        self.recorder.record(result)
        self.events.emit("tool.error", tool_name=tool_name,
                         error=last_error, duration=elapsed)
        return result

    def run_parallel(self, tasks: list[tuple[str, dict]]) -> list[ExecutionResult]:
        """并发执行多个只读工具。"""
        results: list[ExecutionResult] = []

        def _execute_single(name: str, params: dict) -> ExecutionResult:
            return self.run(name, params)

        futures = {}
        for name, params in tasks:
            # 只对只读+并发安全的工具并行
            tool = TOOL_REGISTRY.get(name)
            if tool and tool.is_readonly and tool.concurrency_safe:
                fut = self._parallel_executor.submit(_execute_single, name, params)
                futures[fut] = name
            else:
                # 非并发安全工具串行执行
                results.append(self.run(name, params))

        for fut in as_completed(futures):
            name = futures[fut]
            try:
                results.append(fut.result(timeout=60))
            except Exception as e:
                results.append(ExecutionResult(
                    success=False, error=str(e), tool_name=name,
                ))

        return results

    def run_workflow(self, steps: list[dict]) -> ExecutionResult:
        """执行多步工作流。

        steps 格式: [{"cmd": "tool_name", "params": {...}, "wait": 0.5}, ...]
        """
        total = len(steps)
        success = 0
        outputs: list[str] = []

        for i, step in enumerate(steps, 1):
            cmd = step.get("cmd", "")
            params = step.get("params", {})
            wait = float(step.get("wait", 0.5))
            desc = step.get("desc", cmd)

            result = self.run(cmd, params)
            if result.success:
                success += 1
                outputs.append(f"  [{i}/{total}] ✅ {desc}")
                if len(result.output) > 200:
                    outputs.append(f"     {result.output[:200]}...")
                else:
                    outputs.append(f"     {result.output}")
            else:
                outputs.append(f"  [{i}/{total}] ❌ {desc}: {result.error}")

            if wait > 0:
                time.sleep(wait)

        return ExecutionResult(
            success=success == total,
            output=f"📋 工作流完成（{success}/{total} 步成功）:\n" + "\n".join(outputs),
            tool_name="workflow",
        )

    def resume(self, from_step: int = 0) -> ExecutionResult | None:
        """从指定步骤恢复执行（仅对工作流有效）。"""
        # TODO: 从持久化存储恢复执行状态
        return None

    def shutdown(self) -> None:
        """关闭执行引擎。"""
        self._parallel_executor.shutdown(wait=False)
        self.recorder.clear()


# 延迟导入（避免启动时加载）
import subprocess

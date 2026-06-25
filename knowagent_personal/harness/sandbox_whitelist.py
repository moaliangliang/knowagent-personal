"""Code Sandbox — 白名单隔离的代码执行沙箱。

参考 Hermes `code_execution_tool.py` 的 7-tool 白名单沙箱设计：
- 沙箱内只能调用白名单允许的工具
- 通过 UDS/文件 RPC 与父进程通信
- 环境变量清洗（移除密钥/令牌）
- 资源限制（超时、调用次数、输出大小）

用法:
    from knowagent_personal.harness.sandbox_whitelist import CodeSandbox
    sandbox = CodeSandbox()
    result = sandbox.execute("print('hello')")
    # 或在沙箱内执行 AI 生成的脚本
    result = sandbox.execute_script('''
        result = read_file(path="/etc/hostname")
        print(result)
    ''')
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .registry import TOOL_REGISTRY, ToolDef


# ── 白名单配置 ───────────────────────────────────────────

# 沙箱内允许的工具白名单（参考 Hermes 的 7-tool 设计）
SANDBOX_ALLOWED_TOOLS = frozenset({
    "read_file",
    "file_search",
    "file_grep",
    "http_request",
    "my_ip",
    "ping",
    "whois",
})

# 环境变量清洗规则
_SECRET_SUBSTRINGS = ("KEY", "TOKEN", "SECRET", "PASSWORD",
                      "CREDENTIAL", "PASSWD", "AUTH", "DSN", "WEBHOOK")

_SAFE_ENV_PREFIXES = ("PATH", "HOME", "USER", "LANG", "LC_",
                      "TMPDIR", "TMP", "TEMP", "SHELL", "LOGNAME")

# 沙箱资源限制（参考 Hermes 的默认值）
DEFAULT_TIMEOUT = 60          # 60 秒
DEFAULT_MAX_CALLS = 20        # 最多 20 次工具调用
MAX_STDOUT_BYTES = 50_000     # 50 KB
MAX_STDERR_BYTES = 10_000     # 10 KB


@dataclass
class SandboxResult:
    """沙箱执行结果。"""
    success: bool
    output: str = ""
    error: str = ""
    tool_calls: int = 0
    duration: float = 0.0


# ── 环境变量清洗 ─────────────────────────────────────────


def _scrub_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """清洗环境变量，移除敏感信息。"""
    clean = {}
    source = env or os.environ.copy()
    for key, val in source.items():
        # 密钥子串匹配 → 跳过
        if any(sub in key.upper() for sub in _SECRET_SUBSTRINGS):
            continue
        # 安全前缀匹配 → 保留
        if any(key.startswith(prefix) for prefix in _SAFE_ENV_PREFIXES):
            clean[key] = val
            continue
        # HERMES_ 相关的只保留非密钥的运行时变量
        if key.startswith("HOME") or key == "TZ":
            clean[key] = val
    return clean


# ── Stub 生成 ────────────────────────────────────────────


def _generate_stub(allowed_tools: frozenset[str]) -> str:
    """生成沙箱内的工具 stub 模块。

    沙箱内的脚本只能通过 stub 调用白名单中的工具。
    stub 通过 stdin/stdout JSON-RPC 与父进程通信。
    """
    tool_defs = []
    for name in sorted(allowed_tools):
        tool = TOOL_REGISTRY.get(name)
        if tool:
            tool_defs.append((name, tool.description))

    # 生成 stub 函数
    stub_funcs = []
    for name, desc in tool_defs:
        safe_name = name.replace("-", "_").replace(" ", "_")
        stub_funcs.append(f'''
def {safe_name}(params: dict | None = None) -> str:
    """{desc}"""
    _request = json.dumps({{"tool": "{name}", "params": params or {{}}}})
    _write_request(_request)
    _response = _read_response()
    return _response
''')

    stub_code = textwrap.dedent(f'''
import json
import os
import sys

# ── RPC 通信 ─────────────────────────────────────────────
_RPC_FILE = os.environ.get("HERMES_RPC_FILE", "")
_REQUEST_FILE = _RPC_FILE + ".request"
_RESPONSE_FILE = _RPC_FILE + ".response"

def _write_request(data: str):
    with open(_REQUEST_FILE, "w") as f:
        f.write(data)

def _read_response() -> str:
    import time
    timeout = 30
    start = time.time()
    while True:
        if os.path.exists(_RESPONSE_FILE):
            try:
                with open(_RESPONSE_FILE) as f:
                    data = f.read()
                os.remove(_RESPONSE_FILE)
                return data
            except (OSError, IOError):
                time.sleep(0.05)
                continue
        if time.time() - start > timeout:
            return json.dumps({{"error": "RPC 超时"}})
        time.sleep(0.05)

# ── 白名单工具 ────────────────────────────────────────────
''')

    for func in stub_funcs:
        stub_code += func

    stub_code += f'''
# ── 允许的工具列表 ──────────────────────────────────────
ALLOWED_TOOLS = {json.dumps(sorted(allowed_tools))}

if __name__ == "__main__":
    # 当直接运行时，读取脚本并执行
    script = sys.stdin.read()
    try:
        exec(script, {{"__name__": "__sandbox__"}})
    except Exception as e:
        print(f"❌ 沙箱执行错误: {{e}}", file=sys.stderr)
'''

    return stub_code


# ── 代码沙箱 ─────────────────────────────────────────────


class CodeSandbox:
    """白名单隔离的代码执行沙箱。

    LLM 生成的 Python 脚本在子进程中运行，
    只能通过白名单中的工具与外部交互。

    架构:
        父进程 ←─[file-based RPC]── 子进程 (沙箱)
                     read_file()
                     file_search()   → 仅允许这 7 个工具
                     http_request()  → ...
    """

    def __init__(self, allowed_tools: frozenset[str] | None = None):
        self.allowed_tools = allowed_tools or SANDBOX_ALLOWED_TOOLS
        self.timeout = DEFAULT_TIMEOUT
        self.max_calls = DEFAULT_MAX_CALLS

    def execute_script(self, script: str, params: dict | None = None) -> SandboxResult:
        """在沙箱中执行 Python 脚本。

        Args:
            script: 要执行的 Python 代码
            params: 传入脚本的参数（可选）

        Returns:
            SandboxResult: 执行结果
        """
        start = time.time()
        params = params or {}

        # 安全检查：禁止脚本直接导入可能危险的模块
        if self._has_dangerous_imports(script):
            return SandboxResult(
                success=False,
                error="脚本包含不安全的导入（os.system/subprocess/socket 等）",
            )

        # 生成 stub 代码
        stub = _generate_stub(self.allowed_tools)

        # 创建临时 RPC 文件
        rpc_file = os.path.join(tempfile.mkdtemp(), "sandbox_rpc")

        # 构建完整的沙箱脚本
        full_script = textwrap.dedent(f'''
import json, os, sys
os.environ["HERMES_RPC_FILE"] = {json.dumps(rpc_file)}

# 传入参数
_params = {json.dumps(params)}

# Stub 代码
''') + stub + "\n\n# ── 用户脚本 ──\n" + script

        # 构建清洗后的环境变量
        clean_env = _scrub_env()
        clean_env["HERMES_RPC_FILE"] = rpc_file
        clean_env["PYTHONPATH"] = os.environ.get("PYTHONPATH", "")
        clean_env.pop("HERMES_API_KEY", None)

        # 启动 RPC 监听线程
        import threading
        call_count = 0
        results: list[str] = []
        stop_rpc = threading.Event()

        def rpc_handler():
            nonlocal call_count
            while not stop_rpc.is_set():
                req_file = rpc_file + ".request"
                resp_file = rpc_file + ".response"
                try:
                    if os.path.exists(req_file):
                        with open(req_file) as f:
                            request = json.loads(f.read())
                        os.remove(req_file)
                        call_count += 1
                        if call_count > self.max_calls:
                            response = json.dumps(
                                {"error": f"超过最大工具调用次数 ({self.max_calls})"}
                            )
                        else:
                            tool_name = request.get("tool", "")
                            tool_params = request.get("params", {})
                            response = self._dispatch_tool(tool_name, tool_params)
                        with open(resp_file, "w") as f:
                            f.write(response)
                except (OSError, json.JSONDecodeError):
                    pass
                stop_rpc.wait(0.05)

        rpc_thread = threading.Thread(target=rpc_handler, daemon=True)
        rpc_thread.start()

        try:
            proc = subprocess.run(
                [sys.executable, "-c", full_script],
                capture_output=True, text=True, timeout=self.timeout,
                env=clean_env,
            )
            elapsed = time.time() - start
            stdout = proc.stdout.strip()[:MAX_STDOUT_BYTES]
            stderr = proc.stderr.strip()[:MAX_STDERR_BYTES]

            if proc.returncode != 0:
                error_msg = stderr or f"进程退出码: {proc.returncode}"
                return SandboxResult(
                    success=False, error=error_msg,
                    tool_calls=call_count, duration=elapsed,
                )
            return SandboxResult(
                success=True, output=stdout,
                tool_calls=call_count, duration=elapsed,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                error=f"⏱ 沙箱执行超时 ({self.timeout}秒)",
                tool_calls=call_count,
            )
        finally:
            stop_rpc.set()
            # 清理临时文件
            try:
                for f in [rpc_file + ".request", rpc_file + ".response", rpc_file]:
                    if os.path.exists(f):
                        os.remove(f)
                os.rmdir(os.path.dirname(rpc_file))
            except Exception:
                pass

    def _dispatch_tool(self, tool_name: str, params: dict) -> str:
        """在沙箱上下文中调度工具调用。"""
        if tool_name not in self.allowed_tools:
            return json.dumps({"error": f"沙箱不允许使用工具: {tool_name}"})

        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            return json.dumps({"error": f"未知工具: {tool_name}"})

        try:
            result = tool.handler(params)
            # 限制返回大小
            result_str = str(result)
            if len(result_str) > 10_000:
                result_str = result_str[:10_000] + "\n... (结果被截断)"
            return json.dumps({"result": result_str})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def execute(self, code: str) -> SandboxResult:
        """快捷方式: 执行一段代码。"""
        return self.execute_script(code)

    @staticmethod
    def _has_dangerous_imports(script: str) -> bool:
        """检查脚本中是否包含危险导入。"""
        dangerous = [
            r'import\s+os\s',
            r'import\s+subprocess',
            r'import\s+socket',
            r'import\s+ctypes',
            r'import\s+sys\s',
            r'from\s+os\s+import',
            r'from\s+subprocess\s+import',
            r'from\s+socket\s+import',
            r'from\s+ctypes\s+import',
            r'\bsys\.(?:stdin|stdout)\b',
            r'\bos\.(?:system|popen|fork|exec)',
            r'\bexec\(|\beval\(|\bcompile\(',
            r'__import__\s*\(',
            r'open\(\s*["\']/etc/',
            r'open\(\s*["\']/dev/',
        ]
        for pattern in dangerous:
            if re.search(pattern, script):
                return True
        return False

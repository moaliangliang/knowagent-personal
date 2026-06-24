"""开发者工具命令模块

Homebrew、进程管理、Docker 管理。
所有 cmd_* 函数统一返回 str（纯文本），格式：
  ✅ 成功信息
  ❌ 错误信息
  📋 数据/列表信息
"""

import subprocess
import json
import os
import signal as _signal


# ── 工具函数 ─────────────────────────────────────────────

def _run_cmd(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """执行外部命令并返回 CompletedProcess。"""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _format_table(rows: list[list[str]], headers: list[str]) -> str:
    """将行数据格式化为对齐的表格字符串。"""
    if not rows:
        return "(空)"

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    lines: list[str] = []
    # 表头
    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("  ".join("-" * col_widths[i] for i in range(len(headers))))

    for row in rows:
        cells = [cell.ljust(col_widths[i]) if i < len(col_widths) else cell for i, cell in enumerate(row)]
        lines.append("  ".join(cells))

    return "\n".join(lines)


# ── Homebrew ─────────────────────────────────────────────

def cmd_brew(params: dict) -> str:
    """Homebrew 包管理。action=list/install/search/update/upgrade/cleanup，name?=包名"""
    action = params.get("action", "").strip().lower()
    name = params.get("name", "").strip()

    if not action:
        return "❌ 需要 action 参数，支持: list, install, search, update, upgrade, cleanup"

    try:
        if action == "list":
            r = _run_cmd(["brew", "list"], timeout=30)
            if r.returncode != 0:
                return f"❌ brew list 失败: {r.stderr.strip()}"
            packages = [line for line in r.stdout.split("\n") if line.strip()]
            if not packages:
                return "📋 Homebrew 已安装包: (空)"
            formatted = "\n".join(f"  - {pkg}" for pkg in packages)
            return f"📋 Homebrew 已安装包（共 {len(packages)} 个）:\n{formatted}"

        elif action == "install":
            if not name:
                return "❌ install 操作需要 name 参数（包名）"
            r = _run_cmd(["brew", "install", name], timeout=300)
            if r.returncode != 0:
                stderr = r.stderr.strip()
                if "already installed" in stderr.lower():
                    return f"✅ 已安装: {name}"
                return f"❌ brew install {name} 失败: {stderr}"
            return f"✅ 安装成功: {name}"

        elif action == "search":
            if not name:
                return "❌ search 操作需要 name 参数（关键词）"
            r = _run_cmd(["brew", "search", name], timeout=60)
            if r.returncode != 0:
                return f"❌ brew search 失败: {r.stderr.strip()}"
            output = r.stdout.strip()
            # 解析搜索结果的格式: 分 Formula 和 Casks 两部分
            lines = output.split("\n")
            formulas: list[str] = []
            casks: list[str] = []
            section = None
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("==> Formulae"):
                    section = "formula"
                    continue
                elif stripped.startswith("==> Casks"):
                    section = "cask"
                    continue
                elif stripped.startswith("==") or not stripped:
                    continue
                if section == "formula":
                    formulas.extend(stripped.split())
                elif section == "cask":
                    casks.extend(stripped.split())
            result_lines = [f"📋 brew search '{name}' 结果:"]
            if formulas:
                result_lines.append(f"\n   Formula ({len(formulas)}):")
                for f in formulas[:20]:
                    result_lines.append(f"     - {f}")
                if len(formulas) > 20:
                    result_lines.append(f"     ... 还有 {len(formulas) - 20} 个")
            if casks:
                result_lines.append(f"\n   Cask ({len(casks)}):")
                for c in casks[:20]:
                    result_lines.append(f"     - {c}")
                if len(casks) > 20:
                    result_lines.append(f"     ... 还有 {len(casks) - 20} 个")
            if not formulas and not casks:
                result_lines.append(f"   未找到匹配的包")
            return "\n".join(result_lines)

        elif action == "update":
            r = _run_cmd(["brew", "update"], timeout=300)
            if r.returncode != 0:
                return f"❌ brew update 失败: {r.stderr.strip()}"
            output = r.stdout.strip()
            # brew update 输出可能为空（已经是最新）
            if output:
                return f"✅ brew update 完成:\n{output[:1000]}"
            return "✅ Homebrew 已是最新"

        elif action == "upgrade":
            if name:
                r = _run_cmd(["brew", "upgrade", name], timeout=600)
                if r.returncode != 0:
                    return f"❌ brew upgrade {name} 失败: {r.stderr.strip()}"
                return f"✅ 升级完成: {name}"
            r = _run_cmd(["brew", "upgrade"], timeout=600)
            if r.returncode != 0:
                return f"❌ brew upgrade 失败: {r.stderr.strip()}"
            output = r.stdout.strip()
            if "already installed" in output.lower() or not output:
                return "✅ 所有包已是最新版本"
            return f"✅ brew upgrade 完成:\n{output[:1000]}"

        elif action == "cleanup":
            r = _run_cmd(["brew", "cleanup", "--prune=all"], timeout=300)
            if r.returncode != 0:
                return f"❌ brew cleanup 失败: {r.stderr.strip()}"
            output = r.stdout.strip()
            if not output:
                return "✅ 无需清理"
            # 提取清理摘要
            summary_lines = [line for line in output.split("\n") if line.strip()]
            summary = "\n".join(summary_lines)
            return f"✅ brew cleanup 完成:\n{summary}"

        else:
            return f"❌ 不支持的 action: {action}，支持: list, install, search, update, upgrade, cleanup"

    except subprocess.TimeoutExpired:
        return f"❌ brew {action} 超时"
    except FileNotFoundError:
        return "❌ 未找到 brew 命令，请先安装 Homebrew"
    except Exception as e:
        return f"❌ brew {action} 执行异常: {e}"


# ── 进程管理 ─────────────────────────────────────────────

def cmd_process(params: dict) -> str:
    """进程管理。action=list/kill，name?=进程名（list用），signal?=信号值（默认15）"""
    action = params.get("action", "").strip().lower()
    name = params.get("name", "").strip()
    signal_val = int(params.get("signal", 15))

    if not action:
        return "❌ 需要 action 参数，支持: list, kill"

    try:
        if action == "list":
            if name:
                r = _run_cmd(["ps", "aux"], timeout=10)
                if r.returncode != 0:
                    return f"❌ ps aux 失败: {r.stderr.strip()}"
                lines = r.stdout.split("\n")
                # 过滤匹配进程名（grep 模拟）
                filtered = [lines[0]] if lines else []  # 保留表头
                for line in lines[1:]:
                    if name.lower() in line.lower():
                        filtered.append(line)

                if len(filtered) <= 1:
                    return f"📋 未找到包含 '{name}' 的进程"

                rows: list[list[str]] = []
                for line in filtered[1:]:
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        rows.append([
                            parts[0],          # USER
                            parts[1],          # PID
                            parts[2],          # %CPU
                            parts[3],          # %MEM
                            parts[10][:60],    # COMMAND
                        ])

                table = _format_table(rows, ["USER", "PID", "%CPU", "%MEM", "COMMAND"])
                return f"📋 进程列表（匹配 '{name}'，共 {len(rows)} 个）:\n{table}"

            # 列出所有进程（摘要形式）
            r = _run_cmd(["ps", "aux"], timeout=10)
            if r.returncode != 0:
                return f"❌ ps aux 失败: {r.stderr.strip()}"
            lines = r.stdout.strip().split("\n")
            count = len(lines) - 1  # 减去表头
            # 计算总 CPU 和内存
            total_cpu = 0.0
            total_mem = 0.0
            for line in lines[1:]:
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    try:
                        total_cpu += float(parts[2])
                        total_mem += float(parts[3])
                    except ValueError:
                        pass
            return (
                f"📋 进程总览:\n"
                f"   总进程数: {count}\n"
                f"   总 CPU 使用: {total_cpu:.1f}%\n"
                f"   总内存使用: {total_mem:.1f}%\n"
                f"   使用 'action=list&name=xxx' 搜索特定进程"
            )

        elif action == "kill":
            if not name:
                return "❌ kill 操作需要 name 参数（进程名关键词）"

            r = _run_cmd(["ps", "aux"], timeout=10)
            if r.returncode != 0:
                return f"❌ ps aux 失败: {r.stderr.strip()}"

            # 查找匹配进程（排除 grep、ps 自身）
            matching_pids: list[tuple[str, str]] = []
            for line in r.stdout.split("\n")[1:]:
                if not line.strip():
                    continue
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    cmd = parts[10]
                    pid_str = parts[1]
                    if name.lower() in cmd.lower():
                        # 跳过自身
                        if cmd.strip() in ("ps", "grep", "kill"):
                            continue
                        matching_pids.append((pid_str, cmd[:60]))

            if not matching_pids:
                return f"📋 未找到匹配 '{name}' 的进程"

            if signal_val not in (_signal.Signals.__members__.values() if hasattr(_signal, "Signals") else range(1, 32)):
                return f"❌ 无效的信号值: {signal_val}，常用: 15 (SIGTERM), 9 (SIGKILL), 2 (SIGINT)"

            killed = []
            failed = []
            for pid, cmd in matching_pids:
                try:
                    os.kill(int(pid), signal_val)
                    killed.append(f"  ✓ PID {pid} ({cmd})")
                except ProcessLookupError:
                    failed.append(f"  ✗ PID {pid} 已不存在")
                except PermissionError:
                    failed.append(f"  ✗ PID {pid} 权限不足")
                except Exception as e:
                    failed.append(f"  ✗ PID {pid}: {e}")

            lines: list[str] = []
            if killed:
                sig_name = signal_val
                try:
                    sig_name = _signal.Signals(signal_val).name
                except (ValueError, AttributeError):
                    pass
                lines.append(f"✅ 已发送 {sig_name}({signal_val}) 给 {len(killed)} 个进程:")
                lines.extend(killed)
            if failed:
                lines.extend(failed)

            return "\n".join(lines) if lines else f"❌ 未能终止任何匹配 '{name}' 的进程"

        else:
            return f"❌ 不支持的 action: {action}，支持: list, kill"

    except subprocess.TimeoutExpired:
        return f"❌ 进程 {action} 超时"
    except FileNotFoundError:
        return "❌ 未找到 ps/kill 命令"
    except Exception as e:
        return f"❌ 进程 {action} 异常: {e}"


# ── Docker ────────────────────────────────────────────────

def cmd_docker(params: dict) -> str:
    """Docker 容器管理。action=ps/images/pull/start/stop/logs，name?=容器名/镜像名，lines?=日志行数（默认50）"""
    action = params.get("action", "").strip().lower()
    name = params.get("name", "").strip()
    lines = int(params.get("lines", 50))

    if not action:
        return "❌ 需要 action 参数，支持: ps, images, pull, start, stop, logs"

    try:
        if action == "ps":
            # 检查 docker 是否运行
            info_r = _run_cmd(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=10)
            if info_r.returncode != 0:
                return "❌ Docker 未运行或未安装（请确认 Docker Desktop 已启动）"

            r = _run_cmd(["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}"], timeout=10)
            if r.returncode != 0:
                return f"❌ docker ps 失败: {r.stderr.strip()}"

            running = []
            stopped = []
            for line in r.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 4:
                    cid, image, status, cname = parts[0], parts[1], parts[2], parts[3]
                    if name and name.lower() not in cname.lower() and name.lower() not in image.lower():
                        continue
                    if "Up" in status:
                        running.append([cname, image, status, cid[:12]])
                    else:
                        stopped.append([cname, image, status, cid[:12]])

            result_lines = [f"📋 Docker 容器（Docker Server v{info_r.stdout.strip()}）:"]
            if running:
                result_lines.append(f"\n  🟢 运行中 ({len(running)}):")
                result_lines.append("    " + _format_table(running, ["NAME", "IMAGE", "STATUS", "ID"]).replace("\n", "\n    "))
            if stopped:
                result_lines.append(f"\n  ⏹ 已停止 ({len(stopped)}):")
                result_lines.append("    " + _format_table(stopped, ["NAME", "IMAGE", "STATUS", "ID"]).replace("\n", "\n    "))
            if not running and not stopped:
                result_lines.append("    (无容器)")

            return "\n".join(result_lines)

        elif action == "images":
            r = _run_cmd(["docker", "images", "--format", "{{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.ID}}"], timeout=10)
            if r.returncode != 0:
                return f"❌ docker images 失败: {r.stderr.strip()}"

            rows: list[list[str]] = []
            for line in r.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 4:
                    repo, tag, size, iid = parts[0], parts[1], parts[2], parts[3][:12]
                    if name and name.lower() not in repo.lower():
                        continue
                    rows.append([repo, tag, iid, size])

            if not rows:
                return f"📋 Docker 镜像列表: (无)"
            table = _format_table(rows, ["REPOSITORY", "TAG", "IMAGE ID", "SIZE"])
            return f"📋 Docker 镜像列表（共 {len(rows)} 个）:\n{table}"

        elif action == "pull":
            if not name:
                return "❌ pull 操作需要 name 参数（镜像名，如 nginx:latest）"
            r = _run_cmd(["docker", "pull", name], timeout=600)
            if r.returncode != 0:
                return f"❌ docker pull {name} 失败: {r.stderr.strip()}"
            output = r.stdout.strip()
            # 提取状态行（通常是最后一行）
            status_lines = [l for l in output.split("\n") if "Status" in l]
            status = status_lines[0] if status_lines else "已拉取"
            return f"✅ docker pull {name} 完成\n   {status}"

        elif action == "start":
            if not name:
                return "❌ start 操作需要 name 参数（容器名或 ID）"
            r = _run_cmd(["docker", "start", name], timeout=30)
            if r.returncode != 0:
                return f"❌ docker start {name} 失败: {r.stderr.strip()}"
            return f"✅ 已启动容器: {name}"

        elif action == "stop":
            if not name:
                return "❌ stop 操作需要 name 参数（容器名或 ID）"
            r = _run_cmd(["docker", "stop", name], timeout=30)
            if r.returncode != 0:
                return f"❌ docker stop {name} 失败: {r.stderr.strip()}"
            return f"✅ 已停止容器: {name}"

        elif action == "logs":
            if not name:
                return "❌ logs 操作需要 name 参数（容器名或 ID）"
            lines = max(1, min(lines, 1000))
            r = _run_cmd(["docker", "logs", "--tail", str(lines), name], timeout=10)
            if r.returncode != 0:
                return f"❌ docker logs {name} 失败: {r.stderr.strip()}"
            output = r.stdout.strip()
            if not output:
                return f"📋 容器 {name} 日志: (无输出)"
            if len(output) > 3000:
                output = output[:3000] + f"\n...（截断，共 {len(output)} 字符，使用 tail -n 查看完整日志）"
            return f"📋 容器 {name} 日志（最近 {lines} 行）:\n{output}"

        else:
            return f"❌ 不支持的 action: {action}，支持: ps, images, pull, start, stop, logs"

    except subprocess.TimeoutExpired:
        return f"❌ docker {action} 超时"
    except FileNotFoundError:
        return "❌ 未找到 docker 命令，请先安装 Docker"
    except Exception as e:
        return f"❌ docker {action} 异常: {e}"


# ── 命令注册 ─────────────────────────────────────────────

COMMANDS: dict = {
    "brew": cmd_brew,
    "process": cmd_process,
    "docker": cmd_docker,
}

TOOL_SCHEMAS: dict = {
    "brew": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["list", "install", "search", "update", "upgrade", "cleanup"],
            },
            "name": {
                "type": "string",
                "description": "包名（install/search/upgrade 时需要）",
            },
        },
        "required": ["action"],
    },
    "process": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["list", "kill"],
            },
            "name": {
                "type": "string",
                "description": "进程名关键词（list 时用于过滤，kill 时必填）",
            },
            "signal": {
                "type": "integer",
                "description": "信号值，默认 15 (SIGTERM)，9 为 SIGKILL，2 为 SIGINT",
            },
        },
        "required": ["action"],
    },
    "docker": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["ps", "images", "pull", "start", "stop", "logs"],
            },
            "name": {
                "type": "string",
                "description": "容器名/镜像名（pull/start/stop/logs 时需要）",
            },
            "lines": {
                "type": "integer",
                "description": "日志显示行数，默认 50，最大 1000（仅 logs 操作）",
            },
        },
        "required": ["action"],
    },
}

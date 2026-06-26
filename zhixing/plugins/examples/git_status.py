"""插件示例: Git 状态 — 快速查看当前目录 Git 状态。"""

import subprocess

from zhixing.plugins import Plugin


class GitStatusPlugin(Plugin):
    name = "Git 状态"
    description = "快速查看当前目录的 Git 状态"
    version = "0.1.0"
    author = "Mac Agent"

    def get_commands(self) -> dict:
        return {"git_status": self.cmd_git_status}

    def get_nl_rules(self) -> list:
        return [
            (["git", "git状态", "仓库状态"], lambda kw: ("git_status", {})),
        ]

    def cmd_git_status(self, params: dict) -> str:
        try:
            r = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode != 0:
                return "❌ 当前目录不是 Git 仓库"
            output = r.stdout.strip()
            if not output:
                return "✅ 工作区干净，没有未提交的更改"
            lines = output.split("\n")
            return (
                f"📋 Git 状态（共 {len(lines)} 个变更）:\n"
                f"```\n{output}\n```"
            )
        except FileNotFoundError:
            return "❌ 未找到 git 命令"
        except subprocess.TimeoutExpired:
            return "❌ Git 命令超时"
        except Exception as e:
            return f"❌ Git 状态查询失败: {e}"

"""CLI entry point for `ka` command."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="ka",
        description="Mac Agent Personal - 本地 Mac 桌面 AI 助手",
    )
    parser.add_argument(
        "--model", default=None, help="Ollama 模型名 (覆盖配置)"
    )
    parser.add_argument(
        "--ollama-url", default=None, help="Ollama 服务器地址 (覆盖配置)"
    )
    parser.add_argument(
        "--provider", default=None, choices=["ollama", "openai"],
        help="LLM 提供商 (覆盖配置)"
    )
    parser.add_argument(
        "command", nargs="*", help="单命令模式，如: ka 系统状态"
    )

    args = parser.parse_args()
    cli_overrides = {k: v for k, v in vars(args).items() if v is not None and k != "command"}

    if args.command:
        from knowagent_personal.ui.cli import single_command
        single_command(" ".join(args.command), cli_overrides)
    else:
        from knowagent_personal.ui.cli import run_repl
        run_repl(cli_overrides)


if __name__ == "__main__":
    main()

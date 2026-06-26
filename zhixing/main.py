"""CLI entry point for `zhi` / `flow` / `ka` commands."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="zhi",
        description="知行 (ZhiXing) - 自然语言驱动的 Mac 桌面 AI 自动化助手",
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
        "command", nargs="*", help="单命令模式，如: zhi 系统状态"
    )

    args = parser.parse_args()
    cli_overrides = {k: v for k, v in vars(args).items() if v is not None and k != "command"}

    if args.command:
        from zhixing.ui.cli import single_command
        single_command(" ".join(args.command), cli_overrides)
    else:
        from zhixing.ui.cli import run_repl
        run_repl(cli_overrides)


if __name__ == "__main__":
    main()

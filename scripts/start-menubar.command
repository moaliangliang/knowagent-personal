#!/bin/bash
# Mac Agent Personal - 菜单栏启动器
# 双击此文件启动，或从 Terminal 运行

cd "$(dirname "$0")/.."
echo "🧠 启动 Mac Agent Personal 菜单栏..."
echo "   菜单栏顶部应出现 KA 字样"
echo "   按 Ctrl+C 退出"
echo ""

python3 -m knowagent_personal.app menubar

#!/bin/bash
# 知行 (ZhiXing) - 菜单栏启动器
# 双击此文件启动，或从 Terminal 运行

cd "$(dirname "$0")/.."
echo "🧠 启动 知行 菜单栏..."
echo "   按 Ctrl+C 退出"
echo ""

python3 -m zhixing.app menubar

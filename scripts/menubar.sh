#!/bin/bash
# 知行 (ZhiXing) - 菜单栏应用管理
# 用法: bash scripts/menubar.sh {start|stop|status|restart}

APP_PATH="$HOME/.zhixing/ZhiXing.app"
PID_FILE="/tmp/zhixing-menubar.pid"
LOG_FILE="/tmp/zhixing-menubar.log"

ensure_app() {
    if [ ! -d "$APP_PATH" ]; then
        echo "📦 创建 ZhiXing.app..."
        osacompile -o "$APP_PATH" \
            -e "do shell script \"cd $(pwd) && python3 -m zhixing.app menubar > $LOG_FILE 2>&1 &\"" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "❌ 创建失败"
            return 1
        fi
        echo "✅ .app 已创建"
    fi
    return 0
}

case "${1:-start}" in
    start)
        ensure_app || exit 1
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "⚠️  菜单栏已在运行 (PID $(cat "$PID_FILE"))"
            echo "   重新启动: $0 restart"
            exit 0
        fi
        open "$APP_PATH"
        PID=$(ps aux | grep "zhixing.*menubar" | grep -v grep | awk '{print $2}')
        if [ -n "$PID" ]; then
            echo "$PID" > "$PID_FILE"
        fi
        echo "✅ 菜单栏已启动"
        echo "   点击菜单栏图标使用"
        echo "   关闭: $0 stop"
        ;;
    stop)
        if [ -f "$PID_FILE" ]; then
            kill $(cat "$PID_FILE") 2>/dev/null
            rm -f "$PID_FILE"
            echo "⏹  菜单栏已关闭"
        else
            PID=$(ps aux | grep "zhixing.*menubar" | grep -v grep | awk '{print $2}')
            if [ -n "$PID" ]; then
                kill "$PID" 2>/dev/null
                echo "⏹  菜单栏已关闭 (PID $PID)"
            else
                echo "⚠️  菜单栏未在运行"
            fi
        fi
        ;;
    status)
        PID=$(ps aux | grep "zhixing.*menubar" | grep -v grep | awk '{print $2}')
        if [ -n "$PID" ]; then
            echo "✅ 菜单栏运行中 (PID $PID)"
        else
            echo "⏹  菜单栏未运行"
        fi
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    *)
        echo "用法: bash scripts/menubar.sh {start|stop|status|restart}"
        ;;
esac

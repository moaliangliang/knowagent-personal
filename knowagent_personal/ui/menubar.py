"""macOS Menu Bar application using rumps."""

import os
import subprocess

from knowagent_personal.config import CONFIG_DIR


def run_menubar():
    """Launch the menu bar app (blocking - must run on main thread)."""
    try:
        import rumps
    except ImportError:
        print("❌ 需要安装 rumps: pip install rumps")
        return

    class AgentMenuBar(rumps.App):
        def __init__(self):
            super().__init__("KA", title="KA")
            self.menu = [
                rumps.MenuItem("打开 Agent 终端", callback=self.open_repl),
                rumps.MenuItem("知识库索引", callback=self.index_docs),
                None,
                rumps.MenuItem("打开配置", callback=self.open_settings),
                None,
                rumps.MenuItem("退出", callback=self.quit_app),
            ]

        def open_repl(self, _):
            script = '''
            tell application "Terminal"
                activate
                do script "ka"
            end tell'''
            subprocess.run(["osascript", "-e", script], timeout=5)

        def index_docs(self, _):
            script = '''
            tell application "Terminal"
                activate
                do script "ka rag index ~/Documents"
            end tell'''
            subprocess.run(["osascript", "-e", script], timeout=5)

        def open_settings(self, _):
            config_file = os.path.join(CONFIG_DIR, "config.yaml")
            if os.path.exists(config_file):
                subprocess.run(["open", config_file], timeout=5)

        def quit_app(self, _):
            rumps.quit_application()

    agent_app = AgentMenuBar()
    print("✅ Mac Agent 菜单栏已启动")
    print("   菜单栏顶部应出现 KA 字样")
    print("   按 Ctrl+C 退出")
    agent_app.run()

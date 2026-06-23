import Cocoa
import Foundation

/// 查找 ka 命令路径
func findKa() -> String {
    let candidates = [
        "/usr/local/bin/ka",
        "/opt/homebrew/bin/ka",
        "\(NSHomeDirectory())/Library/Python/3.13/bin/ka",
        "\(NSHomeDirectory())/.local/bin/ka",
        "/Users/maoliangliang/Library/Python/3.13/bin/ka",
    ]
    for path in candidates {
        if FileManager.default.isExecutableFile(atPath: path) {
            return path
        }
    }
    return "ka"
}

let KA = findKa()

/// 运行 shell 命令（不阻塞 UI）
func shell(_ cmd: String) {
    DispatchQueue.global().async {
        let task = Process()
        task.launchPath = "/bin/bash"
        task.arguments = ["-c", cmd]
        task.launch()
    }
}

/// 在 Terminal 中执行命令
func terminal(_ command: String) {
    // 写临时 AppleScript 文件避免引号转义问题
    let script = """
    tell application "Terminal"
        activate
        if (count of windows) = 0 then
            do script "\(command)"
        else
            tell application "System Events" to keystroke "t" using command down
            delay 0.3
            do script "\(command)" in front window
        end if
    end tell
    """
    let tmp = "/tmp/ka_menubar.scpt"
    try? script.write(toFile: tmp, atomically: true, encoding: String.Encoding.utf8)
    shell("osascript '\(tmp)' 2>/dev/null; rm -f '\(tmp)'")
}


// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)  // 仅菜单栏，无 Dock

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            button.title = "🧠"
            button.font = NSFont.systemFont(ofSize: 13)
        }

        let menu = NSMenu()

        menu.addItem(mkItem("打开 Agent 终端", action: #selector(openAgent), key: "k",
                            mods: [.command, .shift]))
        menu.addItem(mkItem("知识库索引", action: #selector(indexDocs)))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(mkItem("打开配置", action: #selector(openConfig), key: ","))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(mkItem("关于 Mac Agent", action: #selector(showAbout)))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(mkItem("退出", action: #selector(quitApp), key: "q"))

        statusItem.menu = menu
        print("🧠 Mac Agent Personal 菜单栏已启动")
    }

    func mkItem(_ title: String, action: Selector, key: String = "",
                mods: NSEvent.ModifierFlags = []) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
        item.target = self
        if !mods.isEmpty {
            item.keyEquivalentModifierMask = mods
        }
        return item
    }

    // MARK: Actions

    @objc func openAgent(_ sender: Any?) {
        terminal(KA)
    }

    @objc func indexDocs(_ sender: Any?) {
        terminal("\(KA) rag index ~/Documents")
    }

    @objc func openConfig(_ sender: Any?) {
        let path = "\(NSHomeDirectory())/.knowagent/config.yaml"
        shell("open '\(path)'")
    }

    @objc func showAbout(_ sender: Any?) {
        let alert = NSAlert()
        alert.messageText = "Mac Agent Personal"
        alert.informativeText = "v0.1.0\n本地 Mac 桌面 AI 助手\n30+ 命令 · 本地 LLM · 离线运行\n\n命令路径: \(KA)"
        alert.alertStyle = .informational
        alert.addButton(withTitle: "好的")
        alert.runModal()
    }

    @objc func quitApp(_ sender: Any?) {
        NSApplication.shared.terminate(nil)
    }
}

// MARK: - Entry Point

let delegate = AppDelegate()
NSApp.delegate = delegate
NSApp.run()

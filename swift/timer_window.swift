import Cocoa

// ═══════════════════════════════════════════════════════════
// 番茄钟原生窗口 — macOS Native
// 编译: swiftc -O -o timer_window timer_window.swift
// ═══════════════════════════════════════════════════════════

let minutes: Int = Int(CommandLine.arguments.dropFirst().first ?? "25") ?? 25
let titleArg: String = CommandLine.arguments.dropFirst().dropFirst().first ?? "番茄钟"

// ── 窗口（CGShieldingWindowLevel 确保在所有窗口最前方）──
let window = NSWindow(
    contentRect: NSRect(x: 0, y: 0, width: 320, height: 220),
    styleMask: [.titled, .closable, .miniaturizable],
    backing: .buffered, defer: false
)
window.title = "🍅 \(titleArg)"
window.center()
window.level = NSWindow.Level(rawValue: Int(CGShieldingWindowLevel()))
window.makeKeyAndOrderFront(nil)
window.orderFrontRegardless()
NSApp.activate(ignoringOtherApps: true)

// ── 视图 ──
let view = NSView(frame: window.contentView!.bounds)
view.wantsLayer = true
view.layer?.backgroundColor = CGColor(red: 0.173, green: 0.173, blue: 0.173, alpha: 1.0)
window.contentView?.addSubview(view)

// ── 倒计时数字 ──
let timerLabel = NSTextField(labelWithString: "00:00")
timerLabel.font = NSFont.monospacedDigitSystemFont(ofSize: 64, weight: .bold)
timerLabel.alignment = .center
timerLabel.textColor = NSColor(red: 0.902, green: 0.494, blue: 0.133, alpha: 1.0)
timerLabel.frame = CGRect(x: 0, y: 100, width: 320, height: 70)
view.addSubview(timerLabel)

// ── 状态文字 ──
let statusLabel = NSTextField(labelWithString: titleArg)
statusLabel.font = NSFont.systemFont(ofSize: 13)
statusLabel.alignment = .center
statusLabel.textColor = NSColor.gray
statusLabel.frame = CGRect(x: 0, y: 60, width: 320, height: 20)
view.addSubview(statusLabel)

// ── 按钮 ──
let pauseBtn = NSButton(title: "⏸ 暂停", target: nil, action: nil)
pauseBtn.frame = CGRect(x: 30, y: 20, width: 120, height: 28)
pauseBtn.bezelStyle = .rounded
pauseBtn.font = NSFont.systemFont(ofSize: 12)
view.addSubview(pauseBtn)

let cancelBtn = NSButton(title: "✕ 取消", target: nil, action: nil)
cancelBtn.frame = CGRect(x: 170, y: 20, width: 120, height: 28)
cancelBtn.bezelStyle = .rounded
cancelBtn.font = NSFont.systemFont(ofSize: 12)
view.addSubview(cancelBtn)

// ── 辅助函数 ──
func notify(_ text: String) {
    let script = "display notification \"\(text)\" with title \"🍅 番茄钟\" sound name \"default\""
    try? Process.run(URL(fileURLWithPath: "/usr/bin/osascript"), arguments: ["-e", script])
}

func speak(_ text: String) {
    try? Process.run(URL(fileURLWithPath: "/usr/bin/say"), arguments: [text])
}

// ── AppDelegate ──
class AppDelegate: NSObject, NSApplicationDelegate {
    var remaining: Int = minutes * 60
    var paused: Bool = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        Timer.scheduledTimer(timeInterval: 1.0, target: self,
            selector: #selector(tick), userInfo: nil, repeats: true)
    }

    @objc func tick() {
        if paused { return }
        remaining -= 1
        if remaining <= 0 { finish(); return }
        let m = remaining / 60
        let s = remaining % 60
        timerLabel.stringValue = String(format: "%02d:%02d", m, s)
    }

    func finish() {
        timerLabel.stringValue = "✅ 完成！"
        timerLabel.textColor = NSColor.green
        statusLabel.stringValue = "🎉 时间到！"
        statusLabel.textColor = NSColor.green
        pauseBtn.title = "✔ 关闭"
        pauseBtn.action = #selector(NSApplication.terminate(_:))
        notify("🍅 时间到！")
        DispatchQueue.global().async { speak("时间到") }
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
            NSApplication.shared.terminate(nil)
        }
    }

    @objc func togglePause() {
        paused.toggle()
        pauseBtn.title = paused ? "▶ 继续" : "⏸ 暂停"
        statusLabel.stringValue = paused ? "⏸ 已暂停 (\(titleArg))" : titleArg
        statusLabel.textColor = paused ? NSColor.orange : NSColor.gray
        timerLabel.textColor = paused ? NSColor.orange :
            NSColor(red: 0.902, green: 0.494, blue: 0.133, alpha: 1.0)
    }

    @objc func cancel() {
        NSApplication.shared.terminate(nil)
    }
}

// ── 绑定按钮 ──
let delegate = AppDelegate()
pauseBtn.target = delegate
pauseBtn.action = #selector(delegate.togglePause)
cancelBtn.target = delegate
cancelBtn.action = #selector(delegate.cancel)

NSApplication.shared.delegate = delegate
NSApplication.shared.setActivationPolicy(.regular)
NSApplication.shared.run()

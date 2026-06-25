import Cocoa

// ═══════════════════════════════════════════════════════════
// 番茄钟原生窗口 — macOS Native
// 编译: swiftc -O -o timer_window timer_window.swift
// ═══════════════════════════════════════════════════════════

let minutes: Int = Int(CommandLine.arguments.dropFirst().first ?? "25") ?? 25
let titleArg: String = CommandLine.arguments.dropFirst().dropFirst().first ?? "番茄钟"

// ── 窗口（可调小 + CGShieldingWindowLevel 置顶）──
let defaultW: CGFloat = 320
let defaultH: CGFloat = 220
let window = NSWindow(
    contentRect: NSRect(x: 0, y: 0, width: defaultW, height: defaultH),
    styleMask: [.titled, .closable, .miniaturizable, .resizable],
    backing: .buffered, defer: false
)
window.minSize = NSSize(width: 200, height: 150)
window.maxSize = NSSize(width: defaultW, height: defaultH)
window.title = "🍅 \(titleArg)"
// 默认右上角（菜单栏下方 4px）
if let screen = NSScreen.main {
    let vf = screen.visibleFrame
    window.setFrameOrigin(NSPoint(x: vf.maxX - window.frame.width - 4, y: vf.maxY - window.frame.height - 4))
}
window.isMovableByWindowBackground = true
window.level = NSWindow.Level(rawValue: Int(CGShieldingWindowLevel()))
window.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
window.hidesOnDeactivate = false
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
statusLabel.frame = CGRect(x: 0, y: 80, width: 320, height: 20)
view.addSubview(statusLabel)

// ── 透明度滑块 ──
let opacityLabel = NSTextField(labelWithString: "不透明度")
opacityLabel.font = NSFont.systemFont(ofSize: 10)
opacityLabel.textColor = NSColor.gray
opacityLabel.frame = CGRect(x: 20, y: 58, width: 60, height: 16)
opacityLabel.isBezeled = false
opacityLabel.isEditable = false
opacityLabel.backgroundColor = .clear
view.addSubview(opacityLabel)

var currentOpacity: CGFloat = 1.0
let opacitySlider = NSSlider(value: 1.0, minValue: 0.2, maxValue: 1.0, target: nil, action: nil)
opacitySlider.frame = CGRect(x: 80, y: 55, width: 140, height: 20)
opacitySlider.isContinuous = true
opacitySlider.action = nil  // will be set in AppDelegate
view.addSubview(opacitySlider)

let opacityValLabel = NSTextField(labelWithString: "100%")
opacityValLabel.font = NSFont.monospacedDigitSystemFont(ofSize: 10, weight: .regular)
opacityValLabel.textColor = NSColor.gray
opacityValLabel.frame = CGRect(x: 225, y: 58, width: 40, height: 16)
opacityValLabel.isBezeled = false
opacityValLabel.isEditable = false
opacityValLabel.backgroundColor = .clear
view.addSubview(opacityValLabel)

// ── 按钮 ──
let pauseBtn = NSButton(title: "⏸ 暂停", target: nil, action: nil)
pauseBtn.frame = CGRect(x: 30, y: 20, width: 100, height: 28)
pauseBtn.bezelStyle = .rounded
pauseBtn.font = NSFont.systemFont(ofSize: 12)
view.addSubview(pauseBtn)

let cancelBtn = NSButton(title: "✕ 取消", target: nil, action: nil)
cancelBtn.frame = CGRect(x: 150, y: 20, width: 100, height: 28)
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
        opacitySlider.target = self
        opacitySlider.action = #selector(changeOpacity(_:))
        Timer.scheduledTimer(timeInterval: 1.0, target: self,
            selector: #selector(tick), userInfo: nil, repeats: true)
    }

    @objc func changeOpacity(_ sender: NSSlider) {
        let alpha = CGFloat(sender.floatValue)
        currentOpacity = alpha
        view.layer?.backgroundColor = CGColor(red: 0.173, green: 0.173, blue: 0.173, alpha: alpha)
        window.alphaValue = alpha
        opacityValLabel.stringValue = "\(Int(alpha * 100))%"
    }

    @objc func tick() {
        // 每 tick 仅复位 level（无感 — 不闪屏、不抢焦点）
        window.level = NSWindow.Level(rawValue: Int(CGShieldingWindowLevel()))

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

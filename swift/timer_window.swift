import Cocoa

// ═══════════════════════════════════════════════════════════
// 番茄钟原生窗口 — macOS Native（等比例缩放 + 透明度50%默认）
// 编译: swiftc -O -o timer_window timer_window.swift
// ═══════════════════════════════════════════════════════════

let minutes: Int = Int(CommandLine.arguments.dropFirst().first ?? "25") ?? 25
let titleArg: String = CommandLine.arguments.dropFirst().dropFirst().first ?? "番茄钟"

let defaultW: CGFloat = 320
let defaultH: CGFloat = 220

// ── 窗口 ──
let window = NSWindow(
    contentRect: NSRect(x: 0, y: 0, width: defaultW, height: defaultH),
    styleMask: [.titled, .closable, .miniaturizable, .resizable],
    backing: .buffered, defer: false
)
window.minSize = NSSize(width: 200, height: 150)
window.maxSize = NSSize(width: defaultW, height: defaultH)
window.title = "🍅 \(titleArg)"
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

// ── 根视图 ──
let view = NSView(frame: window.contentView!.bounds)
view.wantsLayer = true
view.autoresizingMask = [.width, .height]
view.layer?.backgroundColor = CGColor(red: 0.173, green: 0.173, blue: 0.173, alpha: 1.0)
window.contentView?.addSubview(view)

// ── UI 工厂 ──
func pctX(_ p: CGFloat) -> CGFloat { return view.bounds.width * p / 100 }
func pctY(_ p: CGFloat) -> CGFloat { return view.bounds.height * p / 100 }
func fontSize(_ pts: CGFloat) -> CGFloat { return pts * (view.bounds.height / defaultH) }

// ── 倒计时数字 ──
let timerLabel = NSTextField(labelWithString: "00:00")
timerLabel.font = NSFont.monospacedDigitSystemFont(ofSize: fontSize(64), weight: .bold)
timerLabel.alignment = .center
timerLabel.textColor = NSColor(red: 0.902, green: 0.494, blue: 0.133, alpha: 1.0)
timerLabel.autoresizingMask = [.width, .minYMargin, .maxYMargin]
timerLabel.frame = CGRect(x: 0, y: view.bounds.height * 0.48, width: view.bounds.width, height: view.bounds.height * 0.32)
view.addSubview(timerLabel)

// ── 状态文字 ──
let statusLabel = NSTextField(labelWithString: "保持专注")
statusLabel.font = NSFont.systemFont(ofSize: fontSize(13))
statusLabel.alignment = .center
statusLabel.textColor = NSColor.gray
statusLabel.autoresizingMask = [.width, .minYMargin, .maxYMargin]
statusLabel.frame = CGRect(x: 0, y: view.bounds.height * 0.36, width: view.bounds.width, height: 20)
view.addSubview(statusLabel)

// ── 透明度滑块 ──
let opacityVal: CGFloat = 0.5  // 默认 50%
let opacityLabel = NSTextField(labelWithString: "不透明度")
opacityLabel.font = NSFont.systemFont(ofSize: fontSize(10))
opacityLabel.textColor = NSColor.gray
opacityLabel.isBezeled = false; opacityLabel.isEditable = false; opacityLabel.backgroundColor = .clear
opacityLabel.autoresizingMask = [.maxXMargin, .minYMargin, .maxYMargin]
opacityLabel.frame = CGRect(x: pctX(6), y: pctY(26), width: 55, height: fontSize(14))
view.addSubview(opacityLabel)

let opacitySlider = NSSlider(value: Double(opacityVal), minValue: 0.2, maxValue: 1.0, target: nil, action: nil)
opacitySlider.frame = CGRect(x: pctX(22), y: pctY(25), width: pctX(54), height: 20)
opacitySlider.isContinuous = true
opacitySlider.autoresizingMask = [NSView.AutoresizingMask.width, .minXMargin, .maxXMargin, .minYMargin, .maxYMargin]
view.addSubview(opacitySlider)

let opacityValLabel = NSTextField(labelWithString: "50%")
opacityValLabel.font = NSFont.monospacedDigitSystemFont(ofSize: fontSize(10), weight: .regular)
opacityValLabel.textColor = NSColor.gray
opacityValLabel.isBezeled = false; opacityValLabel.isEditable = false; opacityValLabel.backgroundColor = .clear
opacityValLabel.autoresizingMask = [.minXMargin, .minYMargin, .maxYMargin]
opacityValLabel.frame = CGRect(x: pctX(78), y: pctY(26), width: 36, height: fontSize(14))
view.addSubview(opacityValLabel)

// ── 按钮 ──
let pauseBtn = NSButton(title: "⏸ 暂停", target: nil, action: nil)
pauseBtn.bezelStyle = .rounded
pauseBtn.font = NSFont.systemFont(ofSize: fontSize(12))
pauseBtn.autoresizingMask = [.width, .minXMargin, .maxXMargin, .minYMargin, .maxYMargin]
pauseBtn.frame = CGRect(x: pctX(10), y: pctY(6), width: pctX(37), height: pctY(13))
view.addSubview(pauseBtn)

let cancelBtn = NSButton(title: "✕ 取消", target: nil, action: nil)
cancelBtn.bezelStyle = .rounded
cancelBtn.font = NSFont.systemFont(ofSize: fontSize(12))
cancelBtn.autoresizingMask = [.width, .minXMargin, .maxXMargin, .minYMargin, .maxYMargin]
cancelBtn.frame = CGRect(x: pctX(53), y: pctY(6), width: pctX(37), height: pctY(13))
view.addSubview(cancelBtn)

// 默认透明度
view.layer?.backgroundColor = CGColor(red: 0.173, green: 0.173, blue: 0.173, alpha: opacityVal)
window.alphaValue = opacityVal

// ── 辅助函数 ──
func notify(_ text: String) {
    let script = "display notification \"\(text)\" with title \"🍅 番茄钟\" sound name \"default\""
    try? Process.run(URL(fileURLWithPath: "/usr/bin/osascript"), arguments: ["-e", script])
}
func speak(_ text: String) {
    try? Process.run(URL(fileURLWithPath: "/usr/bin/say"), arguments: [text])
}

// ── 窗口 Delegate（等比例缩放）──
class WindowDelegate: NSObject, NSWindowDelegate {
    func windowDidResize(_ notification: Notification) {
        let h = view.bounds.height
        let scale = h / defaultH
        timerLabel.font = NSFont.monospacedDigitSystemFont(ofSize: 64 * scale, weight: .bold)
        statusLabel.font = NSFont.systemFont(ofSize: 13 * scale)
        pauseBtn.font = NSFont.systemFont(ofSize: 12 * scale)
        cancelBtn.font = NSFont.systemFont(ofSize: 12 * scale)
        opacityLabel.font = NSFont.systemFont(ofSize: 10 * scale)
        opacityValLabel.font = NSFont.monospacedDigitSystemFont(ofSize: 10 * scale, weight: .regular)
    }
}
let winDelegate = WindowDelegate()
window.delegate = winDelegate

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
        view.layer?.backgroundColor = CGColor(red: 0.173, green: 0.173, blue: 0.173, alpha: alpha)
        window.alphaValue = alpha
        opacityValLabel.stringValue = "\(Int(alpha * 100))%"
    }

    @objc func tick() {
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
        statusLabel.stringValue = paused ? "⏸ 已暂停" : "保持专注"
        statusLabel.textColor = paused ? NSColor.orange : NSColor.gray
        timerLabel.textColor = paused ? NSColor.orange :
            NSColor(red: 0.902, green: 0.494, blue: 0.133, alpha: 1.0)
    }

    @objc func cancel() {
        NSApplication.shared.terminate(nil)
    }
}

let delegate = AppDelegate()
pauseBtn.target = delegate
pauseBtn.action = #selector(delegate.togglePause)
cancelBtn.target = delegate
cancelBtn.action = #selector(delegate.cancel)

NSApplication.shared.delegate = delegate
NSApplication.shared.setActivationPolicy(.regular)
NSApplication.shared.run()

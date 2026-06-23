import Cocoa
import Carbon

// Global hotkey: Cmd+Shift+K
// Launches Terminal and opens ka REPL.

let keyCode: UInt32 = 0x28  // 'K' key
// commandKey = cmdKey = 0x0100, shiftKey = 0x0200
let modifiers: UInt32 = UInt32(cmdKey | shiftKey)

var hotKeyRef: EventHotKeyRef?
var hotKeyID = EventHotKeyID(signature: 0x4B414745, id: 1)  // arbitrary

// Register
let status = RegisterEventHotKey(keyCode, modifiers, hotKeyID,
    GetEventDispatcherTarget(), 0, &hotKeyRef)

if status != noErr {
    print("⚠️  HotKey registration failed (error \(status))")
    // Keep running anyway
}

// Event handler callback
let handler: EventHandlerUPP = { _, eventRef, _ in
    // Launch Terminal -> ka
    let task = Process()
    task.launchPath = "/usr/bin/open"
    task.arguments = ["-b", "com.apple.Terminal"]
    task.launch()

    // Use AppleScript to launch ka in the new Terminal window
    Thread.sleep(forTimeInterval: 0.5)
    let script = """
    tell application "Terminal"
        activate
        do script "ka"
    end tell
    """
    if let appleScript = NSAppleScript(source: script) {
        var error: NSDictionary?
        appleScript.executeAndReturnError(&error)
    }
    return noErr
}

// Install handler
var eventSpec = EventTypeSpec(
    eventClass: OSType(kEventClassKeyboard),
    eventKind: UInt32(kEventHotKeyPressed)
)

InstallEventHandler(
    GetEventDispatcherTarget(),
    handler,
    1,
    &eventSpec,
    nil,
    nil
)

// Keep the process alive
RunLoop.main.run()

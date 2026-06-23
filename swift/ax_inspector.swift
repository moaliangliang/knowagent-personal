#!/usr/bin/env swift
/**
 * macOS Accessibility Inspector - Native Swift AX API
 *
 * 用法:
 *   swift ax_inspector.swift --app "Music"              # 查询指定应用的UI树
 *   swift ax_inspector.swift --frontmost                 # 查询前台应用
 *   swift ax_inspector.swift --find "播放" "--app" "Music" # 搜索元素
 *   swift ax_inspector.swift --click "播放" "--app" "Music" # 点击元素
 *
 * 比 AppleScript 的优势:
 *  - 完整递归遍历无障碍树
 *  - 支持 WebKit 内容 (WKView)
 *  - 输出结构化 JSON
 *  - 无 AppleScript 语法限制
 */

import Cocoa
import ApplicationServices

// MARK: - AX 元素模型
struct AXElementInfo: Codable {
    let role: String
    let subrole: String?
    let description: String
    let title: String
    let value: String
    let help: String
    let label: String
    let frame: Frame
    let isEnabled: Bool
    let isFocused: Bool
    let isVisible: Bool
    let actions: [String]
    let children: [AXElementInfo]

    struct Frame: Codable {
        let x: Double
        let y: Double
        let width: Double
        let height: Double
    }
}

// MARK: - AX 工具函数
func axAttributeString(_ element: AXUIElement, _ attribute: String) -> String? {
    var value: CFTypeRef?
    let result = AXUIElementCopyAttributeValue(element, attribute as CFString, &value)
    guard result == .success, let val = value else { return nil }
    return "\(val)"
}

func axAttributeBool(_ element: AXUIElement, _ attribute: String) -> Bool {
    var value: CFTypeRef?
    let result = AXUIElementCopyAttributeValue(element, attribute as CFString, &value)
    guard result == .success, let val = value as? Bool else { return false }
    return val
}

func axAttributeRect(_ element: AXUIElement) -> CGRect? {
    var position: CFTypeRef?
    var size: CFTypeRef?
    let posResult = AXUIElementCopyAttributeValue(element, kAXPositionAttribute as CFString, &position)
    let sizeResult = AXUIElementCopyAttributeValue(element, kAXSizeAttribute as CFString, &size)
    guard posResult == .success, sizeResult == .success,
          let posVal = position as! AXValue?,
          let sizeVal = size as! AXValue?
    else { return nil }

    var p = CGPoint.zero
    var s = CGSize.zero
    let pOk = AXValueGetValue(posVal, .cgPoint, &p)
    let sOk = AXValueGetValue(sizeVal, .cgSize, &s)
    guard pOk, sOk else { return nil }
    return CGRect(origin: p, size: s)
}

func axAttributeActions(_ element: AXUIElement) -> [String] {
    var names: CFArray?
    let result = AXUIElementCopyActionNames(element, &names)
    guard result == .success, let actions = names as? [String] else { return [] }
    return actions
}

func axAttributeChildren(_ element: AXUIElement) -> [AXUIElement] {
    var children: CFTypeRef?
    let result = AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
    guard result == .success, let childArray = children as? [AXUIElement] else { return [] }
    return childArray
}

// MARK: - 递归遍历
func inspectElement(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 8) -> AXElementInfo? {
    guard depth <= maxDepth else { return nil }

    // 基本属性
    let role = axAttributeString(element, kAXRoleAttribute) ?? "?"
    let subrole = axAttributeString(element, kAXSubroleAttribute)
    let description = axAttributeString(element, kAXDescriptionAttribute) ?? ""
    let title = axAttributeString(element, kAXTitleAttribute) ?? ""
    let value = axAttributeString(element, kAXValueAttribute) ?? ""
    let help = axAttributeString(element, kAXHelpAttribute) ?? ""
    let label = axAttributeString(element, kAXLabelValueAttribute) ?? ""

    // 状态
    let isEnabled = axAttributeBool(element, kAXEnabledAttribute)
    let isFocused = axAttributeBool(element, kAXFocusedAttribute)
    // macOS 没有直接的 isVisible 属性，用 frame 是否为零判断
    let frame = axAttributeRect(element) ?? .zero

    // 动作
    let actions = axAttributeActions(element)

    // 递归子元素
    var children: [AXElementInfo] = []
    let childElements = axAttributeChildren(element)
    for child in childElements {
        // 跳过 AXRoleDescription 等辅助元素
        if let childInfo = inspectElement(child, depth: depth + 1, maxDepth: maxDepth) {
            children.append(childInfo)
        }
    }

    // 如果没有任何有用信息且没有子元素，跳过
    let hasContent = !description.isEmpty || !title.isEmpty || !value.isEmpty || !children.isEmpty
        || role != "?" || !actions.isEmpty
    guard hasContent || depth == 0 else { return nil }

    return AXElementInfo(
        role: role,
        subrole: subrole,
        description: description,
        title: title,
        value: value,
        help: help,
        label: label,
        frame: AXElementInfo.Frame(
            x: Double(frame.origin.x),
            y: Double(frame.origin.y),
            width: Double(frame.size.width),
            height: Double(frame.size.height)
        ),
        isEnabled: isEnabled,
        isFocused: isFocused,
        isVisible: frame.width > 0 && frame.height > 0,
        actions: actions,
        children: children
    )
}

// MARK: - 查找元素
func findElement(in info: AXElementInfo, desc: String? = nil, role: String? = nil) -> [AXElementInfo] {
    var results: [AXElementInfo] = []

    var match = true
    if let d = desc {
        match = match && (info.description.contains(d) || info.title.contains(d) || info.label.contains(d) || info.value.contains(d))
    }
    if let r = role {
        match = match && info.role == r
    }
    if match && hasContent(info) {
        results.append(info)
    }

    for child in info.children {
        results.append(contentsOf: findElement(in: child, desc: desc, role: role))
    }
    return results
}

func hasContent(_ info: AXElementInfo) -> Bool {
    return !info.description.isEmpty || !info.title.isEmpty || !info.role.isEmpty
}

// MARK: - 获取应用
func getAppElement(_ name: String) -> AXUIElement? {
    let apps = NSWorkspace.shared.runningApplications
    let searchName = name.lowercased().trimmingCharacters(in: .whitespaces)
    for app in apps {
        guard let appName = app.localizedName else { continue }
        let lowerAppName = appName.lowercased()
        // 精确匹配、包含匹配、Bundle ID 匹配
        if lowerAppName == searchName || lowerAppName.contains(searchName) || searchName.contains(lowerAppName) {
            return AXUIElementCreateApplication(app.processIdentifier)
        }
        // 也按 bundle ID 匹配
        if let bundleID = app.bundleIdentifier?.lowercased(), bundleID.contains(searchName) {
            return AXUIElementCreateApplication(app.processIdentifier)
        }
    }
    return nil
}

func getFrontmostApp() -> AXUIElement? {
    if let app = NSWorkspace.shared.frontmostApplication {
        return AXUIElementCreateApplication(app.processIdentifier)
    }
    return nil
}

// MARK: - 查找应用窗口
func getMainWindow(_ app: AXUIElement) -> AXUIElement? {
    var value: CFTypeRef?
    let result = AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &value)
    guard result == .success, let windows = value as? [AXUIElement], !windows.isEmpty else {
        return nil
    }
    return windows[0]
}

// MARK: - 格式化输出
func formatTree(_ info: AXElementInfo, indent: String = "") -> String {
    var result = "\(indent)\(info.role)"
    if !info.description.isEmpty { result += " [\(info.description)]" }
    if !info.title.isEmpty { result += " \"\(info.title)\"" }
    if !info.label.isEmpty { result += " label=\(info.label)" }
    if info.frame.width > 0 { result += " (\(Int(info.frame.x)),\(Int(info.frame.y))) \(Int(info.frame.width))x\(Int(info.frame.height))" }
    if !info.actions.isEmpty { result += " actions=\(info.actions.count)" }

    for child in info.children {
        result += "\n" + formatTree(child, indent: indent + "  ")
    }
    return result
}

// MARK: - 点击元素
func performClick(on info: AXElementInfo, targetDesc: String, app: AXUIElement) -> Bool {
    return clickElement(in: app, desc: targetDesc)
}

func clickElement(in app: AXUIElement, desc: String) -> Bool {
    // Try to find the element and press it
    return findAndPress(app: app, desc: desc)
}

func findAndPress(app: AXUIElement, desc: String) -> Bool {
    var value: CFTypeRef?
    let result = AXUIElementCopyAttributeValue(app, kAXChildrenAttribute as CFString, &value)
    guard result == .success, let children = value as? [AXUIElement] else { return false }

    for child in children {
        let d = axAttributeString(child, kAXDescriptionAttribute) ?? ""
        let t = axAttributeString(child, kAXTitleAttribute) ?? ""
        let l = axAttributeString(child, kAXLabelValueAttribute) ?? ""

        if d.contains(desc) || t.contains(desc) || l.contains(desc) {
            let pressResult = AXUIElementPerformAction(child, kAXPressAction as CFString)
            if pressResult == .success { return true }
        }

        if findAndPress(app: child, desc: desc) {
            return true
        }
    }
    return false
}

// MARK: - 主入口
func main() {
    let args = CommandLine.arguments

    var mode = "tree"
    var appName: String?
    var searchDesc: String?
    var searchRole: String?
    var maxDepth = 6
    var outputJSON = false

    var i = 1
    while i < args.count {
        switch args[i] {
        case "--app", "-a":
            i += 1
            appName = i < args.count ? args[i] : nil
        case "--find", "-f":
            mode = "find"
            i += 1
            searchDesc = i < args.count ? args[i] : nil
        case "--click", "-c":
            mode = "click"
            i += 1
            searchDesc = i < args.count ? args[i] : nil
        case "--role", "-r":
            i += 1
            searchRole = i < args.count ? args[i] : nil
        case "--depth", "-d":
            i += 1
            if i < args.count, let d = Int(args[i]) { maxDepth = d }
        case "--json", "-j":
            outputJSON = true
        case "--frontmost":
            appName = nil // explicitly use frontmost
        case "--help", "-h":
            print("""
            AX Inspector - macOS Accessibility Tree Inspector
            用法:
              \(args[0]) --app "Music"             查看 UI 树
              \(args[0]) --frontmost                查看前台应用
              \(args[0]) --find "播放" --app "Music" 搜索元素
              \(args[0]) --click "播放" --app "Music" 点击元素
              \(args[0]) --json --app "Music"       输出 JSON
            参数:
              --app, -a <名称>    指定应用
              --frontmost         使用前台应用
              --find, -f <文本>   搜索元素描述
              --click, -c <文本>  点击元素（按描述）
              --role, -r <角色>   按角色过滤
              --depth, -d <数字>  递归深度 (默认6)
              --json, -j         输出 JSON 格式
              --help, -h         显示帮助
            """)
            return
        default:
            break
        }
        i += 1
    }

    // 获取目标应用
    var app: AXUIElement?
    if let name = appName {
        app = getAppElement(name)
        if app == nil {
            print("❌ 未找到应用: \(name)")
            return
        }
    } else {
        app = getFrontmostApp()
        if app == nil {
            print("❌ 无法获取前台应用")
            return
        }
    }

    // 获取应用名称
    let appNameStr = appName ?? NSWorkspace.shared.frontmostApplication?.localizedName ?? "?"

    // 获取主窗口
    let targetElement: AXUIElement
    if let win = getMainWindow(app!) {
        targetElement = win
    } else if mode == "click" {
        let success = findAndPress(app: app!, desc: searchDesc ?? "")
        print(success ? "✅ 已点击: \(searchDesc ?? "")" : "❌ 未找到可点击元素: \(searchDesc ?? "")")
        return
    } else {
        // 检查应用级别的元素
        if let rootInfo = inspectElement(app!, maxDepth: maxDepth), !rootInfo.children.isEmpty {
            targetElement = app!
        } else {
            print("❌ 应用「\(appNameStr)」没有可访问的窗口或元素")
            return
        }
    }

    switch mode {
    case "tree":
        guard let rootInfo = inspectElement(targetElement, maxDepth: maxDepth) else {
            print("❌ 无法遍历 UI 树"); return
        }
        if outputJSON {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            if let jsonData = try? encoder.encode(rootInfo),
               let jsonStr = String(data: jsonData, encoding: .utf8) { print(jsonStr) }
        } else {
            let lines = formatTree(rootInfo).split(separator: "\n")
            print("📋 应用「\(appNameStr)」UI 树（\(lines.count) 个元素）:")
            print(formatTree(rootInfo))
        }

    case "find":
        guard let rootInfo = inspectElement(targetElement, maxDepth: maxDepth) else {
            print("❌ 无法遍历 UI 树"); return
        }
        let results = findElement(in: rootInfo, desc: searchDesc, role: searchRole)
        if results.isEmpty {
            print("❌ 未找到匹配元素（desc=\(searchDesc ?? ""), role=\(searchRole ?? "")）")
            return
        }
        if outputJSON {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            if let jsonData = try? encoder.encode(results),
               let jsonStr = String(data: jsonData, encoding: .utf8) { print(jsonStr) }
        } else {
            print("🔍 找到 \(results.count) 个元素:")
            for (i, elem) in results.enumerated() {
                let frame = elem.frame
                print("  [\(i+1)] \(elem.role) \"\(elem.description.isEmpty ? elem.title : elem.description)\" (\(Int(frame.x)),\(Int(frame.y))) \(Int(frame.width))x\(Int(frame.height))")
            }
        }

    case "click":
        let success = findAndPress(app: targetElement, desc: searchDesc ?? "")
        if success {
            print("✅ 已点击: \(searchDesc ?? "")")
        } else {
            guard let rootInfo = inspectElement(targetElement, maxDepth: maxDepth) else {
                print("❌ 无法遍历 UI 树"); return
            }
            let results = findElement(in: rootInfo, desc: searchDesc, role: searchRole)
            if let first = results.first {
                let f = first.frame
                print("pos:\(Int(f.x + f.width / 2)),\(Int(f.y + f.height / 2))")
            } else {
                print("❌ 未找到可点击元素: \(searchDesc ?? "")")
            }
        }

    default:
        print("❌ 未知模式: \(mode)")
    }
}

main()

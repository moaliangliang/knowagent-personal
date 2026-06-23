#!/usr/bin/env swift
/**
 * macOS 原生 Vision OCR — 比 tesseract 更准确的文字识别
 *
 * 用法:
 *   swift screen_ocr.swift <图片路径>                   # OCR 整图
 *   swift screen_ocr.swift <图片路径> --region 100,200,800,600  # 指定区域
 *   swift screen_ocr.swift <图片路径> --fast             # 快速模式(仅英文)
 *
 * 依赖: macOS 10.15+ (内置 Vision framework, 无需安装)
 */

import Cocoa
import Vision

// MARK: - 参数解析
let args = CommandLine.arguments
guard args.count >= 2 else {
    print("用法: \(args[0]) <图片路径> [--region x,y,w,h] [--fast]")
    exit(1)
}

let imagePath = args[1]
var regionRect: CGRect?
var fastMode = false

var i = 2
while i < args.count {
    switch args[i] {
    case "--region":
        i += 1
        let parts = args[i].split(separator: ",").compactMap { Int($0) }
        if parts.count == 4 {
            regionRect = CGRect(x: parts[0], y: parts[1], width: parts[2], height: parts[3])
        }
    case "--fast":
        fastMode = true
    default:
        break
    }
    i += 1
}

// MARK: - 加载图片
guard let image = NSImage(contentsOfFile: imagePath) else {
    print("❌ 无法加载图片: \(imagePath)")
    exit(1)
}

guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("❌ 无法转换图片")
    exit(1)
}

// MARK: - 可选区域裁剪
let sourceImage: CGImage
if let region = regionRect {
    guard let cropped = cgImage.cropping(to: region) else {
        print("❌ 区域裁剪失败")
        exit(1)
    }
    sourceImage = cropped
} else {
    sourceImage = cgImage
}

// MARK: - Vision OCR
func runOCR() {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = fastMode ? .fast : .accurate
    request.usesLanguageCorrection = true

    if fastMode {
        request.recognitionLanguages = ["en-US"]
    } else {
        request.recognitionLanguages = ["zh-Hans", "en-US"]
    }

    let handler = VNImageRequestHandler(cgImage: sourceImage, options: [:])

    do {
        try handler.perform([request])
    } catch {
        print("❌ OCR 失败: \(error.localizedDescription)")
        exit(1)
    }

    guard let observations = request.results, !observations.isEmpty else {
        print("📸 截屏已分析 (\(sourceImage.width)x\(sourceImage.height))")
        print("🔤 未识别到文字")
        exit(0)
    }

    // 按 Y 坐标分组（行），然后按 X 排序
    struct TextBlock {
        let text: String
        let y: Int
        let x: Int
    }

    var blocks: [TextBlock] = []
    for observation in observations {
        let text = observation.topCandidates(1).first?.string ?? ""
        let boundingBox = observation.boundingBox
        let y = Int((1 - boundingBox.origin.y - boundingBox.size.height) * CGFloat(sourceImage.height))
        let x = Int(boundingBox.origin.x * CGFloat(sourceImage.width))
        if !text.trimmingCharacters(in: .whitespaces).isEmpty {
            blocks.append(TextBlock(text: text, y: y, x: x))
        }
    }

    // 按行分组（Y 坐标相近的在同一行）
    blocks.sort { $0.y < $1.y || ($0.y == $1.y && $0.x < $1.x) }

    let lineThreshold = 20
    var lines: [[TextBlock]] = []
    var currentLine: [TextBlock] = []
    var lastY = -100

    for block in blocks {
        if abs(block.y - lastY) > lineThreshold {
            if !currentLine.isEmpty {
                lines.append(currentLine)
            }
            currentLine = [block]
        } else {
            currentLine.append(block)
        }
        lastY = block.y
    }
    if !currentLine.isEmpty {
        lines.append(currentLine)
    }

    // 每行内按 X 排序
    let sortedLines = lines.map { line in
        line.sorted { $0.x < $1.x }
    }

    // 输出
    let totalPixels = sourceImage.width * sourceImage.height
    let sizeKB = Double(totalPixels * 4) / 1024.0 / 1024.0
    print("📸 截屏已分析 (\(sourceImage.width)x\(sourceImage.height))")
    print("🔤 OCR 识别到 \(observations.count) 个文字块，\(sortedLines.count) 行:")

    for line in sortedLines {
        let lineText = line.map { $0.text }.joined(separator: " ")
        // 过滤纯标点行
        let stripped = lineText.trimmingCharacters(in: .punctuationCharacters).trimmingCharacters(in: .whitespaces)
        if !stripped.isEmpty {
            print("  \(lineText)")
        }
    }

    // 统计
    let totalChars = sortedLines.flatMap { $0 }.reduce(0) { $0 + $1.text.count }
    print("  ---")
    print("  📊 共 \(totalChars) 字符，\(sortedLines.count) 行")
}

runOCR()

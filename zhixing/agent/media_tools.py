"""Media commands module

Screen recording, audio recording, video info, OCR.
All cmd_* functions return str (plain text), format:
  ✅ success message
  ❌ error message
  📋 data/info
"""

import subprocess
import os
import shutil
import time
import json
import tempfile


# ── Helpers ──────────────────────────────────────────────

def _run_cmd(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Execute external command and return CompletedProcess."""
    # 使用 encoding+errors 防止非 UTF-8 stderr 导致崩溃
    return subprocess.run(
        cmd, capture_output=True, timeout=timeout, check=False,
        encoding="utf-8", errors="replace",
    )


def _fmt_size(path: str) -> str:
    """Return human-readable file size for a path."""
    try:
        size = os.path.getsize(path)
        if size < 1024:
            return f"{size}B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / 1024 ** 2:.1f}MB"
    except OSError:
        return "?"


def _default_path(prefix: str, ext: str) -> str:
    """Generate a timestamped default path under /tmp."""
    return f"/tmp/{prefix}_{int(time.time())}.{ext}"


# ── Screen Recording ────────────────────────────────────

def cmd_screen_record(params: dict) -> str:
    """Screen recording. duration=seconds, path?=output path (default /tmp/...).

    Uses ffmpeg with avfoundation input. Falls back to screencapture -V if ffmpeg
    is not available on macOS.
    """
    duration = params.get("duration")
    if duration is None:
        return "❌ screen_record requires 'duration' (seconds)"
    try:
        duration = int(duration)
    except (ValueError, TypeError):
        return "❌ duration must be an integer (seconds)"
    if duration <= 0:
        return "❌ duration must be positive"
    if duration > 300:
        return "❌ duration capped at 300 seconds (5 min)"

    path = params.get("path", _default_path("screen_record", "mp4"))

    # ── ffmpeg path ──────────────────────────────────────
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        # macOS: avfoundation device. ":0" = main screen (video+audio), "1" = audio
        # Try primary display index 1 (most common on MacBooks: 1 is the built-in display)
        # We attempt :1 first, fall back to :0
        for device_index in ("1", "0"):
            try:
                r = _run_cmd([
                    ffmpeg, "-y",
                    "-f", "avfoundation",
                    "-capture_cursor", "1",
                    "-i", f"{device_index}:none",
                    "-t", str(duration),
                    "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    path,
                ], timeout=duration + 30)
                if r.returncode == 0 and os.path.exists(path):
                    break
            except Exception:
                continue
        else:
            return "❌ screen_record: ffmpeg avfoundation capture failed (no usable display device)"

        if os.path.exists(path) and os.path.getsize(path) > 0:
            return f"✅ Screen recording saved: {path} ({_fmt_size(path)}, {duration}s)"
        return "❌ screen_record: output file is empty or missing"

    # ── screencapture fallback (macOS) ───────────────────
    screencap = shutil.which("screencapture")
    if not screencap:
        return "❌ screen_record: neither ffmpeg nor screencapture found"

    try:
        r = _run_cmd([screencap, "-V", str(duration * 1000), "-T", "0", path],
                       timeout=duration + 30)
        if r.returncode != 0 or not os.path.exists(path):
            err = r.stderr.strip() or "unknown error"
            return f"❌ screen_record: screencapture failed: {err}"
        return f"✅ Screen recording saved: {path} ({_fmt_size(path)}, {duration}s)"
    except subprocess.TimeoutExpired:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return f"✅ Screen recording saved: {path} ({_fmt_size(path)}, {duration}s)"
        return "❌ screen_record: screencapture timed out"
    except FileNotFoundError:
        return "❌ screen_record: screencapture not found"
    except Exception as e:
        return f"❌ screen_record error: {e}"


# ── Audio Recording ─────────────────────────────────────

def cmd_audio_record(params: dict) -> str:
    """Audio recording. duration=seconds, path?=output path (default /tmp/...).

    Uses ffmpeg first. Falls back to sox, then rec.
    """
    duration = params.get("duration")
    if duration is None:
        return "❌ audio_record requires 'duration' (seconds)"
    try:
        duration = int(duration)
    except (ValueError, TypeError):
        return "❌ duration must be an integer (seconds)"
    if duration <= 0:
        return "❌ duration must be positive"
    if duration > 600:
        return "❌ duration capped at 600 seconds (10 min)"

    path = params.get("path", _default_path("audio_record", "m4a"))

    # ── ffmpeg ───────────────────────────────────────────
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        try:
            r = _run_cmd([
                ffmpeg, "-y",
                "-f", "avfoundation",
                "-i", ":none:0",  # default audio input (macOS)
                "-t", str(duration),
                "-acodec", "aac",
                "-b:a", "128k",
                path,
            ], timeout=duration + 30)
            if r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 0:
                return f"✅ Audio recording saved: {path} ({_fmt_size(path)}, {duration}s)"
            # Some Macs may use a different audio device index; try ":none:1"
            r = _run_cmd([
                ffmpeg, "-y",
                "-f", "avfoundation",
                "-i", ":none:1",
                "-t", str(duration),
                "-acodec", "aac",
                "-b:a", "128k",
                path,
            ], timeout=duration + 30)
            if r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 0:
                return f"✅ Audio recording saved: {path} ({_fmt_size(path)}, {duration}s)"
            err = r.stderr.strip() or "no audio input device found"
            return f"❌ audio_record: ffmpeg failed: {err}"
        except subprocess.TimeoutExpired:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return f"✅ Audio recording saved: {path} ({_fmt_size(path)}, {duration}s)"
            return "❌ audio_record: ffmpeg timed out"
        except Exception as e:
            return f"❌ audio_record: ffmpeg error: {e}"

    # ── sox fallback ─────────────────────────────────────
    sox = shutil.which("sox")
    if sox:
        try:
            r = _run_cmd([sox, "-d", path, "trim", "0", str(duration)],
                           timeout=duration + 30)
            if r.returncode == 0 and os.path.exists(path):
                return f"✅ Audio recording saved: {path} ({_fmt_size(path)}, {duration}s)"
            err = r.stderr.strip() or "unknown error"
            return f"❌ audio_record: sox failed: {err}"
        except subprocess.TimeoutExpired:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return f"✅ Audio recording saved: {path} ({_fmt_size(path)}, {duration}s)"
            return "❌ audio_record: sox timed out"
        except Exception as e:
            return f"❌ audio_record: sox error: {e}"

    # ── rec fallback (from sox package) ──────────────────
    rec = shutil.which("rec")
    if rec:
        try:
            r = _run_cmd([rec, "-b", "16", path, "trim", "0", str(duration)],
                           timeout=duration + 30)
            if r.returncode == 0 and os.path.exists(path):
                return f"✅ Audio recording saved: {path} ({_fmt_size(path)}, {duration}s)"
            err = r.stderr.strip() or "unknown error"
            return f"❌ audio_record: rec failed: {err}"
        except subprocess.TimeoutExpired:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return f"✅ Audio recording saved: {path} ({_fmt_size(path)}, {duration}s)"
            return "❌ audio_record: rec timed out"
        except Exception as e:
            return f"❌ audio_record: rec error: {e}"

    return "❌ audio_record: no recording tool found (install ffmpeg or sox)"


# ── Video Info ──────────────────────────────────────────

def cmd_video_info(params: dict) -> str:
    """Read video metadata. path=file path.

    Uses ffprobe to extract format, duration, codec, resolution.
    """
    path = params.get("path", "")
    if not path:
        return "❌ video_info requires 'path'"
    if not os.path.isfile(path):
        return f"❌ File not found: {path}"

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return "❌ video_info: ffprobe not found (install ffmpeg)"

    try:
        # Get format info
        fmt_r = _run_cmd([
            ffprobe, "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            path,
        ], timeout=30)

        if fmt_r.returncode != 0:
            err = fmt_r.stderr.strip() or "ffprobe parse error"
            # Try simpler fallback: just size
            size_str = _fmt_size(path)
            return f"❌ video_info: {err}\n📋 File size: {size_str}"

        data = json.loads(fmt_r.stdout)
    except json.JSONDecodeError:
        size_str = _fmt_size(path)
        return f"❌ video_info: could not parse ffprobe output\n📋 File size: {size_str}"
    except subprocess.TimeoutExpired:
        return "❌ video_info: ffprobe timed out"
    except FileNotFoundError:
        return "❌ video_info: ffprobe not found"
    except Exception as e:
        return f"❌ video_info error: {e}"

    # ── Format ──────────────────────────────────────────────
    fmt = data.get("format", {})
    format_name = fmt.get("format_name", "?")
    file_size = _fmt_size(path)

    # Duration
    duration_sec = fmt.get("duration")
    duration_str = "?"
    if duration_sec:
        try:
            secs = float(duration_sec)
            mins = int(secs // 60)
            secs_remain = int(secs % 60)
            duration_str = f"{mins}:{secs_remain:02d}"
        except ValueError:
            duration_str = duration_sec

    bit_rate = fmt.get("bit_rate", "")
    bit_rate_str = f"{int(bit_rate) // 1000}kbps" if bit_rate and bit_rate.isdigit() else "?"

    # ── Streams ─────────────────────────────────────────────
    streams = data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    lines = [f"📋 Video info: {os.path.basename(path)}"]
    lines.append(f"   Path: {path}")
    lines.append(f"   Size: {file_size}")
    lines.append(f"   Format: {format_name}")
    lines.append(f"   Duration: {duration_str}")
    lines.append(f"   Bitrate: {bit_rate_str}")

    # Video streams
    if video_streams:
        lines.append(f"   Video streams ({len(video_streams)}):")
        for vs in video_streams:
            codec = vs.get("codec_name", "?")
            width = vs.get("width", "?")
            height = vs.get("height", "?")
            fps = vs.get("r_frame_rate", "?")
            # Simplify fps fraction
            if fps and "/" in str(fps):
                try:
                    num, den = str(fps).split("/")
                    fps = f"{float(num) / float(den):.2f}"
                except (ValueError, ZeroDivisionError):
                    pass
            lines.append(f"      {codec}  {width}x{height}  {fps}fps")
    else:
        lines.append("   Video: none")

    # Audio streams
    if audio_streams:
        lines.append(f"   Audio streams ({len(audio_streams)}):")
        for audio in audio_streams:
            acodec = audio.get("codec_name", "?")
            sample_rate = audio.get("sample_rate", "?")
            channels = audio.get("channels", "?")
            lines.append(f"      {acodec}  {sample_rate}Hz  {channels}ch")
    else:
        lines.append("   Audio: none")

    return "\n".join(lines)


# ── OCR (Tesseract) ─────────────────────────────────────

def cmd_ocr_file(params: dict) -> str:
    """OCR a file (image or PDF). path=file path, lang?=language (default chi_sim+eng).

    Uses tesseract via subprocess. Supports common image formats and PDFs.
    """
    path = params.get("path", "")
    if not path:
        return "❌ ocr_file requires 'path'"
    if not os.path.isfile(path):
        return f"❌ File not found: {path}"

    lang = params.get("lang", "chi_sim+eng")

    tesseract = shutil.which("tesseract")
    if not tesseract:
        return "❌ ocr_file: tesseract not found (install with: brew install tesseract tesseract-lang)"

    # Check file extension
    ext = os.path.splitext(path)[1].lower()
    image_exts = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}
    pdf_exts = {".pdf"}

    if ext not in image_exts | pdf_exts:
        return f"❌ ocr_file: unsupported format '{ext}'. Supported: {', '.join(sorted(image_exts | pdf_exts))}"

    try:
        # Tesseract can read images directly; for PDFs we pass the file
        r = _run_cmd([tesseract, path, "stdout", "-l", lang, "--psm", "3"],
                       timeout=120)

        if r.returncode != 0:
            err = r.stderr.strip()
            if "Error" in err or "Failed" in err or "Cannot" in err:
                return f"❌ ocr_file: tesseract error: {err[:500]}"

        text = r.stdout.strip()
        if not text:
            return f"📋 OCR result: (no text detected in {os.path.basename(path)})"

        lines = text.split("\n")
        non_empty = [l for l in lines if l.strip()]
        preview = text[:2000]
        if len(text) > 2000:
            preview += f"\n... (truncated, {len(text)} total chars)"

        return (
            f"📋 OCR result for {os.path.basename(path)}\n"
            f"   Language: {lang}\n"
            f"   Lines: {len(non_empty)}\n"
            f"   Chars: {len(text)}\n"
            f"\n{preview}"
        )

    except subprocess.TimeoutExpired:
        return "❌ ocr_file: tesseract timed out (file may be too large)"
    except FileNotFoundError:
        return "❌ ocr_file: tesseract not found"
    except Exception as e:
        return f"❌ ocr_file error: {e}"


# ── Pro 版：OCR 增强（批量/多语言/自动复制） ────────────


def cmd_ocr_pro(params: dict) -> str:
    """📸 Pro 版 OCR — 批量识别/多语言检测/自动复制。

    参数:
        action (str): file | batch | dir | lang_detect
        path (str): 文件或目录路径
        lang (str, optional): 语言代码，默认自动检测
        copy (bool, optional): 是否自动复制结果到剪贴板，默认 true
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("enhanced_ocr")
    if guard is not None:
        return guard

    action = params.get("action", "file")
    path = params.get("path", "")
    lang = params.get("lang", "auto")
    copy_result = params.get("copy", "true") in ("true", "True", "1", True)

    tesseract = shutil.which("tesseract")
    if not tesseract:
        return "❌ tesseract not found (install: brew install tesseract tesseract-lang)"

    # 获取已安装语言
    installed_langs = _get_tesseract_langs(tesseract)

    if action == "lang_detect":
        return _ocr_lang_info(installed_langs, tesseract)

    if action == "batch":
        return _ocr_batch(tesseract, path, lang, installed_langs, copy_result)

    if action in ("dir", "directory"):
        return _ocr_dir(tesseract, path, lang, installed_langs, copy_result)

    if action in ("vision", "v"):
        return _ocr_vision(path)

    if action in ("vision_batch", "vb"):
        return _ocr_vision_batch(path)

    # action == "file" — 增强单文件 OCR
    return _ocr_file_pro(tesseract, path, lang, installed_langs, copy_result)


def _get_tesseract_langs(tesseract: str) -> list[str]:
    """获取 tesseract 已安装的语言列表。"""
    try:
        r = subprocess.run([tesseract, "--list-langs"], capture_output=True, text=True, timeout=10)
        # tesseract 输出去 stdout，偶尔某些版本走 stderr
        raw = r.stdout or r.stderr or ""
        langs = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line or line.startswith("List of"):
                continue
            langs.append(line)
        return langs
    except Exception:
        return []


def _detect_best_lang(text: str, installed_langs: list[str]) -> str:
    """根据 OCR 结果文本自动判断最佳语言。"""
    if not text or len(text) < 5:
        return "eng"

    import re
    cn_chars = len(re.findall(r'[一-鿿]', text))
    jp_chars = len(re.findall(r'[぀-ゟ゠-ヿ]', text))
    kr_chars = len(re.findall(r'[가-힯]', text))
    total = len(text.strip())

    if cn_chars > total * 0.1:
        base = "chi_sim"
        if "chi_sim" in installed_langs:
            return "chi_sim+eng"
        return "eng"
    if jp_chars > total * 0.1:
        base = "jpn"
        return f"{base}+eng" if base in installed_langs else "eng"
    if kr_chars > total * 0.1:
        base = "kor"
        return f"{base}+eng" if base in installed_langs else "eng"
    return "eng"


def _ocr_file_pro(tesseract: str, path: str, lang: str, installed: list[str], copy_result: bool) -> str:
    """增强单文件 OCR — 自动语言检测 + 复制结果。"""
    if not path:
        return "❌ ocr_pro 需要 path 参数"
    if not os.path.isfile(path):
        return f"❌ 文件不存在: {path}"

    # 自动检测语言
    if lang == "auto":
        lang = "chi_sim+eng" if "chi_sim" in installed else "eng"

    try:
        r = _run_cmd([tesseract, path, "stdout", "-l", lang, "--psm", "3"], timeout=120)
        if r.returncode != 0:
            return f"❌ OCR 失败: {r.stderr.strip()[:200]}"

        text = r.stdout.strip()
        if not text:
            return f"📋 OCR 结果:（未识别到文字）"

        # 自动复制到剪贴板
        if copy_result:
            _copy_to_clipboard(text)

        lines = [l for l in text.split("\n") if l.strip()]
        preview = text[:3000]

        result = (
            f"📋 OCR 识别结果 — {os.path.basename(path)}\n"
            f"   语言: {lang}  |  行数: {len(lines)}  |  字符: {len(text)}\n"
            f"   {'✅ 已复制到剪贴板' if copy_result else ''}\n"
            f"\n{preview}"
        )
        if len(text) > 3000:
            result += f"\n...（共 {len(text)} 字符，已截断）"
        return result

    except subprocess.TimeoutExpired:
        return "❌ OCR 超时（文件过大）"
    except Exception as e:
        return f"❌ OCR 异常: {e}"


def _ocr_batch(tesseract: str, path: str, lang: str, installed: list[str], copy_result: bool) -> str:
    """批量 OCR — 处理多个文件（逗号分隔或通配符）。"""
    import glob

    files = []
    for p in path.split(","):
        p = p.strip()
        expanded = os.path.expanduser(p)
        if os.path.isfile(expanded):
            files.append(expanded)
        else:
            files.extend(glob.glob(expanded))

    if not files:
        return "❌ 未找到匹配的文件"

    image_exts = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}
    image_files = [f for f in files if os.path.splitext(f)[1].lower() in image_exts]

    if not image_files:
        return "❌ 未找到支持的图片格式"

    if lang == "auto":
        lang = "chi_sim+eng" if "chi_sim" in installed else "eng"

    all_results = []
    success = 0
    for img in image_files[:20]:  # 最多 20 张
        try:
            r = _run_cmd([tesseract, img, "stdout", "-l", lang, "--psm", "3"], timeout=60)
            if r.returncode == 0 and r.stdout.strip():
                all_results.append(f"── {os.path.basename(img)} ──\n{r.stdout.strip()}")
                success += 1
        except Exception:
            pass

    result_text = "\n\n".join(all_results)

    if copy_result and result_text:
        _copy_to_clipboard(result_text)

    return (
        f"📋 批量 OCR — {success}/{len(image_files)} 成功\n"
        f"   语言: {lang}\n"
        f"   {'✅ 已复制到剪贴板' if copy_result else ''}\n"
        f"\n{result_text[:3000]}"
    )


def _ocr_dir(tesseract: str, path: str, lang: str, installed: list[str], copy_result: bool) -> str:
    """OCR 整个目录的图片。"""
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        return f"❌ 目录不存在: {path}"

    image_exts = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}
    all_files = [
        os.path.join(path, f) for f in os.listdir(path)
        if os.path.splitext(f)[1].lower() in image_exts
    ]

    if not all_files:
        return f"❌ 目录中未找到图片: {path}"

    return _ocr_batch(tesseract, ",".join(all_files[:20]), lang, installed, copy_result)


def _ocr_vision(path: str) -> str:
    """使用 macOS 原生 Vision Framework 做 OCR（比 Tesseract 更准）。"""
    if not path:
        return "❌ vision OCR 需要 path 参数"
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return f"❌ 文件不存在: {path}"

    # 查找 screen_ocr 二进制
    _BIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "swift")
    binary = os.path.join(os.path.expanduser("~/.zhixing/bin"), "screen_ocr")
    if not os.path.exists(binary):
        binary = os.path.join(_BIN_DIR, "screen_ocr")
    if not os.path.exists(binary):
        # 尝试编译
        src = os.path.join(os.path.dirname(binary), "screen_ocr.swift")
        if os.path.exists(src):
            try:
                subprocess.run(["swiftc", "-O", "-o", binary, src], capture_output=True, timeout=60)
            except Exception:
                pass
    if not os.path.exists(binary):
        return "❌ screen_ocr 未编译，运行: cd swift && swiftc -O -o screen_ocr screen_ocr.swift"

    try:
        r = subprocess.run(
            [binary, path],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        result = r.stdout.strip()
        if r.returncode != 0:
            return f"❌ Vision OCR 失败: {result[:200]}"

        # 提取纯文本行（去掉分析信息）
        lines = [l.strip() for l in result.split("\n") if l.strip() and not l.startswith("📸") and not l.startswith("🔤") and not l.startswith("  ---") and not l.startswith("  📊")]

        # 复制到剪贴板
        text = "\n".join(lines)
        _copy_to_clipboard(text)

        return (
            f"📸 Vision Framework OCR — {os.path.basename(path)}\n"
            f"   ⚡ macOS 原生引擎 | 中英文自动识别\n"
            f"   ✅ 结果已复制到剪贴板\n"
            f"\n{result}"
        )
    except subprocess.TimeoutExpired:
        return "❌ Vision OCR 超时"
    except Exception as e:
        return f"❌ Vision OCR 异常: {e}"


def _ocr_vision_batch(path: str) -> str:
    """批量 Vision OCR（目录或逗号分隔的文件列表）。"""
    import glob

    path = os.path.expanduser(path)
    files = []

    if os.path.isdir(path):
        image_exts = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}
        files = [
            os.path.join(path, f) for f in sorted(os.listdir(path))
            if os.path.splitext(f)[1].lower() in image_exts
        ][:20]
    else:
        for p in path.split(","):
            p = p.strip()
            expanded = os.path.expanduser(p)
            if os.path.isfile(expanded):
                files.append(expanded)
            else:
                files.extend(glob.glob(expanded))

    if not files:
        return "❌ 未找到图片文件"

    results = []
    success = 0
    for img in files:
        try:
            r = _ocr_vision(img)
            if "❌" not in r:
                success += 1
            # 提取 OCR 结果中的文字部分
            lines = r.split("\n")
            text_lines = [l for l in lines if not l.startswith("📸") and not l.startswith("   ⚡") and not l.startswith("   ✅") and not l.startswith("📋") and l.strip()]
            text = "\n".join(text_lines).strip()
            if text:
                results.append(f"── {os.path.basename(img)} ──\n{text}")
        except Exception:
            pass

    all_text = "\n\n".join(results)
    if all_text:
        _copy_to_clipboard(all_text)

    return (
        f"📸 Vision 批量 OCR — {success}/{len(files)} 成功\n"
        f"   ⚡ macOS 原生引擎 | 自动中英文识别\n"
        f"   ✅ 已复制到剪贴板\n"
        f"\n{all_text[:3000]}"
    )


def _ocr_lang_info(installed: list[str], tesseract: str) -> str:
    """显示已安装的 OCR 语言。"""
    lines = ["🌐 OCR 已安装语言:"]
    key_langs = {"eng": "英语", "chi_sim": "简体中文", "chi_tra": "繁体中文",
                 "jpn": "日语", "kor": "韩语", "fra": "法语", "deu": "德语",
                 "spa": "西班牙语", "rus": "俄语"}
    for lang in sorted(installed):
        name = key_langs.get(lang, "")
        tag = f" ({name})" if name else ""
        lines.append(f"  {lang}{tag}")
    lines.append("")
    lines.append("安装更多语言: brew install tesseract-lang")
    return "\n".join(lines)


def _copy_to_clipboard(text: str):
    """将文本复制到 macOS 剪贴板。"""
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(text.encode("utf-8"), timeout=5)
    except Exception:
        pass


# ── Command Registration ───────────────────────────────

COMMANDS: dict = {
    "screen_record": cmd_screen_record,
    "audio_record": cmd_audio_record,
    "video_info": cmd_video_info,
    "ocr_file": cmd_ocr_file,
    "ocr_pro": cmd_ocr_pro,
}

TOOL_SCHEMAS: dict = {
    "ocr_pro": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["file", "batch", "dir", "lang_detect", "vision", "vision_batch"],
                "description": "操作: file=单文件增强, batch=批量, dir=目录, lang_detect=查看语言, vision=Vision原生OCR, vision_batch=Vision批量",
            },
            "path": {
                "type": "string",
                "description": "文件路径 / 目录路径 / 批量路径（逗号分隔）",
            },
            "lang": {
                "type": "string",
                "description": "语言代码，默认 auto（自动检测）",
            },
            "copy": {
                "type": "boolean",
                "description": "是否自动复制结果到剪贴板，默认 true",
            },
        },
        "required": ["action"],
    },
    "screen_record": {
        "type": "object",
        "properties": {
            "duration": {
                "type": "integer",
                "description": "Recording duration in seconds (max 300)",
            },
            "path": {
                "type": "string",
                "description": "Output file path (default: /tmp/screen_record_<timestamp>.mp4)",
            },
        },
        "required": ["duration"],
    },
    "audio_record": {
        "type": "object",
        "properties": {
            "duration": {
                "type": "integer",
                "description": "Recording duration in seconds (max 600)",
            },
            "path": {
                "type": "string",
                "description": "Output file path (default: /tmp/audio_record_<timestamp>.m4a)",
            },
        },
        "required": ["duration"],
    },
    "video_info": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the video file",
            },
        },
        "required": ["path"],
    },
    "ocr_file": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the image or PDF file",
            },
            "lang": {
                "type": "string",
                "description": "Tesseract language(s), e.g. chi_sim+eng (default), eng, chi_sim+eng+fra",
            },
        },
        "required": ["path"],
    },
}

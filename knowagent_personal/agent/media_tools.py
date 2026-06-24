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
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


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


# ── Command Registration ───────────────────────────────

COMMANDS: dict = {
    "screen_record": cmd_screen_record,
    "audio_record": cmd_audio_record,
    "video_info": cmd_video_info,
    "ocr_file": cmd_ocr_file,
}

TOOL_SCHEMAS: dict = {
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

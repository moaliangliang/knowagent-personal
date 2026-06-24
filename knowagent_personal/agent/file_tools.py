"""macOS 文件管理命令模块

文件搜索、内容搜索、压缩解压、回收站、重复文件查找、图片转换。
所有 cmd_* 函数统一返回 str（纯文本），格式：
  ✅ 成功信息
  ❌ 错误信息
"""

import hashlib
import os
import re
import subprocess
import tempfile
from collections import defaultdict


# ── 工具函数 ─────────────────────────────────────────────

def _run_cmd(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """执行外部命令并返回 CompletedProcess，异常时抛出。"""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _ensure_dir(path: str) -> str:
    """展开 ~ 并确保父目录存在。"""
    path = os.path.abspath(os.path.expanduser(path))
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


# ── 文件搜索（Spotlight）─────────────────────────────────

def cmd_file_search(params: dict) -> str:
    """使用 Spotlight (mdfind) 搜索文件。"""
    query = params.get("query", "")
    directory = params.get("dir")
    limit = int(params.get("limit", 20))

    if not query or not query.strip():
        return "❌ query 参数不能为空"

    limit = max(1, min(limit, 500))

    try:
        cmd = ["mdfind"]
        if directory:
            dir_path = os.path.abspath(os.path.expanduser(directory))
            if not os.path.isdir(dir_path):
                return f"❌ 目录不存在: {dir_path}"
            cmd.extend(["-onlyin", dir_path])
        cmd.append(query.strip())

        r = _run_cmd(cmd, timeout=30)
        if r.returncode != 0:
            err = r.stderr.strip() or "mdfind 无输出"
            return f"❌ Spotlight 搜索失败: {err}"

        results = [line for line in r.stdout.split("\n") if line.strip()]
        total = len(results)
        shown = results[:limit]

        lines = [
            f"✅ Spotlight 搜索: {query}",
            f"   共找到 {total} 个结果，显示前 {len(shown)} 个:",
        ]
        for i, path in enumerate(shown, 1):
            lines.append(f"   {i:>4}. {path}")

        if total > limit:
            lines.append(f"   ... 还有 {total - limit} 个结果被截断")

        return "\n".join(lines)

    except subprocess.TimeoutExpired:
        return "❌ Spotlight 搜索超时（30秒）"
    except FileNotFoundError:
        return "❌ 未找到 mdfind 命令（需 macOS Spotlight）"
    except Exception as e:
        return f"❌ 搜索异常: {e}"


# ── 文件内容搜索（grep）───────────────────────────────────

def cmd_file_grep(params: dict) -> str:
    """在文件中搜索文本内容。"""
    pattern = params.get("pattern", "")
    path = params.get("path", "")
    extension = params.get("ext")

    if not pattern:
        return "❌ pattern 参数不能为空"
    if not path:
        return "❌ path 参数不能为空"

    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        return f"❌ 路径不存在: {path}"

    limit = 30

    try:
        cmd = ["grep", "-rn"]
        if extension:
            ext = extension if extension.startswith(".") else f".{extension}"
            cmd.append(f"--include=*{ext}")
        cmd.append(pattern)
        cmd.append(path)

        r = _run_cmd(cmd, timeout=120)
        if r.returncode == 1:
            return f"✅ 未找到匹配 '{pattern}' 的内容"
        if r.returncode != 0 and r.returncode != 1:
            err = r.stderr.strip() or "grep 错误"
            return f"❌ 搜索失败: {err}"

        results = [line for line in r.stdout.split("\n") if line.strip()]
        total = len(results)
        shown = results[:limit]

        lines = [
            f"✅ Grep '{pattern}' in {path}",
            f"   共 {total} 个匹配，显示前 {len(shown)} 个:",
        ]
        for i, line in enumerate(shown, 1):
            # 截断长行
            truncated = line[:300]
            lines.append(f"   {i:>4}. {truncated}")
            if len(line) > 300:
                lines[-1] += "..."

        if total > limit:
            lines.append(f"   ... 还有 {total - limit} 个匹配被截断")

        return "\n".join(lines)

    except subprocess.TimeoutExpired:
        return "❌ Grep 搜索超时（120秒），目录过大或文件过多"
    except FileNotFoundError:
        return "❌ 未找到 grep 命令"
    except Exception as e:
        return f"❌ 搜索异常: {e}"


# ── 压缩 ─────────────────────────────────────────────────

def cmd_compress(params: dict) -> str:
    """压缩文件或目录。"""
    path = params.get("path", "")
    format = params.get("format", "zip")
    output = params.get("output")

    if not path:
        return "❌ path 参数不能为空"

    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        return f"❌ 路径不存在: {path}"

    format = format.strip().lower()
    if format not in ("zip", "tar", "tar.gz", "tar.bz2", "tgz", "tbz2"):
        return f"❌ 不支持的格式: {format}，支持: zip, tar, tar.gz, tar.bz2, tgz, tbz2"

    # 生成默认输出路径
    if not output:
        base = os.path.basename(path.rstrip("/"))
        output = os.path.join(os.path.dirname(path), base)
        if format == "zip":
            output += ".zip"
        elif format in ("tar",):
            output += ".tar"
        elif format in ("tar.gz", "tgz"):
            output = output.rstrip(".tar.gz").rstrip(".tgz")
            output += ".tar.gz"
        elif format in ("tar.bz2", "tbz2"):
            output = output.rstrip(".tar.bz2").rstrip(".tbz2")
            output += ".tar.bz2"

    output = _ensure_dir(output)

    try:
        if format == "zip":
            # 使用 zip 命令
            if os.path.isdir(path):
                # zip -r output.zip dir/
                cmd = ["zip", "-r", output, path]
            else:
                cmd = ["zip", output, path]
            r = _run_cmd(cmd, timeout=300)

        elif format == "tar":
            cmd = ["tar", "-cf", output, path]
            r = _run_cmd(cmd, timeout=300)

        elif format in ("tar.gz", "tgz"):
            cmd = ["tar", "-czf", output, path]
            r = _run_cmd(cmd, timeout=300)

        elif format in ("tar.bz2", "tbz2"):
            cmd = ["tar", "-cjf", output, path]
            r = _run_cmd(cmd, timeout=300)

        else:
            return f"❌ 不支持的格式: {format}"

        if r.returncode != 0:
            err = r.stderr.strip() or "压缩失败"
            return f"❌ 压缩失败: {err}"

        # 检查输出文件大小
        size_bytes = os.path.getsize(output)
        size_str = _format_size(size_bytes)

        return (
            f"✅ 压缩完成\n"
            f"   源文件: {path}\n"
            f"   输出:   {output}\n"
            f"   格式:   {format}\n"
            f"   大小:   {size_str}"
        )

    except subprocess.TimeoutExpired:
        return "❌ 压缩超时（300秒）"
    except FileNotFoundError:
        return "❌ 未找到压缩命令（需要 zip/tar）"
    except Exception as e:
        return f"❌ 压缩异常: {e}"


# ── 解压 ─────────────────────────────────────────────────

def cmd_extract(params: dict) -> str:
    """自动检测格式并解压文件。"""
    path = params.get("path", "")
    output = params.get("output")

    if not path:
        return "❌ path 参数不能为空"

    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(path):
        return f"❌ 文件不存在: {path}"

    # 自动检测格式
    filename = path.lower()
    if filename.endswith(".zip"):
        fmt = "zip"
    elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        fmt = "tar.gz"
    elif filename.endswith(".tar.bz2") or filename.endswith(".tbz2"):
        fmt = "tar.bz2"
    elif filename.endswith(".tar"):
        fmt = "tar"
    else:
        return "❌ 无法识别的压缩格式，支持: zip, tar, tar.gz, tar.bz2, tgz, tbz2"

    # 默认输出目录：和压缩包同名（去掉扩展名）
    if not output:
        base = os.path.basename(path)
        for ext in [".tar.gz", ".tar.bz2", ".tgz", ".tbz2", ".zip", ".tar"]:
            if base.lower().endswith(ext):
                base = base[: -len(ext)]
                break
        output = os.path.join(os.path.dirname(path), base)
    output = _ensure_dir(output)

    try:
        if fmt == "zip":
            cmd = ["unzip", "-o", path, "-d", output]
            r = _run_cmd(cmd, timeout=300)

        elif fmt in ("tar", "tar.gz", "tar.bz2"):
            # tar 自动检测压缩格式
            cmd = ["tar", "-xf", path, "-C", output]
            r = _run_cmd(cmd, timeout=300)

        else:
            return f"❌ 不支持的格式: {fmt}"

        if r.returncode != 0:
            err = r.stderr.strip() or "解压失败"
            return f"❌ 解压失败: {err}"

        # 统计解压出的文件数
        extracted_count = 0
        for root, dirs, files in os.walk(output):
            extracted_count += len(files) + len(dirs)

        return (
            f"✅ 解压完成\n"
            f"   源文件: {path}\n"
            f"   输出目录: {output}\n"
            f"   格式:     {fmt}\n"
            f"   解出数量: {extracted_count} 个项目"
        )

    except subprocess.TimeoutExpired:
        return "❌ 解压超时（300秒）"
    except FileNotFoundError:
        if fmt == "zip":
            return "❌ 未找到 unzip 命令"
        return "❌ 未找到 tar 命令"
    except Exception as e:
        return f"❌ 解压异常: {e}"


# ── 回收站 ───────────────────────────────────────────────

def cmd_trash(params: dict) -> str:
    """将文件移到废纸篓或清空废纸篓。"""
    path = params.get("path")
    action = params.get("action", "trash")
    action = action.strip().lower()

    if action == "trash":
        if not path:
            return "❌ path 参数不能为空（action=trash 时需要指定路径）"

        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(path):
            return f"❌ 路径不存在: {path}"

        try:
            # 使用 osascript 移动到废纸篓
            script = (
                f'tell application "Finder"\n'
                f'    delete POSIX file "{path}"\n'
                f"end tell"
            )
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode != 0:
                err = r.stderr.strip()
                # 有些情况 Finder 拒绝删除 (权限问题等)
                return f"❌ 移到废纸篓失败: {err or 'Finder 拒绝操作'}"
            return f"✅ 已移到废纸篓: {path}"

        except subprocess.TimeoutExpired:
            return "❌ 移到废纸篓超时"
        except FileNotFoundError:
            return "❌ 未找到 osascript 命令"
        except Exception as e:
            return f"❌ 移到废纸篓异常: {e}"

    elif action == "empty":
        try:
            script = (
                'tell application "Finder"\n'
                "    empty trash\n"
                "end tell"
            )
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode != 0:
                err = r.stderr.strip()
                return f"❌ 清空废纸篓失败: {err}"
            return "✅ 废纸篓已清空"

        except subprocess.TimeoutExpired:
            return "❌ 清空废纸篓超时"
        except FileNotFoundError:
            return "❌ 未找到 osascript 命令"
        except Exception as e:
            return f"❌ 清空废纸篓异常: {e}"

    else:
        return "❌ action 须为 'trash' 或 'empty'"


# ── 重复文件查找 ──────────────────────────────────────────

def cmd_duplicate_finder(params: dict) -> str:
    """查找指定目录下的重复文件（按大小分组 -> MD5 校验）。"""
    path = params.get("path", "")
    if not path:
        return "❌ path 参数不能为空"

    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(path):
        return f"❌ 目录不存在: {path}"

    try:
        # Step 1: 按文件大小分组（跳过目录和 0 字节文件）
        size_groups: dict[int, list[str]] = defaultdict(list)
        total_scanned = 0

        for root, dirs, files in os.walk(path):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if fname.startswith("."):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    size = os.path.getsize(fpath)
                    if size > 0:
                        size_groups[size].append(fpath)
                        total_scanned += 1
                except OSError:
                    continue

        # Step 2: 对每组同尺寸文件进行 MD5 校验
        duplicates: list[list[str]] = []
        total_dup_size = 0

        for size, files_list in size_groups.items():
            if len(files_list) < 2:
                continue

            # 按 MD5 分组
            md5_groups: dict[str, list[str]] = defaultdict(list)
            for fpath in files_list:
                try:
                    md5 = _md5_file(fpath)
                    md5_groups[md5].append(fpath)
                except Exception:
                    continue

            # 找出真正的重复
            for md5, dup_list in md5_groups.items():
                if len(dup_list) > 1:
                    duplicates.append(dup_list)
                    total_dup_size += size * (len(dup_list) - 1)

        if not duplicates:
            return (
                f"✅ 扫描完成，未发现重复文件\n"
                f"   扫描路径: {path}\n"
                f"   扫描文件: {total_scanned}"
            )

        # 格式化输出
        lines = [
            f"✅ 发现 {len(duplicates)} 组重复文件",
            f"   扫描路径: {path}",
            f"   扫描文件: {total_scanned}",
            f"   可节省空间: {_format_size(total_dup_size)}",
            "",
        ]

        for idx, group in enumerate(duplicates, 1):
            size = os.path.getsize(group[0])
            lines.append(f"   ── 重复组 #{idx} ({_format_size(size)}) ──")
            for i, fpath in enumerate(group, 1):
                lines.append(f"      {i}. {fpath}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 查找重复文件异常: {e}"


def _md5_file(fpath: str) -> str:
    """计算文件的 MD5 哈希值。"""
    h = hashlib.md5()
    with open(fpath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _format_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读形式。"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


# ── 图片转换 ──────────────────────────────────────────────

def cmd_convert_image(params: dict) -> str:
    """使用 sips 转换图片格式。"""
    path = params.get("path", "")
    format = params.get("format", "jpg")
    quality = int(params.get("quality", 80))
    resize = params.get("resize")

    if not path:
        return "❌ path 参数不能为空"

    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(path):
        return f"❌ 文件不存在: {path}"

    format = format.strip().lower()
    if format not in ("jpg", "jpeg", "png", "webp", "gif", "tiff", "bmp"):
        return f"❌ 不支持的输出格式: {format}，支持: jpg, png, webp, gif, tiff, bmp"

    # 标准化 jpeg -> jpg
    if format == "jpeg":
        format = "jpg"

    quality = max(1, min(quality, 100))

    # 解析 resize 参数
    resize_args: list[str] = []
    if resize:
        resize = resize.strip()
        # 支持格式: "50%", "800x600", "800x600>", "800x600<"
        if resize.endswith("%"):
            # 百分比缩放
            pct = resize.rstrip("%")
            try:
                float(pct)
            except ValueError:
                return f"❌ 无效的 resize 百分比: {resize}"
            resize_args = ["-Z", pct]  # sips -Z 按百分比缩放
        elif "x" in resize or "X" in resize:
            # 宽x高格式，去掉可选的后缀 > <
            dim = re.sub(r"[<>]$", "", resize).strip()
            parts = dim.split("x")
            if len(parts) == 2:
                try:
                    w = int(parts[0])
                    h = int(parts[1])
                except ValueError:
                    return f"❌ 无效的 resize 尺寸: {resize}"
                resize_args = ["-Z", str(max(w, h))]  # sips -Z 保持比例缩放至最长边
            else:
                return f"❌ 无效的 resize 尺寸: {resize}"
        else:
            return f"❌ 无效的 resize 参数: {resize}，使用格式: 50%, 800x600"

    # 构建输出路径
    base, _ = os.path.splitext(path)
    output = f"{base}.{format}"

    try:
        # Step 1: sips 转换格式（sips 原生支持 jpg/png/tiff/bmp/gif）
        # sips 不支持 webp，需要额外处理
        supported_by_sips = {"jpg", "jpeg", "png", "gif", "tiff", "bmp"}

        if format in supported_by_sips:
            cmd = ["sips", "-s", "format", format]
            if quality > 0 and format in ("jpg", "jpeg"):
                cmd.extend(["-s", "formatOptions", str(quality)])
            if resize_args:
                cmd.extend(resize_args)
            cmd.extend([path, "--out", output])

            r = _run_cmd(cmd, timeout=120)
            if r.returncode != 0:
                err = r.stderr.strip() or "sips 转换失败"
                return f"❌ 图片转换失败: {err}"

        elif format == "webp":
            # sips 不支持 webp，尝试使用 cwebp 或 Pillow
            # 先用 sips 转成 png 临时文件，再用 cwebp 转 webp
            temp_png = os.path.join(
                tempfile.gettempdir(),
                f"_sips_tmp_{os.getpid()}.png",
            )
            try:
                # sips 转 png
                cmd = ["sips", "-s", "format", "png"]
                if resize_args:
                    cmd.extend(resize_args)
                cmd.extend([path, "--out", temp_png])
                r1 = _run_cmd(cmd, timeout=60)
                if r1.returncode != 0:
                    err = r1.stderr.strip() or "sips 转 PNG 失败"
                    return f"❌ 图片转换失败 (sips→PNG): {err}"

                # cwebp 转 webp
                cwebp_quality = str(quality)
                r2 = _run_cmd(
                    ["cwebp", "-q", cwebp_quality, temp_png, "-o", output],
                    timeout=60,
                )
                if r2.returncode != 0:
                    err = r2.stderr.strip() or "cwebp 转换失败"
                    # 回退：尝试使用 Python Pillow
                    return _convert_with_pillow(temp_png, output, format, quality, resize)

            finally:
                if os.path.exists(temp_png):
                    try:
                        os.remove(temp_png)
                    except OSError:
                        pass
        else:
            return f"❌ 不支持的格式: {format}"

        # 验证输出文件
        if not os.path.isfile(output):
            return f"❌ 转换后文件未生成: {output}"

        out_size = _format_size(os.path.getsize(output))
        in_size = _format_size(os.path.getsize(path))

        lines = [
            f"✅ 图片转换完成",
            f"   源文件:  {path} ({in_size})",
            f"   输出:    {output} ({out_size})",
            f"   格式:    {format}",
            f"   质量:    {quality}",
        ]
        if resize_args:
            lines.append(f"   缩放:    {resize}")
        return "\n".join(lines)

    except subprocess.TimeoutExpired:
        return "❌ 图片转换超时（120秒）"
    except FileNotFoundError:
        return "❌ 未找到 sips 命令（需 macOS）"
    except Exception as e:
        return f"❌ 图片转换异常: {e}"


def _convert_with_pillow(src: str, output: str, fmt: str, quality: int, resize: str | None) -> str:
    """使用 Pillow 作为回退方案转换图片。"""
    try:
        from PIL import Image

        img = Image.open(src)
        if resize:
            if resize.endswith("%"):
                pct = float(resize.rstrip("%")) / 100
                w = int(img.width * pct)
                h = int(img.height * pct)
                img = img.resize((w, h), Image.LANCZOS)
            elif "x" in resize:
                dim = re.sub(r"[<>]$", "", resize).strip()
                parts = dim.split("x")
                w = int(parts[0])
                h = int(parts[1])
                img.thumbnail((w, h), Image.LANCZOS)

        save_kwargs = {"format": fmt.upper()}
        if fmt.lower() in ("jpg", "jpeg", "webp"):
            save_kwargs["quality"] = quality
        if fmt.lower() == "png":
            # PNG 不支持 quality 参数
            save_kwargs.pop("quality", None)

        img.save(output, **save_kwargs)

        out_size = _format_size(os.path.getsize(output))
        return (
            f"✅ 图片转换完成 (Pillow)\n"
            f"   输出: {output} ({out_size})"
        )

    except ImportError:
        return "❌ 未安装 Pillow 库 (pip install Pillow) 且未找到 cwebp"
    except Exception as e:
        return f"❌ Pillow 转换失败: {e}"


# ── 命令注册 ─────────────────────────────────────────────

COMMANDS: dict = {
    "file_search": cmd_file_search,
    "file_grep": cmd_file_grep,
    "compress": cmd_compress,
    "extract": cmd_extract,
    "trash": cmd_trash,
    "duplicate_finder": cmd_duplicate_finder,
    "convert_image": cmd_convert_image,
}

TOOL_SCHEMAS: dict = {
    "file_search": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "directory": {"type": "string", "description": "限定搜索目录（默认全盘）"},
            "limit": {"type": "integer", "description": "返回结果数量上限（1-500，默认 20）"},
        },
        "required": ["query"],
    },
    "file_grep": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "搜索的文本模式"},
            "path": {"type": "string", "description": "搜索路径（文件或目录）"},
            "extension": {"type": "string", "description": "文件扩展名过滤（如 .py, .txt）"},
        },
        "required": ["pattern", "path"],
    },
    "compress": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要压缩的文件或目录路径"},
            "format": {
                "type": "string",
                "description": "压缩格式",
                "enum": ["zip", "tar", "tar.gz", "tar.bz2", "tgz", "tbz2"],
            },
            "output": {"type": "string", "description": "输出路径（默认自动生成）"},
        },
        "required": ["path"],
    },
    "extract": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "压缩文件路径"},
            "output": {"type": "string", "description": "解压输出目录（默认自动生成）"},
        },
        "required": ["path"],
    },
    "trash": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要移到废纸篓的文件路径（action=trash 时需要）"},
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["trash", "empty"],
            },
        },
        "required": [],
    },
    "duplicate_finder": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要扫描的目录路径"},
        },
        "required": ["path"],
    },
    "convert_image": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "源图片路径"},
            "format": {
                "type": "string",
                "description": "输出格式",
                "enum": ["jpg", "jpeg", "png", "webp", "gif", "tiff", "bmp"],
            },
            "quality": {"type": "integer", "description": "图片质量 1-100（默认 80）"},
            "resize": {"type": "string", "description": "缩放参数，如 50%, 800x600"},
        },
        "required": ["path"],
    },
}

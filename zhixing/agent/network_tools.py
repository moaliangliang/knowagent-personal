"""macOS 网络诊断工具模块

公网 IP、测速、HTTP 请求、文件下载、whois、ping、端口检测。
所有 cmd_* 函数统一返回 str（纯文本），格式：
  ✅ 成功信息
  ❌ 错误信息
"""

import json
import os
import re
import socket
import subprocess
import tempfile
import time
import urllib.parse
from datetime import datetime

import requests

# ── 公网 IP ────────────────────────────────────────────────

def cmd_my_ip(params: dict | None = None) -> str:
    """查询公网 IP 及地理位置"""
    try:
        resp = requests.get("https://api.ipify.org?format=json", timeout=15)
        resp.raise_for_status()
        ip = resp.json().get("ip", "未知")
    except requests.RequestException as e:
        return f"❌ 获取公网 IP 失败: {e}"

    try:
        geo_resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=15)
        geo_resp.raise_for_status()
        geo = geo_resp.json()

        parts = []
        if geo.get("country"):
            parts.append(geo["country"])
        if geo.get("regionName"):
            parts.append(geo["regionName"])
        if geo.get("city"):
            parts.append(geo["city"])
        location = " / ".join(parts) if parts else "未知"

        isp = geo.get("isp", "未知")
        org = geo.get("org", "未知")
        lat = geo.get("lat")
        lon = geo.get("lon")
        coord = f"{lat}, {lon}" if lat is not None and lon is not None else "未知"

        lines = [
            f"✅ 公网 IP: {ip}",
            f"   位置:  {location}",
            f"   坐标:  {coord}",
            f"   ISP:   {isp}",
            f"   组织:  {org}",
        ]
        return "\n".join(lines)
    except requests.RequestException as e:
        return f"✅ 公网 IP: {ip}\n❌ 获取地理位置失败: {e}"


# ── 网速测试 ────────────────────────────────────────────────

def cmd_speedtest(params: dict | None = None) -> str:
    """测试网络速度（优先 speedtest-cli，回退 CDN 下载测速）"""
    _ = _try_speedtest_cli()
    if _ is not None:
        return _

    return _cdn_speedtest()


def _try_speedtest_cli() -> str | None:
    """尝试使用 speedtest-cli 测速"""
    try:
        r = subprocess.run(
            ["speedtest-cli", "--simple"],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            lines = []
            for line in r.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                # 格式化数字
                parts = line.split()
                if len(parts) >= 2:
                    lines.append(f"   {parts[0].ljust(8)} {parts[1]} {parts[2] if len(parts) > 2 else ''}")
            return f"✅ 测速结果 (speedtest-cli):\n" + "\n".join(lines)
        return None
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return "❌ speedtest-cli 测速超时（120秒）"
    except Exception as e:
        return f"❌ speedtest-cli 测速失败: {e}"


def _cdn_speedtest() -> str:
    """回退方案：从 CDN 下载文件测速"""
    test_urls = [
        "https://speed.cloudflare.com/__down?bytes=10485760",  # 10 MB from Cloudflare
        "https://cdn.jsdelivr.net/npm/empty@0.0.1/empty.js",  # fallback small file
    ]
    test_size = 10 * 1024 * 1024  # 10 MB

    lines = ["speedtest-cli 未安装，使用 CDN 下载测速（10 MB）:"]

    for url in test_urls:
        try:
            start = time.time()
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()
            downloaded = 0
            for chunk in resp.iter_content(chunk_size=65536):
                downloaded += len(chunk)
                if downloaded >= test_size:
                    break
            elapsed = time.time() - start
            if elapsed <= 0:
                elapsed = 0.001
            speed_bps = downloaded * 8 / elapsed
            speed_mbps = speed_bps / 1_000_000

            lines.append(f"   ✅ 下载 {downloaded / 1024 / 1024:.1f} MB 耗时 {elapsed:.2f}s")
            lines.append(f"      速度: {speed_mbps:.2f} Mbps ({(speed_mbps / 8):.2f} MB/s)")
            lines.append(f"      来源: {url}")
            return "\n".join(lines)
        except requests.RequestException as e:
            lines.append(f"   ⚠️  {url}: {e}")
            continue

    lines.append("   ❌ 所有测速源均不可用")
    return "\n".join(lines)


# ── HTTP 请求 ──────────────────────────────────────────────

def cmd_http_request(params: dict | None = None) -> str:
    """发送 HTTP 请求并返回状态、响应头和正文预览"""
    url = (params or {}).get("url", "")
    method = (params or {}).get("method", "GET")
    headers = (params or {}).get("headers")
    body = (params or {}).get("body")

    if not url:
        return "❌ url 参数不能为空"

    method = method.upper().strip()
    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
        return f"❌ 不支持的 HTTP 方法: {method}"

    # 解析请求头
    parsed_headers = {}
    if headers:
        try:
            # 支持 JSON 字符串或 key:value 格式
            if headers.strip().startswith("{"):
                parsed_headers = json.loads(headers)
            else:
                for line in headers.strip().split("\n"):
                    line = line.strip()
                    if ":" in line:
                        k, v = line.split(":", 1)
                        parsed_headers[k.strip()] = v.strip()
        except json.JSONDecodeError as e:
            return f"❌ headers 解析失败（JSON 格式错误）: {e}"
        except Exception as e:
            return f"❌ headers 解析失败: {e}"

    try:
        start = time.time()
        kwargs = {
            "url": url,
            "headers": parsed_headers,
            "timeout": 60,
        }
        if method in ("POST", "PUT", "PATCH") and body:
            # 尝试 JSON 解析，失败则作为纯文本
            try:
                kwargs["json"] = json.loads(body)
            except (json.JSONDecodeError, TypeError):
                kwargs["data"] = body

        resp = requests.request(method, **kwargs)
        elapsed = time.time() - start

        # 状态行
        lines = [
            f"✅ HTTP {method} {url}",
            f"   状态码: {resp.status_code} {resp.reason}",
            f"   耗时:   {elapsed:.3f}s",
            f"   大小:   {len(resp.content):,} bytes",
        ]

        # 响应头（前 20 行）
        lines.append(f"   响应头 ({len(resp.headers)} 个):")
        for i, (k, v) in enumerate(resp.headers.items()):
            if i >= 20:
                lines.append(f"       ... 还有 {len(resp.headers) - 20} 个头")
                break
            lines.append(f"       {k}: {v[:120]}{'...' if len(v) > 120 else ''}")

        # 正文预览
        body_preview = resp.text[:1000]
        if body_preview:
            lines.append(f"   正文预览 ({len(resp.text):,} chars, 显示前 1000):")
            for line in body_preview.split("\n")[:15]:
                truncated = line[:200]
                lines.append(f"       {truncated}")
                if len(line) > 200:
                    lines[-1] += "..."

        return "\n".join(lines)

    except requests.RequestException as e:
        return f"❌ HTTP 请求失败: {e}"
    except Exception as e:
        return f"❌ 请求异常: {e}"


# ── 文件下载 ───────────────────────────────────────────────

def cmd_download(params: dict | None = None) -> str:
    """下载文件并显示进度"""
    url = (params or {}).get("url", "")
    path = (params or {}).get("path")

    if not url:
        return "❌ url 参数不能为空"

    # 确定保存路径
    if not path:
        basename = url.split("/")[-1].split("?")[0] or "download"
        path = os.path.join(tempfile.gettempdir(), basename)

    path = os.path.abspath(os.path.expanduser(path))
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    try:
        start = time.time()
        resp = requests.get(url, timeout=300, stream=True)
        resp.raise_for_status()

        # 获取文件大小
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        last_logged_pct = -1
        chunks = []

        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                chunks.append(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = int(downloaded * 100 / total)
                    if pct >= last_logged_pct + 10:
                        last_logged_pct = pct

        with open(path, "wb") as f:
            for chunk in chunks:
                f.write(chunk)
            f.flush()

        elapsed = time.time() - start
        size_mb = downloaded / 1024 / 1024
        speed_mbps = (downloaded * 8 / elapsed) / 1_000_000 if elapsed > 0 else 0

        lines = [
            f"✅ 下载完成",
            f"   来源: {url}",
            f"   保存: {path}",
            f"   大小: {size_mb:.2f} MB",
            f"   耗时: {elapsed:.2f}s",
            f"   速度: {speed_mbps:.2f} Mbps",
        ]
        return "\n".join(lines)

    except requests.RequestException as e:
        return f"❌ 下载失败: {e}"
    except OSError as e:
        return f"❌ 写入文件失败: {e}"
    except Exception as e:
        return f"❌ 下载异常: {e}"


# ── Whois ──────────────────────────────────────────────────

def cmd_whois(params: dict | None = None) -> str:
    """查询域名 whois 信息（macOS whois 命令）"""
    domain = (params or {}).get("domain", "")
    if not domain:
        return "❌ domain 参数不能为空"

    try:
        r = subprocess.run(
            ["whois", domain],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0 and not r.stdout.strip():
            err = r.stderr.strip() or "whois 无输出"
            return f"❌ whois 查询失败: {err}"

        raw = r.stdout
        lines = raw.split("\n")

        # 过滤掉注释行和空行，取前 30 行有效内容
        important = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("%") or stripped.startswith("#"):
                continue
            # 只保留 key: value 形式的行
            if ":" in stripped:
                important.append(stripped)

        summary_lines = important[:30]
        total = len(important)

        lines_out = [
            f"✅ Whois 查询: {domain}",
            f"   总有效行数: {total}",
        ]
        for line in summary_lines:
            lines_out.append(f"   {line}")

        if total > 30:
            lines_out.append(f"   ... 还有 {total - 30} 行被截断")

        return "\n".join(lines_out)

    except FileNotFoundError:
        return "❌ 未找到 whois 命令（macOS 自带，请确认系统完整性）"
    except subprocess.TimeoutExpired:
        return "❌ whois 查询超时（30秒）"
    except Exception as e:
        return f"❌ whois 查询异常: {e}"


# ── Ping ───────────────────────────────────────────────────

def cmd_ping(params: dict | None = None) -> str:
    """Ping 目标主机并解析统计结果"""
    host = (params or {}).get("host", "")
    count = int((params or {}).get("count", 4))
    if not host:
        return "❌ host 参数不能为空"

    count = max(1, min(count, 100))
    lines = [f"📡 Ping {host} ({count} 次)..."]

    try:
        r = subprocess.run(
            ["ping", "-c", str(count), host],
            capture_output=True, text=True, timeout=(count * 5 + 10),
        )

        stdout = r.stdout
        stderr = r.stderr

        # 解析丢包率
        loss = "?"
        loss_match = re.search(r"(\d+\.?\d*)% packet loss", stdout)
        if loss_match:
            loss = loss_match.group(1)

        # 解析往返时间统计
        rtt = "?"
        rtt_match = re.search(r"min/avg/max/(?:stddev|mdev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", stdout)
        if rtt_match:
            rtt = f"min={rtt_match.group(1)}ms  avg={rtt_match.group(2)}ms  max={rtt_match.group(3)}ms  mdev={rtt_match.group(4)}ms"

        # 如果上面没匹配到，试试别的格式
        if rtt == "?":
            rtt_match = re.search(r"round-trip\s+min/avg/max\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)\s*ms", stdout)
            if rtt_match:
                rtt = f"min={rtt_match.group(1)}ms  avg={rtt_match.group(2)}ms  max={rtt_match.group(3)}ms"

        # 提取各次 ping 延迟
        times = []
        for m in re.finditer(r"time=(\d+\.?\d*)\s*ms", stdout):
            times.append(float(m.group(1)))

        if times:
            time_details = ", ".join(f"{t:.1f}ms" for t in times)
            lines.append(f"   各次延迟: {time_details}")
        lines.append(f"   丢包率:   {loss}%")
        lines.append(f"   统计:     {rtt}")

        if r.returncode != 0:
            if stderr:
                lines.append(f"   ⚠️  {stderr.strip()}")
            if loss == "100":
                return f"❌ Ping {host} 全部丢包\n" + "\n".join(lines[1:])

        return "✅ " + "\n".join(lines[1:]) if r.returncode == 0 else "⚠️ " + "\n".join(lines[1:])

    except FileNotFoundError:
        return "❌ 未找到 ping 命令"
    except subprocess.TimeoutExpired:
        return f"❌ Ping {host} 超时（超过 {count * 5 + 10} 秒）"
    except Exception as e:
        return f"❌ Ping 异常: {e}"


# ── 端口检测 ───────────────────────────────────────────────

def cmd_port_check(params: dict | None = None) -> str:
    """检测远程主机端口是否开放"""
    host = (params or {}).get("host", "")
    port = int((params or {}).get("port", 0))
    if not host:
        return "❌ host 参数不能为空"
    if port < 1 or port > 65535:
        return "❌ port 须为 1-65535 的整数"

    # 常见端口服务映射
    common_ports = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
        53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
        443: "HTTPS", 465: "SMTPS", 587: "SMTP Submission",
        993: "IMAPS", 995: "POP3S", 1433: "MSSQL",
        1521: "Oracle DB", 3306: "MySQL", 3389: "RDP",
        5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt",
        8443: "HTTPS-Alt", 27017: "MongoDB",
    }
    service = common_ports.get(port, "")

    try:
        # DNS 解析
        start = time.time()
        try:
            addr = socket.getaddrinfo(host, port)
            ip = addr[0][4][0]
        except socket.gaierror:
            return f"❌ 无法解析主机名: {host}"

        # TCP 连接测试
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((ip, port))
        sock.close()

        elapsed_ms = int((time.time() - start) * 1000)

        service_label = f" ({service})" if service else ""

        if result == 0:
            return (
                f"✅ 端口 {port}{service_label} 开放\n"
                f"   目标:  {host} ({ip})\n"
                f"   耗时:  {elapsed_ms}ms"
            )
        else:
            return (
                f"❌ 端口 {port}{service_label} 关闭\n"
                f"   目标:  {host} ({ip})\n"
                f"   耗时:  {elapsed_ms}ms\n"
                f"   (connect 返回码: {result})"
            )

    except socket.timeout:
        return f"❌ 端口 {port} 连接超时（10秒）\n   目标: {host}"
    except Exception as e:
        return f"❌ 端口检测异常: {e}"


# ── 新闻搜索 ────────────────────────────────────────────────

_NEWS_CACHE: dict = {}
_NEWS_CACHE_TIME = 0


def cmd_news(params: dict | None = None) -> str:
    """📰 搜索最新新闻资讯。

    支持中英文关键词搜索，返回标题、来源、摘要。
    可在配置中设置 news.api_key（NewsAPI）以获得更全面的结果。

    参数:
        keyword (str, optional): 搜索关键词。不传则返回综合新闻。
        limit (int, optional): 返回条数，默认 5，最大 10。
        source (str, optional): 来源，bing(默认) / baidu / newsapi。
            bing 无需 API Key；newsapi 需设置 news.api_key。
    """
    keyword = params.get("keyword", "") if params else ""
    limit = min(int(params.get("limit", 5)) if params and params.get("limit") else 5, 10)
    source = params.get("source", "bing") if params else "bing"

    # 中文搜索结果标题
    title = f"📰 新闻{'搜索: ' + keyword if keyword else '综合'}"

    # 策略 1: NewsAPI（需要 API Key，质量最高）
    if source == "newsapi":
        from zhixing.config import Config
        api_key = Config().get("news.api_key", "")
        if api_key:
            result = _fetch_newsapi(keyword, api_key, limit)
            if result:
                return title + "\n" + result

    # 策略 2: Bing News（无需 API Key，适用于中英文）
    # 注意：Bing 可能返回不准确的单条 OG 标题，需要至少 2 条才算成功
    if source in ("bing", "newsapi"):
        result = _fetch_bing_news(keyword, limit)
        # 只有返回 >= 2 条才算有效（避免单条 OG 元数据标题误导）
        if result and result.count("\n") >= 1:
            return title + "\n" + result

    # 策略 3: 百度新闻（中国用户，无需 API Key）
    if source in ("baidu", "bing", "newsapi"):
        result = _fetch_baidu_news(keyword, limit)
        if result:
            return title + "\n" + result

    # 全部失败 — 回退到百度热搜（无 keyword 时已成功，此处给提示兜底）
    if keyword and source == "bing":
        # 尝试用热搜结果作为兜底
        fallback = _fetch_baidu_news("", limit)
        if fallback:
            return (
                f"{title}\n⚠️ 未能获取「{keyword}」的专门搜索结果（网络限制），\n"
                f"以下为当前热门新闻：\n" + fallback
            )
    return (
        f"{title}\n❌ 无法获取新闻（网络不可用或新闻源被屏蔽）\n"
        f"可尝试:\n"
        f"  • 不指定关键词查看热搜: 新闻\n"
        f"  • 配置 NewsAPI Key: 在 ~/.zhixing/config.yaml 设置 news.api_key\n"
        f"  • 连接 VPN 后重试\n"
        f"  • 使用 http_request 命令手动抓取"
    )


def _fetch_bing_news(keyword: str, limit: int) -> str | None:
    """从 Bing News 搜索新闻。"""
    try:
        query = urllib.parse.quote(keyword) if keyword else ""
        url = f"https://www.bing.com/news/search?q={query}&mkt=zh-CN"
        if not keyword:
            url = "https://www.bing.com/news?mkt=zh-CN"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()

        lines = []
        seen = set()
        html = resp.text

        # 多模式提取标题（按优先级）
        patterns = [
            (r'aria-label="([^"]{10,})"', None),    # 新闻卡片标签
            (r'data-title="([^"]+)"', None),          # 数据标题属性
            (r'<a[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</a>', None),  # 标题链接
        ]

        for pat, _ in patterns:
            for m in re.findall(pat, html):
                title = re.sub(r"<[^>]+>", "", str(m)).strip()
                if title and title not in seen and len(title) > 5 and len(title) < 120:
                    seen.add(title)
                    lines.append(f"  • {title}")
                    if len(lines) >= limit:
                        break
            if len(lines) >= limit:
                break

        return "\n".join(lines[:limit]) if lines else None
    except Exception:
        return None


def _parse_bing_json(html: str, limit: int) -> str | None:
    """从 Bing News HTML 中提取 JSON 数据。"""
    import re as _re
    lines = []
    # 尝试匹配 data-card 或类似的结构
    cards = _re.findall(r'data-card="(.*?)"', html)
    if cards:
        import html as _html
        for card in cards[:limit]:
            text = _html.unescape(card)
            lines.append(f"  • {text[:100]}")
    return "\n".join(lines) if lines else None


def _fetch_baidu_news(keyword: str, limit: int) -> str | None:
    """从百度/搜狗搜索新闻。"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if not keyword:
            # 百度热搜榜
            resp = requests.get(
                "https://top.baidu.com/board?tab=realtime",
                headers=headers, timeout=10,
            )
            titles = re.findall(r'"word":"([^"]+)"', resp.text)
            if titles:
                lines = [f"  {i+1}. {t}" for i, t in enumerate(titles[:limit])]
                return "🔥 百度热搜:\n" + "\n".join(lines)
        else:
            # 搜狗新闻搜索（中国用户，无需 API Key）
            query = urllib.parse.quote(keyword)
            resp = requests.get(
                f"https://news.sogou.com/news?query={query}&sort=1",
                headers=headers, timeout=10,
            )
            titles = re.findall(r'<h3[^>]*>.*?<a[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            if titles:
                lines = []
                seen = set()
                for t in titles:
                    clean = re.sub(r'<[^>]+>', '', t).strip()
                    if clean and clean not in seen and len(clean) > 5:
                        seen.add(clean)
                        lines.append(f"  • {clean}")
                        if len(lines) >= limit:
                            break
                if lines:
                    src = f"🔍 搜狗新闻搜索: {keyword}"
                    return src + "\n" + "\n".join(lines)
        return None
    except Exception:
        return None


def _fetch_newsapi(keyword: str, api_key: str, limit: int) -> str | None:
    """从 NewsAPI 获取新闻（需 API Key）。"""
    try:
        if keyword:
            url = f"https://newsapi.org/v2/everything?q={urllib.parse.quote(keyword)}&pageSize={limit}&language=zh&sortBy=publishedAt"
        else:
            url = f"https://newsapi.org/v2/top-headlines?country=cn&pageSize={limit}"
        resp = requests.get(url, headers={"X-Api-Key": api_key}, timeout=10)
        data = resp.json()
        if data.get("status") != "ok":
            return None
        articles = data.get("articles", [])
        if not articles:
            return None
        lines = []
        for a in articles[:limit]:
            title_text = a.get("title", "")
            source_name = a.get("source", {}).get("name", "")
            desc = a.get("description", "")
            line = f"  • {title_text}"
            if source_name:
                line += f"\n    [{source_name}]"
            if desc and len(desc) < 100:
                line += f" {desc}"
            lines.append(line)
        return "\n".join(lines)
    except Exception:
        return None

COMMANDS: dict = {
    "my_ip": cmd_my_ip,
    "speedtest": cmd_speedtest,
    "http_request": cmd_http_request,
    "download": cmd_download,
    "whois": cmd_whois,
    "ping": cmd_ping,
    "port_check": cmd_port_check,
    "news": cmd_news,
}

TOOL_SCHEMAS: dict = {
    "my_ip": {
        "type": "object",
        "properties": {},
    },
    "speedtest": {
        "type": "object",
        "properties": {},
    },
    "news": {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "搜索关键词。不传返回综合新闻"},
            "limit": {"type": "integer", "description": "返回条数（1-10，默认 5）"},
            "source": {"type": "string", "enum": ["bing", "baidu", "newsapi"], "description": "新闻源: bing(默认), baidu, newsapi（需配置 API Key）"},
        },
    },
    "http_request": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "请求 URL"},
            "method": {"type": "string", "description": "HTTP 方法 (GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS)", "default": "GET"},
            "headers": {"type": "string", "description": "请求头（JSON 或 key:value 格式）"},
            "body": {"type": "string", "description": "请求体（自动尝试 JSON 解析）"},
        },
        "required": ["url"],
    },
    "download": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "下载 URL"},
            "path": {"type": "string", "description": "保存路径（默认 /tmp/<filename>）"},
        },
        "required": ["url"],
    },
    "whois": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "域名"},
        },
        "required": ["domain"],
    },
    "ping": {
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "目标主机（域名或 IP）"},
            "count": {"type": "integer", "description": "Ping 次数（1-100，默认 4）", "default": 4},
        },
        "required": ["host"],
    },
    "port_check": {
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "目标主机（域名或 IP）"},
            "port": {"type": "integer", "description": "端口号（1-65535）"},
        },
        "required": ["host", "port"],
    },
}

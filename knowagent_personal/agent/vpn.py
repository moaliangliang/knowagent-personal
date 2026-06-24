"""VPN 工具 — 深信服 aTrust + FortiGate VPN 管理与代理配置

提供 VPN 连通性检测、代理开关、浏览器登录、openfortivpn 隧道连接等能力。
"""

import os
import re
import signal
import socket
import ssl
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Literal

import requests

# 默认配置
VPN_CONFIG_DIR = os.path.expanduser("~/.knowagent/vpn")
FORTI_CONFIG_FILE = os.path.join(VPN_CONFIG_DIR, "forti_config")
OPENSSL_CONFIG_FILE = os.path.join(VPN_CONFIG_DIR, "openssl_weak.cnf")


@dataclass
class VpnStatus:
    """VPN 状态数据类"""
    # 连接目标
    vpn_type: str = "atrust"          # "atrust" | "fortinet"
    host: str = ""
    port: int = 443
    # 连通性
    reachable: bool = False
    dns_ok: bool = False
    dns_ip: str = ""
    tls_ok: bool = False
    tls_subject: str = ""
    tls_expiry: str = ""
    tls_issuer: str = ""
    http_ok: bool = False
    server_type: str = ""
    response_time_ms: int = 0
    # 代理
    proxy_enabled: bool = False
    proxy_http: str = ""
    proxy_https: str = ""
    proxy_socks: str = ""
    proxy_no_proxy: str = ""
    # Fortinet 隧道
    fortinet_installed: bool = False
    fortinet_running: bool = False
    fortinet_pid: int = 0
    tunnel_interface: str = ""

    def to_text(self) -> str:
        """格式化为可读文本"""
        lines = [
            "📋 VPN 状态报告",
            f"   类型:   {'深信服 aTrust' if self.vpn_type == 'atrust' else 'FortiGate (openfortivpn)'}",
            f"   服务器: {self.host}:{self.port}",
        ]
        # DNS
        if self.dns_ok:
            lines.append(f"  📡 DNS:    ✅ {self.dns_ip} ({self.response_time_ms}ms)")
        else:
            lines.append(f"  📡 DNS:    ❌ 解析失败")
        # 网络
        if self.reachable:
            lines.append(f"  🌐 网络:   ✅ 可达")
        else:
            lines.append(f"  🌐 网络:   ❌ 不可达")
        # TLS
        if self.tls_ok:
            lines.append(f"  🔒 TLS:    ✅ 证书有效")
            lines.append(f"     归属:   {self.tls_subject}")
            lines.append(f"     签发:   {self.tls_issuer}")
            lines.append(f"     有效期: {self.tls_expiry}")
        else:
            lines.append(f"  🔒 TLS:    ❌ 证书异常")
        # HTTP
        if self.http_ok:
            lines.append(f"  🖥 HTTP:   ✅ {self.server_type} 服务正常")
        else:
            lines.append(f"  🖥 HTTP:   ❌ 服务不可用")
        # Fortinet 隧道
        if self.vpn_type == "fortinet":
            if not self.fortinet_installed:
                lines.append("  🚇 隧道:   ❌ openfortivpn 未安装")
                lines.append("   安装: brew install openfortivpn")
            elif self.fortinet_running:
                lines.append(f"  🚇 隧道:   ✅ 已连接 (PID {self.fortinet_pid})")
                if self.tunnel_interface:
                    lines.append(f"     接口:   {self.tunnel_interface}")
            else:
                lines.append("  🚇 隧道:   🔴 未连接")
        # 代理
        status_icon = "🟢 已启用" if self.proxy_enabled else "🔴 已禁用"
        lines.append(f"  🔌 代理:   {status_icon}")
        if self.proxy_enabled:
            if self.proxy_http:
                lines.append(f"     HTTP:   {self.proxy_http}")
            if self.proxy_https:
                lines.append(f"     HTTPS:  {self.proxy_https}")
            if self.proxy_socks:
                lines.append(f"     SOCKS:  {self.proxy_socks}")
            if self.proxy_no_proxy:
                lines.append(f"     忽略:   {self.proxy_no_proxy}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "vpn_type": self.vpn_type,
            "host": self.host,
            "port": self.port,
            "reachable": self.reachable,
            "dns_ok": self.dns_ok,
            "dns_ip": self.dns_ip,
            "tls_ok": self.tls_ok,
            "http_ok": self.http_ok,
            "server_type": self.server_type,
            "response_time_ms": self.response_time_ms,
            "proxy_enabled": self.proxy_enabled,
            "fortinet_running": self.fortinet_running,
        }


# ═══════════════════════════════════════════════════════════════
#  VpnClient
# ═══════════════════════════════════════════════════════════════

class VpnClient:
    """VPN 客户端 — aTrust 代理管理 + FortiGate 隧道连接"""

    def __init__(self, config=None):
        from knowagent_personal.config import Config
        self._config = config or Config()

    # ── VPN 类型 ────────────────────────────────────────────

    @property
    def vpn_type(self) -> Literal["atrust", "fortinet"]:
        return self._config.get("proxy.vpn_type", "atrust")

    @property
    def host(self) -> str:
        if self.vpn_type == "fortinet":
            return self._config.get("proxy.fortinet.host", "60.190.246.42")
        return self._config.get("proxy.vpn_host", "vpn.sgssemi.com")

    @property
    def port(self) -> int:
        if self.vpn_type == "fortinet":
            return int(self._config.get("proxy.fortinet.port", 10443))
        return int(self._config.get("proxy.vpn_port", 443))

    # ── 代理管理 ────────────────────────────────────────────

    def is_proxy_enabled(self) -> bool:
        return bool(self._config.get("proxy.enabled", False))

    def enable_proxy(self) -> str:
        """启用代理"""
        self._config.set("proxy.enabled", True)
        self._config.save()
        http = self._config.get("proxy.http", "未设置")
        https = self._config.get("proxy.https", "未设置")
        return f"✅ 代理已启用\n   HTTP: {http}\n   HTTPS: {https}"

    def disable_proxy(self) -> str:
        """禁用代理"""
        self._config.set("proxy.enabled", False)
        self._config.save()
        return "✅ 代理已禁用"

    # ── 连通性检测（通用）───────────────────────────────────

    def check_connectivity(self) -> VpnStatus:
        """检测 VPN 服务器连通性"""
        status = VpnStatus(vpn_type=self.vpn_type, host=self.host, port=self.port)

        # DNS 解析
        try:
            start = time.time()
            info = socket.getaddrinfo(self.host, self.port)
            elapsed = int((time.time() - start) * 1000)
            status.dns_ok = True
            status.dns_ip = info[0][4][0]
            status.response_time_ms = elapsed
            status.reachable = True
        except socket.gaierror:
            status.dns_ok = False
            status.reachable = False
            return status

        # TLS 证书检查
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((self.host, self.port), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=self.host) as ssock:
                    cert = ssock.getpeercert()
                    if cert:
                        status.tls_ok = True
                        # 主题
                        subject_parts = []
                        for part in cert.get("subject", []):
                            for key, val in part:
                                subject_parts.append(val)
                        status.tls_subject = " / ".join(subject_parts) if subject_parts else ""
                        # 签发者
                        issuer_parts = []
                        for part in cert.get("issuer", []):
                            for key, val in part:
                                issuer_parts.append(val)
                        status.tls_issuer = " / ".join(issuer_parts)
                        # 有效期
                        from datetime import datetime
                        not_before = cert.get("notBefore", "")
                        not_after = cert.get("notAfter", "")
                        if not_before:
                            try:
                                d = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")
                                not_before = d.strftime("%Y-%m-%d")
                            except ValueError:
                                pass
                        if not_after:
                            try:
                                d = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                                not_after = d.strftime("%Y-%m-%d")
                            except ValueError:
                                pass
                        status.tls_expiry = f"{not_before} ~ {not_after}" if not_before and not_after else ""
        except Exception:
            status.tls_ok = False

        # HTTP 检测（仅 aTrust 需要）
        if self.vpn_type == "atrust":
            try:
                resp = requests.get(
                    f"https://{self.host}:{self.port}/",
                    timeout=10,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    },
                )
                if resp.status_code == 200:
                    status.http_ok = True
                    server_h = resp.headers.get("Server", "")
                    if "Sangine" in server_h or "Sangfor" in server_h:
                        status.server_type = "深信服 aTrust 2.0 零信任接入"
                    elif server_h:
                        status.server_type = server_h
                    else:
                        status.server_type = "Web 服务"
                else:
                    status.http_ok = True
                    status.server_type = f"HTTP {resp.status_code}"
            except requests.RequestException:
                status.http_ok = False
        else:
            # Fortinet: 端口可达即认为服务正常
            if status.reachable:
                status.http_ok = True
                status.server_type = "FortiGate VPN (openfortivpn)"

        # 代理状态
        status.proxy_enabled = self.is_proxy_enabled()
        if status.proxy_enabled:
            status.proxy_http = self._config.get("proxy.http", "")
            status.proxy_https = self._config.get("proxy.https", "")
            status.proxy_socks = self._config.get("proxy.socks", "")
            status.proxy_no_proxy = self._config.get("proxy.no_proxy", "")

        # Fortinet 隧道状态
        if self.vpn_type == "fortinet":
            self._fill_fortinet_status(status)

        return status

    # ── Fortinet 隧道管理 ───────────────────────────────────

    @staticmethod
    def _fortinet_bin() -> str:
        """查找 openfortivpn 可执行文件路径"""
        candidates = [
            "/opt/homebrew/opt/openfortivpn/bin/openfortivpn",
            "/usr/local/bin/openfortivpn",
            "/usr/bin/openfortivpn",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        # fallback: 从 PATH 查找
        try:
            result = subprocess.run(["which", "openfortivpn"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    def _fortinet_installed(self) -> bool:
        return bool(self._fortinet_bin())

    def _ensure_config_dir(self):
        """确保 VPN 配置目录存在"""
        os.makedirs(VPN_CONFIG_DIR, exist_ok=True)

    def _write_fortinet_config(self) -> str:
        """写入 openfortivpn 配置文件，返回路径"""
        self._ensure_config_dir()
        host = self._config.get("proxy.fortinet.host", "60.190.246.42")
        port = self._config.get("proxy.fortinet.port", 10443)
        username = self._config.get("proxy.fortinet.username", "")
        password = self._config.get("proxy.fortinet.password", "")
        trusted_cert = self._config.get("proxy.fortinet.trusted_cert", "")

        lines = [
            f"host = {host}",
            f"port = {port}",
            f"username = {username}",
            f"password = {password}",
            "insecure-ssl = 1",
        ]
        if trusted_cert:
            lines.append(f"trusted-cert = {trusted_cert}")

        with open(FORTI_CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return FORTI_CONFIG_FILE

    def _write_openssl_config(self) -> str:
        """写入宽松 OpenSSL 配置（兼容旧 VPN），返回路径"""
        self._ensure_config_dir()
        content = """openssl_conf = openssl_init

[openssl_init]
ssl_conf = ssl_sect

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
MinProtocol = TLSv1.2
CipherString = DEFAULT:@SECLEVEL=0
"""
        with open(OPENSSL_CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        return OPENSSL_CONFIG_FILE

    @staticmethod
    def _fill_fortinet_status(status: VpnStatus):
        """填入 Fortinet 隧道状态"""
        # 检查安装
        bin_path = VpnClient._fortinet_bin()
        status.fortinet_installed = bool(bin_path)
        if not bin_path:
            status.fortinet_running = False
            return

        # 检查进程
        try:
            r = subprocess.run(
                ["pgrep", "-f", "openfortivpn"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                pids = r.stdout.strip().split()
                status.fortinet_running = True
                status.fortinet_pid = int(pids[0])
        except Exception:
            pass

        # 检查隧道接口
        try:
            r = subprocess.run(
                ["ifconfig", "ppp0"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                status.tunnel_interface = "ppp0"
        except Exception:
            pass

        if not status.tunnel_interface:
            try:
                r = subprocess.run(
                    ["netstat", "-rn"],
                    capture_output=True, text=True, timeout=5,
                )
                for line in r.stdout.split("\n"):
                    if "ppp" in line:
                        m = re.search(r"ppp\d+", line)
                        if m:
                            status.tunnel_interface = m.group()
                            break
            except Exception:
                pass

    def fortinet_connect(self) -> str:
        """连接 Fortinet VPN（openfortivpn）"""
        if not self._fortinet_installed():
            return (
                "❌ openfortivpn 未安装\n"
                "   请执行: brew install openfortivpn"
            )

        # 检查是否已连接
        sv = VpnStatus(vpn_type="fortinet")
        self._fill_fortinet_status(sv)
        if sv.fortinet_running:
            return f"⏸ Fortinet VPN 已在运行 (PID {sv.fortinet_pid})，无需重复连接"

        # 写入配置
        self._write_fortinet_config()
        self._write_openssl_config()

        bin_path = self._fortinet_bin()
        host = self._config.get("proxy.fortinet.host", "60.190.246.42")
        port = self._config.get("proxy.fortinet.port", 10443)

        lines = [
            f"🔌 正在连接 Fortinet VPN ({host}:{port}) ...",
            "   按 Ctrl+C 断开连接",
            f"   PID 文件: {FORTI_CONFIG_FILE}",
            "",
        ]

        # 后台启动（使用 nohup 和 sudo）
        cmd = [
            "sudo",
            "env",
            f"OPENSSL_CONF={OPENSSL_CONFIG_FILE}",
            bin_path,
            "-c", FORTI_CONFIG_FILE,
        ]

        # 启动后打印日志到 stdout
        try:
            log_file = os.path.join(VPN_CONFIG_DIR, "fortinet.log")
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            # 等待几秒看是否启动成功
            time.sleep(3)
            ret = proc.poll()
            if ret is not None:
                # 立即退出了 — 有错误
                output, _ = proc.communicate(timeout=5)
                error_msg = output.strip() if output else "未知错误（请检查配置）"
                return (
                    f"❌ Fortinet VPN 连接失败 (exit {ret})\n"
                    f"   {error_msg}\n"
                    f"   日志: {log_file}"
                )

            self._fill_fortinet_status(sv)
            if sv.fortinet_running:
                lines.append(f"✅ Fortinet VPN 已连接 (PID {sv.fortinet_pid})")
            else:
                lines.append("⏳ Fortinet VPN 启动中（后台运行）...")
                lines.append(f"   日志: {log_file}")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ 启动 Fortinet VPN 失败: {e}"

    def fortinet_disconnect(self) -> str:
        """断开 Fortinet VPN"""
        sv = VpnStatus(vpn_type="fortinet")
        self._fill_fortinet_status(sv)

        if not sv.fortinet_running:
            return "⏸ Fortinet VPN 未在运行"

        try:
            # 发送 SIGTERM 给 openfortivpn 进程
            os.kill(sv.fortinet_pid, signal.SIGTERM)
            time.sleep(1)

            # 检查是否已终止
            self._fill_fortinet_status(sv)
            if sv.fortinet_running:
                # 强制终止
                subprocess.run(
                    ["sudo", "kill", "-9", str(sv.fortinet_pid)],
                    capture_output=True, timeout=5,
                )
                return f"✅ Fortinet VPN 已强制断开 (PID {sv.fortinet_pid})"
            return f"✅ Fortinet VPN 已断开 (PID {sv.fortinet_pid})"

        except ProcessLookupError:
            return "✅ Fortinet VPN 已断开"
        except Exception as e:
            return f"❌ 断开 VPN 失败: {e}"

    # ── 浏览器登录（aTrust）─────────────────────────────────

    def open_browser(self) -> str:
        """在默认浏览器中打开 VPN 登录页面"""
        url = f"https://{self.host}:{self.port}/"
        try:
            subprocess.run(["open", url], check=True, timeout=5)
            return f"✅ 已在浏览器中打开 VPN 登录页面\n   {url}"
        except subprocess.CalledProcessError as e:
            return f"❌ 打开浏览器失败: {e}"
        except FileNotFoundError:
            return '❌ "open" 命令不可用（非 macOS）'

    def open_safari(self) -> str:
        """在 Safari 中打开 VPN 登录页面"""
        url = f"https://{self.host}:{self.port}/"
        try:
            subprocess.run(["open", "-a", "Safari", url], check=True, timeout=5)
            return f"✅ 已在 Safari 中打开 VPN 登录页面\n   {url}"
        except subprocess.CalledProcessError:
            return self.open_browser()

    # ── 配置查询 ───────────────────────────────────────────

    def get_config(self) -> dict:
        """获取 VPN/代理配置详情"""
        from knowagent_personal.config import CONFIG_FILE
        cfg = {
            "vpn_type": self.vpn_type,
            "enabled": self.is_proxy_enabled(),
            "http": self._config.get("proxy.http", ""),
            "https": self._config.get("proxy.https", ""),
            "socks": self._config.get("proxy.socks", ""),
            "no_proxy": self._config.get("proxy.no_proxy", ""),
            "vpn_host": self.host,
            "vpn_port": self.port,
            "config_file": CONFIG_FILE,
        }
        if self.vpn_type == "fortinet":
            cfg["fortinet_username"] = self._config.get("proxy.fortinet.username", "")
            fortinet_host = self._config.get("proxy.fortinet.host", "")
            fortinet_port = self._config.get("proxy.fortinet.port", "")
            cfg["fortinet_server"] = f"{fortinet_host}:{fortinet_port}"
        return cfg

    # ── 一键操作 ───────────────────────────────────────────

    def quick_check(self) -> str:
        """快速检测：连通性 + VPN 状态"""
        status = self.check_connectivity()
        return status.to_text()

    def connect(self) -> str:
        """一键连接（根据 vpn_type 自动选择）"""
        if self.vpn_type == "fortinet":
            return self.fortinet_connect()

        # aTrust: 启用代理 → 检测连通 → 打开浏览器
        lines = []
        lines.append(self.enable_proxy())
        lines.append("检测 VPN 服务器连通性...")
        status = self.check_connectivity()
        if status.http_ok:
            lines.append(f"  ✅ VPN 服务器 {status.host}:{status.port} 可达")
        else:
            lines.append(f"  ❌ VPN 服务器 {status.host}:{status.port} 不可达")
            if not self.is_proxy_enabled():
                lines.append("  💡 尝试: vpn_status action=login 在浏览器中登录")
        lines.append(self.open_browser())
        return "\n".join(lines)

    def disconnect(self) -> str:
        """断开连接（根据 vpn_type 自动选择）"""
        if self.vpn_type == "fortinet":
            return self.fortinet_disconnect()
        return self.disable_proxy()

    def switch_type(self, vpn_type: str) -> str:
        """切换 VPN 类型"""
        if vpn_type not in ("atrust", "fortinet"):
            return f"❌ 不支持的类型: {vpn_type}（支持 atrust/fortinet）"
        self._config.set("proxy.vpn_type", vpn_type)
        self._config.save()
        names = {"atrust": "深信服 aTrust", "fortinet": "FortiGate (openfortivpn)"}
        return f"✅ VPN 已切换为: {names[vpn_type]}"

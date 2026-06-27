#!/usr/bin/env python3
"""
知行 (ZhiXing) License 验证服务器
部署: 可以部署到任何支持 Python 的服务器，或 GitHub Pages

快速启动:
  pip install flask
  python license_server.py

环境变量:
  LICENSE_KEYS=key1,key2,key3    # 逗号分隔的有效 License Key
  PORT=5000                       # 监听端口
"""

import json
import os
import re
import sys

try:
    from flask import Flask, request, jsonify
except ImportError:
    # 无 Flask 时用简易 HTTP Server
    HAS_FLASK = False
else:
    HAS_FLASK = True

PORT = int(os.environ.get("PORT", 5000))
VALID_KEYS = set()

# 从环境变量加载有效密钥
keys_env = os.environ.get("LICENSE_KEYS", "")
if keys_env:
    VALID_KEYS.update(k.strip() for k in keys_env.split(",") if k.strip())

# 从文件加载
KEYS_FILE = os.path.join(os.path.dirname(__file__), "valid_keys.txt")
if os.path.exists(KEYS_FILE):
    with open(KEYS_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                VALID_KEYS.add(line)

print(f"📋 已加载 {len(VALID_KEYS)} 个有效 License Key")


def validate_key_local(key: str) -> bool:
    """本地格式校验"""
    if not re.match(r'^KA-PRO-[A-Z0-9]{20}$', key):
        return False
    seg = key.split("-")[2]
    body = seg[:-1]
    checksum = sum(ord(c) for c in body) % 10
    return int(seg[-1]) == checksum


# ── Flask 模式 ─────────────────────────────────

if HAS_FLASK:
    app = Flask(__name__)

    @app.route("/verify", methods=["POST"])
    def verify():
        data = request.get_json(silent=True) or {}
        key = (data.get("key") or "").strip()

        if not key:
            return jsonify({"valid": False, "error": "missing_key"}), 400

        if not validate_key_local(key):
            return jsonify({"valid": False, "error": "invalid_format"}), 200

        if key in VALID_KEYS:
            return jsonify({"valid": True, "plan": "pro", "expires": None})
        else:
            return jsonify({"valid": False, "error": "unknown_key"}), 200

    @app.route("/status", methods=["GET"])
    def status():
        return jsonify({"online": True, "keys_count": len(VALID_KEYS)})

    print(f"🚀 License Server 运行在 http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)

# ── 简易 HTTP Server 模式 ─────────────────────

else:
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class LicenseHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                data = json.loads(body)
                key = (data.get("key") or "").strip()
            except Exception:
                key = ""

            if self.path == "/verify":
                valid = key in VALID_KEYS and validate_key_local(key)
                resp = json.dumps({"valid": valid})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(resp.encode())
            else:
                self.send_response(404)
                self.end_headers()

        def do_GET(self):
            resp = json.dumps({"online": True, "keys_count": len(VALID_KEYS)})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.encode())

    print(f"🚀 License Server 运行在 http://0.0.0.0:{PORT}")
    HTTPServer(("0.0.0.0", PORT), LicenseHandler).serve_forever()

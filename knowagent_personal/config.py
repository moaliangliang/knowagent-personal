"""Configuration management - reads ~/.knowagent/config.yaml."""

import os

try:
    import yaml as _yaml
except ImportError:
    _yaml = None

import json

CONFIG_DIR = os.path.expanduser("~/.knowagent")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.yaml")

DEFAULT_CONFIG = {
    "llm": {
        "provider": "ollama",        # "ollama" or "openai"
        "ollama_url": "http://localhost:11434",
        "model": "qwen2.5:7b",       # or "deepseek-r1:8b"
        "api_key": "",               # for OpenAI-compatible providers
        "base_url": "",              # optional API base URL override
    },
    "storage": {
        "db_path": os.path.join(CONFIG_DIR, "personal.db"),
    },
    "rag": {
        "enabled": True,
        "index_path": os.path.join(CONFIG_DIR, "chroma"),
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "index_dirs": ["~/Documents", "~/Desktop"],
    },
    "proxy": {
        "enabled": False,
        "vpn_type": "atrust",          # "atrust" 深信服 or "fortinet" FortiGate
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890",
        "socks": "",
        "no_proxy": "localhost,127.0.0.1,.local",
        "vpn_host": "vpn.sgssemi.com",
        "vpn_port": 443,
        # Fortinet VPN (openfortivpn) 配置
        # 安全提示：用户名密码请通过 ka credential 存入 macOS Keychain
        "fortinet": {
            "host": "60.190.246.42",
            "port": 10443,
            "username": "",
            "password": "",
            "trusted_cert": "d5e84c6f2b426cac1cceeebdd43797f76d4ef7f885ee814d01f8460f8bd55b24",
        },
    },
    "ui": {
        "history_file": os.path.join(CONFIG_DIR, "history"),
        "color_enabled": True,
    },
    "telemetry": {
        "enabled": False,            # 匿名使用统计（默认关闭，纯 opt-in）
    },
    "conversion": {
        "dismissed": False,          # 用户是否选择不再看到漏斗提示
        "last_prompt_version": 0,    # 上次展示的提示版本号
    },
    "harness": {
        "permission_mode": "normal",  # plan | normal | accept_edits | elevated | trusted
        "permissions_file": os.path.join(CONFIG_DIR, "permissions.json"),
        "max_retries": 2,
        "audit_log": True,
        "context_compression": True,
        "max_history_turns": 20,
    },
}


class Config:
    """Configuration manager with dot-notation access & CLI overrides."""

    def __init__(self, cli_overrides: dict | None = None):
        self._data = self._load()
        if cli_overrides:
            self._apply_cli_overrides(cli_overrides)

    def _load(self) -> dict:
        config = self._deep_copy(DEFAULT_CONFIG)
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(CONFIG_FILE):
            try:
                if _yaml:
                    with open(CONFIG_FILE, encoding="utf-8") as f:
                        loaded = _yaml.safe_load(f) or {}
                else:
                    with open(CONFIG_FILE, encoding="utf-8") as f:
                        loaded = json.load(f)
                self._deep_merge(config, loaded)
            except Exception:
                pass  # fall through to defaults
        # Ensure storage path under config dir
        if not os.path.isabs(config["storage"]["db_path"]):
            config["storage"]["db_path"] = os.path.join(
                CONFIG_DIR, config["storage"]["db_path"]
            )
        return config

    @staticmethod
    def _deep_copy(d):
        """Deep copy a dict structure."""
        import copy
        return copy.deepcopy(d)

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        """Recursively merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value

    def _apply_cli_overrides(self, overrides: dict):
        llm = self._data["llm"]
        if overrides.get("model"):
            llm["model"] = overrides["model"]
        if overrides.get("ollama_url"):
            llm["ollama_url"] = overrides["ollama_url"]
        if overrides.get("provider"):
            llm["provider"] = overrides["provider"]

    def get(self, key_path: str, default=None):
        """Dot-notation access: config.get('llm.model')"""
        parts = key_path.split(".")
        val = self._data
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
                if val is None:
                    return default
            else:
                return default
        return val

    def set(self, key_path: str, value):
        """Dot-notation setter: config.set('llm.model', 'qwen2.5:7b')"""
        parts = key_path.split(".")
        target = self._data
        for p in parts[:-1]:
            target = target.setdefault(p, {})
        target[parts[-1]] = value

    def get_proxies(self) -> dict | None:
        """Return requests-compatible proxy dict, or None if proxy disabled."""
        if not self._data.get("proxy", {}).get("enabled", False):
            return None
        p = self._data["proxy"]
        proxies = {}
        if p.get("http"):
            proxies["http"] = p["http"]
        if p.get("https"):
            proxies["https"] = p["https"]
        if p.get("socks"):
            proxies["socks5"] = p["socks"]
        return proxies or None

    def save(self):
        """Persist config to disk."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            if _yaml:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    _yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)
            else:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @property
    def raw(self) -> dict:
        return self._data

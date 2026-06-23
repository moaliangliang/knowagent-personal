"""Tests for configuration module."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from knowagent_personal.config import Config, CONFIG_DIR, DEFAULT_CONFIG


def test_default_values():
    c = Config()
    assert c.get("llm.provider") == "ollama"
    assert c.get("llm.model") == "qwen2.5:7b"
    assert c.get("rag.enabled") is True
    assert "personal.db" in c.get("storage.db_path", "")


def test_cli_overrides():
    c = Config(cli_overrides={"model": "deepseek-r1:8b", "provider": "openai"})
    assert c.get("llm.model") == "deepseek-r1:8b"
    assert c.get("llm.provider") == "openai"


def test_dot_notation():
    c = Config()
    c.set("test.nested.key", "value")
    assert c.get("test.nested.key") == "value"


def test_config_dir_created():
    assert os.path.isdir(CONFIG_DIR)
    cfg_file = os.path.join(CONFIG_DIR, "config.yaml")
    exists = os.path.exists(cfg_file)
    if exists:
        assert os.path.getsize(cfg_file) > 0

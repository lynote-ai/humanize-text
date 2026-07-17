"""Unit tests for LLM client config resolution (no network)."""

import importlib.util
from pathlib import Path

import pytest

_LLM_CLIENT_PATH = Path(__file__).parent.parent / "src" / "standard" / "llm_client.py"
_spec = importlib.util.spec_from_file_location("llm_client", _LLM_CLIENT_PATH)
_llm_client = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_llm_client)

normalize_chat_completions_url = _llm_client.normalize_chat_completions_url
resolve_llm_config = _llm_client.resolve_llm_config


def test_deepseek_defaults_backward_compat():
    config = {
        "api_keys": {"deepseek_api_key": "sk-test"},
        "pipeline": {"model": "deepseek-chat", "temperature": 1.2},
    }
    llm = resolve_llm_config(config)
    assert llm["provider"] == "deepseek"
    assert llm["base_url"] == "https://api.deepseek.com"
    assert llm["model"] == "deepseek-chat"
    assert llm["temperature"] == 1.2
    assert llm["api_key"] == "sk-test"
    assert llm["display_name"] == "DeepSeek"


def test_openrouter_provider():
    config = {
        "api_keys": {"openrouter_api_key": "sk-or-test"},
        "llm": {"provider": "openrouter"},
    }
    llm = resolve_llm_config(config)
    assert llm["provider"] == "openrouter"
    assert llm["base_url"] == "https://openrouter.ai/api/v1"
    assert llm["model"] == "deepseek/deepseek-chat"
    assert llm["api_key"] == "sk-or-test"
    assert llm["display_name"] == "OpenRouter"


def test_atlascloud_provider():
    config = {
        "api_keys": {"atlascloud_api_key": "ak-atlas-test"},
        "llm": {"provider": "atlascloud"},
    }
    llm = resolve_llm_config(config)
    assert llm["provider"] == "atlascloud"
    assert llm["base_url"] == "https://api.atlascloud.ai/v1"
    assert llm["model"] == "qwen/qwen3.5-flash"
    assert llm["api_key"] == "ak-atlas-test"
    assert llm["display_name"] == "Atlas Cloud"


def test_base_url_override():
    config = {
        "api_keys": {"openrouter_api_key": "sk-or-test"},
        "llm": {
            "provider": "openrouter",
            "base_url": "https://my-proxy.example.com/v1",
        },
    }
    llm = resolve_llm_config(config)
    assert llm["base_url"] == "https://my-proxy.example.com/v1"


def test_llm_section_takes_precedence_over_pipeline():
    config = {
        "api_keys": {"deepseek_api_key": "sk-test"},
        "llm": {"model": "custom-model", "temperature": 1.5},
        "pipeline": {"model": "deepseek-chat", "temperature": 1.1},
    }
    llm = resolve_llm_config(config)
    assert llm["model"] == "custom-model"
    assert llm["temperature"] == 1.5


def test_env_overrides(monkeypatch):
    config = {
        "api_keys": {"openrouter_api_key": "toml-key"},
        "llm": {"provider": "openrouter"},
    }
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_BASE_URL", "https://env-proxy.example.com/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
    monkeypatch.setenv("LLM_MODEL", "anthropic/claude-3.5-sonnet")

    llm = resolve_llm_config(config)
    assert llm["base_url"] == "https://env-proxy.example.com/v1"
    assert llm["api_key"] == "env-key"
    assert llm["model"] == "anthropic/claude-3.5-sonnet"


def test_llm_api_key_env_overrides_provider_key(monkeypatch):
    config = {
        "api_keys": {"deepseek_api_key": "toml-key"},
    }
    monkeypatch.setenv("LLM_API_KEY", "generic-override")
    llm = resolve_llm_config(config)
    assert llm["api_key"] == "generic-override"


def test_atlascloud_env_key(monkeypatch):
    config = {
        "api_keys": {},
        "llm": {"provider": "atlascloud"},
    }
    monkeypatch.setenv("ATLASCLOUD_API_KEY", "env-atlas-key")
    llm = resolve_llm_config(config)
    assert llm["api_key"] == "env-atlas-key"


def test_missing_api_key_raises():
    with pytest.raises(ValueError, match="Missing API key"):
        resolve_llm_config({"api_keys": {}})


def test_unsupported_provider_raises():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        resolve_llm_config({
            "api_keys": {"deepseek_api_key": "sk-test"},
            "llm": {"provider": "unknown"},
        })


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("https://openrouter.ai/api/v1", "https://openrouter.ai/api/v1/chat/completions"),
        ("https://api.deepseek.com/", "https://api.deepseek.com/chat/completions"),
        (
            "https://api.example.com/v1/chat/completions",
            "https://api.example.com/v1/chat/completions",
        ),
    ],
)
def test_normalize_chat_completions_url(base_url, expected):
    assert normalize_chat_completions_url(base_url) == expected


def test_openrouter_extra_headers():
    config = {
        "api_keys": {"openrouter_api_key": "sk-or-test"},
        "llm": {
            "provider": "openrouter",
            "http_referer": "https://example.com",
            "app_title": "Humanize Text",
        },
    }
    llm = resolve_llm_config(config)
    assert llm["extra_headers"] == {
        "HTTP-Referer": "https://example.com",
        "X-Title": "Humanize Text",
    }

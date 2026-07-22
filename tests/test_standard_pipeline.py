"""Tests for Standard Pipeline Step 4 provider switching.

All external calls are mocked; no API keys or network access needed.
"""

from typing import Any

import pytest

import src.standard.pipeline as pipeline_module
from src.standard.pipeline import run_standard_pipeline


@pytest.fixture
def base_config() -> dict[str, Any]:
    return {
        "api_keys": {
            "deepseek_api_key": "sk-secret",
            "niutrans_api_key": "secret-niutrans",
        },
        "llm": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "temperature": 1.3,
        },
        "pipeline": {"intermediate_lang": "fi", "step4_provider": "niutrans"},
        "providers": {
            "libretranslate": {
                "base_url": "http://libre.example.com:5000",
                "api_key": "secret-libre",
                "timeout_sec": 30,
            }
        },
    }


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Stub LLM steps, Google Translate, and both Step 4 translators."""
    monkeypatch.setattr(
        pipeline_module,
        "llm_rewrite",
        lambda **kwargs: f"rewritten({kwargs['target_language']}): {kwargs['text']}",
    )
    monkeypatch.setattr(pipeline_module, "google_translate", lambda text, source, target: f"google({source}->{target}): {text}")

    captured = {}

    def fake_niutrans(text, source, target, api_key):
        captured["niutrans"] = {"text": text, "source": source, "target": target, "api_key": api_key}
        return f"niutrans({source}->{target}): {text}"

    def fake_libretranslate(text, source, target, base_url, api_key="", timeout=60):
        captured["libretranslate"] = {
            "text": text,
            "source": source,
            "target": target,
            "base_url": base_url,
            "api_key": api_key,
            "timeout": timeout,
        }
        return f"libre({source}->{target}): {text}"

    monkeypatch.setattr(pipeline_module, "niutrans_translate", fake_niutrans)
    monkeypatch.setattr(pipeline_module, "libretranslate_translate", fake_libretranslate)

    return captured


def test_step4_defaults_to_niutrans(base_config, stub_pipeline):
    result = run_standard_pipeline("hello", base_config, target_lang="en")

    assert "niutrans" in stub_pipeline
    assert stub_pipeline["niutrans"]["source"] == "fi"
    assert stub_pipeline["niutrans"]["target"] == "en"
    assert stub_pipeline["niutrans"]["api_key"] == "secret-niutrans"

    assert result["result"].startswith("niutrans(")
    step4 = result["steps"][3]
    assert step4["step"] == 4
    assert step4["engine"] == "Niutrans"


def test_step4_uses_libretranslate_when_configured(base_config, stub_pipeline):
    base_config["pipeline"]["step4_provider"] = "libretranslate"

    result = run_standard_pipeline("hello", base_config, target_lang="en")

    assert "libretranslate" in stub_pipeline
    assert stub_pipeline["libretranslate"]["source"] == "fi"
    assert stub_pipeline["libretranslate"]["target"] == "en"
    assert stub_pipeline["libretranslate"]["base_url"] == "http://libre.example.com:5000"
    assert stub_pipeline["libretranslate"]["api_key"] == "secret-libre"
    assert stub_pipeline["libretranslate"]["timeout"] == 30

    assert result["result"].startswith("libre(")
    step4 = result["steps"][3]
    assert step4["step"] == 4
    assert step4["engine"] == "LibreTranslate"


def test_step4_preserves_response_shape(base_config, stub_pipeline):
    base_config["pipeline"]["step4_provider"] = "libretranslate"

    result = run_standard_pipeline("hello", base_config, target_lang="en")

    assert "result" in result
    assert "steps" in result
    assert "processing_time_ms" in result
    assert len(result["steps"]) == 4
    assert all("step" in s and "engine" in s and "output" in s for s in result["steps"])

"""Tests for the v1.5 Standard Pipeline API (src/api.py + src/standard/api.py).

All external API calls are mocked so no API keys or network access are needed.
"""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture
def client(monkeypatch, tmp_path: Path) -> TestClient:
    """Provide a test client configured with a temporary, safe config.toml."""
    config = tmp_path / "config.toml"
    config.write_text(
        """
[general]
target_language = "en"

[api_keys]
deepseek_api_key = "sk-secret"
openrouter_api_key = "sk-or-secret"
niutrans_api_key = "secret-niutrans"

[llm]
provider = "deepseek"
model = "deepseek-chat"
base_url = "https://api.deepseek.com"
temperature = 1.3
http_referer = "https://example.com"
app_title = "Test App"

[pipeline]
model = "fallback-model"
temperature = 1.1
intermediate_lang = "fi"
step4_provider = "niutrans"

[providers.libretranslate]
base_url = "http://libre.example.com:5000"
api_key = "secret-libre"
timeout_sec = 30
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("CONFIG_PATH", str(config))
    return TestClient(app)


def test_v1_health(client: TestClient) -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.5"}


def test_v1_config_redacts_api_keys(client: TestClient) -> None:
    response = client.get("/v1/config")
    assert response.status_code == 200

    data = response.json()
    assert { "intermediate_lang", "step4_provider", "provider", "model", "base_url", "libretranslate_base_url", "temperature", }.issubset(data.keys())

    # No API keys or secrets should be exposed anywhere in the response.
    response_text = response.text
    assert "secret" not in response_text.lower()
    assert "api_key" not in response_text.lower()
    assert "sk-" not in response_text

    assert data["provider"] == "deepseek"
    assert data["model"] == "deepseek-chat"
    assert data["base_url"] == "https://api.deepseek.com"
    assert data["intermediate_lang"] == "fi"
    assert data["step4_provider"] == "niutrans"
    assert data["libretranslate_base_url"] == "http://libre.example.com:5000"
    assert data["temperature"] == 1.3


def test_v1_humanize_standard_response_shape(client: TestClient, monkeypatch) -> None:
    """POST /v1/humanize/standard returns the expected shape and timing."""
    import src.standard.api as api_module

    def fake_run(text: str, config: Any, target_lang: str) -> dict:
        assert text == "hello world"
        assert target_lang == "en"
        return {
            "result": "Hello, world!",
            "steps": [
                {
                    "step": 1,
                    "engine": "DeepSeek",
                    "direction": "Input → Chinese",
                    "output": "你好世界",
                    "length": 4,
                }
            ],
            "processing_time_ms": 1200,
        }

    monkeypatch.setattr(api_module, "run_standard_pipeline", fake_run)

    response = client.post("/v1/humanize/standard", json={"text": "hello world", "target_lang": "en"})
    assert response.status_code == 200

    data = response.json()
    assert data["result"] == "Hello, world!"
    assert data["processing_time_ms"] == 1200
    assert len(data["steps"]) == 1
    assert data["target_lang"] == {"original": "en", "normalized": "en"}
    assert data["pipeline"]["intermediate_lang"] == "fi"


def test_v1_humanize_standard_language_normalization(client: TestClient, monkeypatch) -> None:
    """Locale-style codes like en-US are normalized to base codes before running the pipeline."""
    import src.standard.api as api_module

    captured: dict[str, Any] = {}

    def fake_run(text: str, config: Any, target_lang: str) -> dict:
        captured["target_lang"] = target_lang
        return {
            "result": "Hello!",
            "steps": [],
            "processing_time_ms": 500,
        }

    monkeypatch.setattr(api_module, "run_standard_pipeline", fake_run)

    response = client.post("/v1/humanize/standard", json={"text": "hello", "target_lang": "en-US"})
    assert response.status_code == 200

    assert captured["target_lang"] == "en"
    data = response.json()
    assert data["target_lang"] == {"original": "en-US", "normalized": "en"}


def test_v1_humanize_standard_rejects_empty_text(client: TestClient) -> None:
    response = client.post("/v1/humanize/standard", json={"text": "", "target_lang": "en"})
    assert response.status_code == 422


def test_v1_humanize_legacy_bridge(client: TestClient, monkeypatch) -> None:
    """POST /v1/humanize accepts the legacy body format and returns the legacy shape."""
    from src.methodologies import humanizer

    class FakeHumanizeResult:
        text = "rewritten!"
        method_used = "translation_chain"
        processing_time = 0.5

    def fake_process(self, text: str, method: str = None, **kwargs) -> Any:
        assert text == "hello"
        assert method == "translation_chain"
        assert kwargs["tier"] == "standard"
        assert kwargs["language"] == "en-US"
        return FakeHumanizeResult()

    monkeypatch.setattr(humanizer.Humanizer, "process", fake_process)

    response = client.post(
        "/v1/humanize",
        json={"text": "hello", "method": "translation_chain", "language": "en-US", "tier": "standard"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "rewritten!"
    assert data["method"] == "translation_chain"
    assert data["processing_time_ms"] == 500


# The legacy v1.0 endpoints are mounted at the root and should not be broken.
# We do not assert on their behavior here (which would require API keys), but we
# verify the routes are reachable and the app structure is intact.

def test_legacy_methods_endpoint_is_reachable(client: TestClient) -> None:
    response = client.get("/methods")
    assert response.status_code == 200
    assert "methods" in response.json()


def test_legacy_health_endpoint_is_reachable(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

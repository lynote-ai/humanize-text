"""API tests — no network calls (pipeline is mocked)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.standard.api import app


@pytest.fixture
def client():
    app.state.config = {
        "api_keys": {
            "deepseek_api_key": "test-deepseek",
            "niutrans_api_key": "test-niutrans",
        },
        "pipeline": {"intermediate_lang": "fi"},
    }
    app.state.config_error = None
    with TestClient(app) as test_client:
        yield test_client


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("src.standard.api.run_standard_pipeline")
def test_humanize_returns_result(mock_pipeline, client):
    mock_pipeline.return_value = {
        "result": "humanized output",
        "steps": [{"step": 1, "engine": "DeepSeek", "direction": "test", "output": "x", "length": 1}],
        "processing_time_ms": 1234,
    }
    response = client.post(
        "/humanize",
        json={"text": "AI generated text", "target": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "humanized output"
    assert data["processing_time_ms"] == 1234
    assert "steps" not in data
    mock_pipeline.assert_called_once()


@patch("src.standard.api.run_standard_pipeline")
def test_humanize_include_steps(mock_pipeline, client):
    steps = [{"step": 1, "engine": "DeepSeek", "direction": "test", "output": "x", "length": 1}]
    mock_pipeline.return_value = {
        "result": "humanized output",
        "steps": steps,
        "processing_time_ms": 500,
    }
    response = client.post(
        "/humanize",
        json={"text": "AI text", "include_steps": True},
    )
    assert response.status_code == 200
    assert response.json()["steps"] == steps


def test_humanize_empty_text_returns_422(client):
    response = client.post("/humanize", json={"text": ""})
    assert response.status_code == 422


def test_humanize_missing_config_returns_503():
    app.state.config = None
    app.state.config_error = "Config file not found: config/config.toml"
    with TestClient(app) as client:
        response = client.post("/humanize", json={"text": "some text"})
    assert response.status_code == 503

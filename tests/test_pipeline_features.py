"""Tests for pre-flight config validation and the --json CLI output.

No network or API keys required — the pipeline itself is mocked for the
CLI tests, and the validator is a pure function.
"""

import json

import pytest

import src.standard.pipeline as pipeline_module
from src.standard.pipeline import _validate_pipeline_config


def _valid_config() -> dict:
    return {
        "api_keys": {"niutrans_api_key": "secret-niutrans"},
        "pipeline": {"intermediate_lang": "fi"},
    }


# --- Pre-flight config validation (#65) ---------------------------------

def test_validate_config_passes_with_valid_config():
    _validate_pipeline_config(_valid_config())  # should not raise


def test_validate_config_rejects_missing_niutrans_key():
    cfg = _valid_config()
    cfg["api_keys"]["niutrans_api_key"] = ""
    with pytest.raises(ValueError, match="niutrans_api_key"):
        _validate_pipeline_config(cfg)


def test_validate_config_rejects_unknown_intermediate_lang():
    cfg = _valid_config()
    cfg["pipeline"]["intermediate_lang"] = "finnish"  # should be the code "fi"
    with pytest.raises(ValueError, match="intermediate_lang"):
        _validate_pipeline_config(cfg)


def test_validate_config_reports_all_errors_together():
    cfg = {"api_keys": {}, "pipeline": {"intermediate_lang": "xx"}}
    with pytest.raises(ValueError) as exc:
        _validate_pipeline_config(cfg)
    msg = str(exc.value)
    assert "niutrans_api_key" in msg
    assert "intermediate_lang" in msg


# --- CLI --json output (#64) --------------------------------------------

def _write_config(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[api_keys]\nniutrans_api_key = "x"\n', encoding="utf-8")
    return config_file


def test_cli_json_output(monkeypatch, tmp_path):
    from click.testing import CliRunner

    fake_result = {
        "result": "humanized",
        "steps": [
            {"step": 1, "engine": "DeepSeek", "direction": "Input → Chinese", "output": "你好", "length": 2}
        ],
        "processing_time_ms": 42,
    }
    monkeypatch.setattr(
        pipeline_module, "run_standard_pipeline",
        lambda text, cfg, target_lang="en": fake_result,
    )

    runner = CliRunner()
    result = runner.invoke(
        pipeline_module.main,
        ["--input", "hello world", "--config", str(_write_config(tmp_path)), "--json"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["result"] == "humanized"
    assert data["processing_time_ms"] == 42
    assert data["steps"][0]["output"] == "你好"  # ensure_ascii=False keeps CJK readable


def test_cli_plain_output_unchanged(monkeypatch, tmp_path):
    from click.testing import CliRunner

    monkeypatch.setattr(
        pipeline_module, "run_standard_pipeline",
        lambda text, cfg, target_lang="en": {"result": "just text", "steps": [], "processing_time_ms": 1},
    )

    runner = CliRunner()
    result = runner.invoke(
        pipeline_module.main,
        ["--input", "hi", "--config", str(_write_config(tmp_path))],
    )
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "just text"

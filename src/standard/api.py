"""v1.5 Standard Pipeline REST API.

Exposes the production Standard Pipeline under `/v1` so the frontend can use it
as the primary path while the legacy `/humanize` endpoints remain available.
"""

import os
import time
from typing import Optional

import toml
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.methodologies.humanizer import Humanizer
from src.standard.pipeline import run_standard_pipeline

router = APIRouter()


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def _get_config_path() -> str:
    return os.environ.get("CONFIG_PATH", "config/config.toml")


def _load_config() -> dict:
    path = _get_config_path()
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Config file not found: {path}",
        )
    with open(path, "r", encoding="utf-8") as f:
        return toml.load(f)


# ---------------------------------------------------------------------------
# Language normalization
# ---------------------------------------------------------------------------


def normalize_target_lang(target_lang: str) -> str:
    """Map locale-style codes to the base language codes the pipeline expects.

    Examples:
        en-US -> en, fr-FR -> fr, zh-CN -> zh, ja-JP -> ja.
    """
    lower = target_lang.lower()
    if lower.startswith("en-"):
        return "en"
    if lower.startswith("fr-"):
        return "fr"
    if lower.startswith("zh-"):
        return "zh"
    if lower.startswith("ja-"):
        return "ja"
    if lower.startswith("ko-"):
        return "ko"
    if lower.startswith("de-"):
        return "de"
    if lower.startswith("es-"):
        return "es"
    if lower.startswith("pt-"):
        return "pt"
    if lower.startswith("ru-"):
        return "ru"
    if lower.startswith("ar-"):
        return "ar"
    if lower.startswith("it-"):
        return "it"
    if lower.startswith("nl-"):
        return "nl"
    return target_lang.split("-")[0]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class StandardRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to humanize")
    target_lang: str = Field(default="en", description="Target language code")


class StandardResponse(BaseModel):
    result: str
    steps: list
    processing_time_ms: int
    target_lang: dict
    pipeline: dict


class LegacyRequest(BaseModel):
    text: str
    method: str = "translation_chain"
    language: str = "en"
    tier: str = "standard"


class LegacyResponse(BaseModel):
    result: str
    method: str
    processing_time_ms: int


class HealthResponse(BaseModel):
    status: str
    version: str


class ConfigResponse(BaseModel):
    intermediate_lang: str
    step4_provider: str
    provider: str
    model: str
    base_url: str
    libretranslate_base_url: str
    temperature: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
def v1_health():
    return {"status": "ok", "version": "1.5"}


@router.get("/config", response_model=ConfigResponse)
def v1_config():
    """Return non-sensitive pipeline configuration. API keys are never exposed."""
    config = _load_config()
    llm = config.get("llm", {})
    pipeline = config.get("pipeline", {})
    libre_cfg = config.get("providers", {}).get("libretranslate", {})

    return {
        "intermediate_lang": pipeline.get("intermediate_lang", "fi"),
        "step4_provider": pipeline.get("step4_provider", "niutrans"),
        "provider": llm.get("provider", "deepseek"),
        "model": llm.get("model") or pipeline.get("model", "deepseek-chat"),
        "base_url": llm.get("base_url", ""),
        "libretranslate_base_url": libre_cfg.get("base_url", ""),
        "temperature": llm.get("temperature", pipeline.get("temperature", 1.3)),
    }


@router.post("/humanize/standard", response_model=StandardResponse)
def v1_humanize_standard(req: StandardRequest):
    """Run the v1.5 Standard Pipeline (two LLM rewrites + two translations)."""
    config = _load_config()
    normalized = normalize_target_lang(req.target_lang)

    result = run_standard_pipeline(req.text, config, target_lang=normalized)

    return {
        "result": result["result"],
        "steps": result["steps"],
        "processing_time_ms": result["processing_time_ms"],
        "target_lang": {
            "original": req.target_lang,
            "normalized": normalized,
        },
        "pipeline": {
            "intermediate_lang": config.get("pipeline", {}).get("intermediate_lang", "fi"),
        },
    }


@router.post("/humanize", response_model=LegacyResponse)
def v1_humanize_legacy(req: LegacyRequest):
    """Legacy bridge: route the v1.0 request format to the v1.0 dispatcher."""
    h = Humanizer(config_path=_get_config_path())
    result = h.process(
        req.text, method=req.method, tier=req.tier, language=req.language
    )
    return {
        "result": result.text,
        "method": result.method_used,
        "processing_time_ms": int(result.processing_time * 1000),
    }

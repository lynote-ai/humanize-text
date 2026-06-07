"""FastAPI server for the Standard Pipeline."""

import os
from contextlib import asynccontextmanager
from typing import Any

import toml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .pipeline import run_standard_pipeline

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config/config.toml")


def _load_config(path: str) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    return toml.load(path)


def _validate_config(config: dict) -> None:
    api_keys = config.get("api_keys", {})
    missing = []
    if not api_keys.get("deepseek_api_key"):
        missing.append("deepseek_api_key")
    if not api_keys.get("niutrans_api_key"):
        missing.append("niutrans_api_key")
    if missing:
        raise ValueError(f"Missing required API keys in config: {', '.join(missing)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        config = _load_config(CONFIG_PATH)
        _validate_config(config)
        app.state.config = config
    except (FileNotFoundError, ValueError) as exc:
        app.state.config = None
        app.state.config_error = str(exc)
    yield


app = FastAPI(title="Humanize Text API", lifespan=lifespan)


class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target: str = "en"
    include_steps: bool = False


class HumanizeResponse(BaseModel):
    result: str
    processing_time_ms: int
    steps: list[dict[str, Any]] | None = None


def _get_config_or_raise(app: FastAPI) -> dict:
    if app.state.config is None:
        raise HTTPException(
            status_code=503,
            detail=app.state.config_error or "Service configuration is unavailable",
        )
    return app.state.config


@app.get("/health")
def api_health():
    return {"status": "ok"}


@app.post("/humanize", response_model=HumanizeResponse)
def api_humanize(req: HumanizeRequest):
    config = _get_config_or_raise(app)
    try:
        result = run_standard_pipeline(req.text, config, target_lang=req.target)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Pipeline processing failed") from exc

    response: dict[str, Any] = {
        "result": result["result"],
        "processing_time_ms": result["processing_time_ms"],
    }
    if req.include_steps:
        response["steps"] = result["steps"]
    return response

"""Unified FastAPI entry point combining v1.0 legacy endpoints and v1.5 Standard API.

The v1.5 router is mounted under `/v1`; the v1.0 dispatcher and its static
frontend are mounted at root so the same Uvicorn process serves both.
"""

from fastapi import FastAPI

from src.methodologies.humanizer import app as legacy_app
from src.standard.api import router

app = FastAPI(title="Humanize-Text API")

# v1.5 Standard Pipeline routes (checked before the legacy mount)
app.include_router(router, prefix="/v1")

# v1.0 dispatcher + Svelte frontend static files
app.mount("/", legacy_app, name="legacy")

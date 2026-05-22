"""v1.0 multi-method dispatcher (reference).

Original entry point that routes between the 4 methodologies. Kept for
backwards compatibility and reference. New code should use the v1.5
Standard Pipeline directly:

    from src.pipeline import run_standard_pipeline
"""

import time
from dataclasses import dataclass

import click
import toml
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from .translation_chain import TranslationChainProcessor
from .llm_rewriter import LLMRewriteProcessor
from .detection_pipeline import DetectionGuidedProcessor
from .mixed_engine import MixedEngineProcessor


@dataclass
class HumanizeResult:
    text: str
    method_used: str
    processing_time: float


class Humanizer:
    METHODS = {
        "translation_chain": TranslationChainProcessor,
        "llm_rewrite": LLMRewriteProcessor,
        "detection_guided": DetectionGuidedProcessor,
        "mixed_engine": MixedEngineProcessor,
    }

    def __init__(self, config_path: str = "config/config.toml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = toml.load(f)

    def process(self, text: str, method: str = None, **kwargs) -> HumanizeResult:
        method = method or self.config["general"]["default_method"]
        if method not in self.METHODS:
            raise ValueError(f"Unknown method: {method}. Available: {list(self.METHODS.keys())}")

        processor = self.METHODS[method](self.config)
        start = time.time()
        result_text = processor.process(text, **kwargs)
        elapsed = time.time() - start

        return HumanizeResult(
            text=result_text,
            method_used=method,
            processing_time=elapsed,
        )


# --- FastAPI app (used by Docker) ---

app = FastAPI(title="AI-Humanizer API")


class HumanizeRequest(BaseModel):
    text: str
    method: str = "translation_chain"
    language: str = "en"
    tier: str = "standard"


@app.post("/humanize")
def api_humanize(req: HumanizeRequest):
    import os
    config_path = os.environ.get("CONFIG_PATH", "config/config.toml")
    h = Humanizer(config_path=config_path)
    result = h.process(req.text, method=req.method, tier=req.tier)
    return {
        "result": result.text,
        "method": result.method_used,
        "processing_time_ms": int(result.processing_time * 1000),
    }


@app.get("/methods")
def api_methods():
    return {"methods": list(Humanizer.METHODS.keys())}


@app.get("/health")
def api_health():
    return {"status": "ok"}


# --- CLI ---

@click.command()
@click.option("--input", "input_text", required=True, help="Input text or path to text file")
@click.option("--method", default=None, help="Humanization method")
@click.option("--output", default=None, help="Output file path")
@click.option("--config", default="config/config.toml", help="Config file path")
@click.option("--tier", default="standard", help="Processing tier")
@click.option("--language", default="en", help="Target language code")
@click.option("--serve", is_flag=True, help="Start API server instead of CLI processing")
def main(input_text, method, output, config, tier, language, serve):
    if serve:
        uvicorn.run(app, host="0.0.0.0", port=8000)
        return

    import os
    if os.path.isfile(input_text):
        with open(input_text, "r", encoding="utf-8") as f:
            input_text = f.read()

    h = Humanizer(config_path=config)
    result = h.process(input_text, method=method, tier=tier)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result.text)
        click.echo(f"Written to {output} ({result.processing_time:.1f}s)")
    else:
        click.echo(result.text)


if __name__ == "__main__":
    main()

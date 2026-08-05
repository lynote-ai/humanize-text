"""v1.0 multi-method dispatcher (reference).

The optional detection and API dependencies are imported only when their features
are used. The recommended v1.5 Standard Pipeline therefore remains lightweight.
"""

import importlib
import time
from dataclasses import dataclass

import click
import toml


@dataclass
class HumanizeResult:
    text: str
    method_used: str
    processing_time: float


class Humanizer:
    METHODS = {
        "translation_chain": ("src.methodologies.translation_chain", "TranslationChainProcessor"),
        "llm_rewrite": ("src.methodologies.llm_rewriter", "LLMRewriteProcessor"),
        "detection_guided": ("src.methodologies.detection_pipeline", "DetectionGuidedProcessor"),
        "mixed_engine": ("src.methodologies.mixed_engine", "MixedEngineProcessor"),
    }

    def __init__(self, config_path: str = "config/config.toml"):
        with open(config_path, "r", encoding="utf-8") as config_file:
            self.config = toml.load(config_file)

    @classmethod
    def _processor_class(cls, method: str):
        module_name, class_name = cls.METHODS[method]
        module = importlib.import_module(module_name)
        return getattr(module, class_name)

    def process(self, text: str, method: str = None, **kwargs) -> HumanizeResult:
        method = method or self.config["general"]["default_method"]
        if method not in self.METHODS:
            raise ValueError(f"Unknown method: {method}. Available: {list(self.METHODS.keys())}")

        processor = self._processor_class(method)(self.config)
        start = time.time()
        result_text = processor.process(text, **kwargs)
        return HumanizeResult(
            text=result_text,
            method_used=method,
            processing_time=time.time() - start,
        )


def create_api_app():
    """Create the optional FastAPI application.

    Install ``fastapi``, ``pydantic`` and ``uvicorn`` before using ``--serve``.
    They are intentionally not required by the standard CLI pipeline.
    """
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
    except ImportError as exc:
        raise RuntimeError(
            "API dependencies are missing. Install fastapi, pydantic and uvicorn to use --serve."
        ) from exc

    api = FastAPI(title="Humanize Text Reference API")

    class HumanizeRequest(BaseModel):
        text: str
        method: str = "translation_chain"
        language: str = "en"
        tier: str = "standard"

    @api.post("/humanize")
    def api_humanize(request: HumanizeRequest):
        import os

        config_path = os.environ.get("CONFIG_PATH", "config/config.toml")
        result = Humanizer(config_path=config_path).process(
            request.text, method=request.method, tier=request.tier
        )
        return {
            "result": result.text,
            "method": result.method_used,
            "processing_time_ms": int(result.processing_time * 1000),
        }

    @api.get("/methods")
    def api_methods():
        return {"methods": list(Humanizer.METHODS.keys())}

    @api.get("/health")
    def api_health():
        return {"status": "ok"}

    return api


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
        try:
            import uvicorn
        except ImportError as exc:
            raise click.ClickException(
                "API dependencies are missing. Install fastapi, pydantic and uvicorn."
            ) from exc
        uvicorn.run(create_api_app(), host="0.0.0.0", port=8000)
        return

    import os

    if os.path.isfile(input_text):
        with open(input_text, "r", encoding="utf-8") as input_file:
            input_text = input_file.read()

    result = Humanizer(config_path=config).process(input_text, method=method, tier=tier)
    if output:
        with open(output, "w", encoding="utf-8") as output_file:
            output_file.write(result.text)
        click.echo(f"Written to {output} ({result.processing_time:.1f}s)")
    else:
        click.echo(result.text)


if __name__ == "__main__":
    main()

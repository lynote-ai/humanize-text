"""
Standard Pipeline v1.5.1 — Multi-language translation chain with LLM humanization.

Pipeline (4 steps):
  Step 1: Input (EN) → Chinese — DeepSeek humanization rewrite
  Step 2: Chinese → Japanese — DeepSeek humanization rewrite (with history)
  Step 3: Japanese → Finnish — Google Translate (first translation hop)
  Step 4: Finnish → Target (EN) — Niutrans (second translation hop)

This chain was selected after empirical testing against AI detectors on
50+ sample texts. See `examples/showcase/` for input/output traces of all
4 intermediate steps on 5 real samples.
"""

import time
import click
import toml

from .translators import google_translate, niutrans_translate
from .llm_rewriter import deepseek_rewrite


def run_standard_pipeline(text: str, config: dict, target_lang: str = "en") -> dict:
    """Run the Standard humanization pipeline.

    Args:
        text: Input text to humanize.
        config: Configuration dict loaded from config.toml.
        target_lang: Target language code for final output (default: "en").

    Returns:
        dict with keys:
            - 'result': final humanized text
            - 'steps': list of {step, engine, direction, output, length}
            - 'processing_time_ms': total elapsed time in milliseconds
    """
    ds_key = config["api_keys"]["deepseek_api_key"]
    niutrans_key = config["api_keys"]["niutrans_api_key"]
    intermediate_lang = config.get("pipeline", {}).get("intermediate_lang", "fi")

    steps = []
    start = time.time()

    # Step 1: DeepSeek — Input (EN) → Chinese humanization rewrite
    step1 = deepseek_rewrite(
        text=text,
        target_language="中文",
        api_key=ds_key,
        history=None,
    )
    steps.append({
        "step": 1, "engine": "DeepSeek",
        "direction": "Input → Chinese (中文改写)",
        "output": step1, "length": len(step1),
    })

    # Step 2: DeepSeek — Chinese → Japanese (carries step 1 as history)
    step2 = deepseek_rewrite(
        text=step1,
        target_language="日语",
        api_key=ds_key,
        history={"input": text, "output": step1},
    )
    steps.append({
        "step": 2, "engine": "DeepSeek",
        "direction": "Chinese → Japanese (日语改写)",
        "output": step2, "length": len(step2),
    })

    # Step 3: Google Translate — Japanese → intermediate language (first translation hop)
    step3 = google_translate(step2, source="ja", target=intermediate_lang)
    steps.append({
        "step": 3, "engine": "Google",
        "direction": f"Japanese → {intermediate_lang.upper()} (一轮翻译)",
        "output": step3, "length": len(step3),
    })

    # Step 4: Niutrans — intermediate language → target (second translation hop)
    step4 = niutrans_translate(
        step3,
        source=intermediate_lang,
        target=_lang_code_to_niutrans(target_lang),
        api_key=niutrans_key,
    )
    steps.append({
        "step": 4, "engine": "Niutrans",
        "direction": f"{intermediate_lang.upper()} → {target_lang.upper()} (二轮翻译)",
        "output": step4, "length": len(step4),
    })

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "result": step4,
        "steps": steps,
        "processing_time_ms": elapsed_ms,
    }


def _lang_code_to_niutrans(code: str) -> str:
    """Map common language codes to Niutrans format."""
    mapping = {
        "en": "en", "zh": "zh", "ja": "ja", "ko": "ko",
        "fr": "fr", "de": "de", "es": "es", "pt": "pt",
        "ru": "ru", "ar": "ar", "it": "it", "nl": "nl",
        "fi": "fi",
    }
    return mapping.get(code, code)


@click.command()
@click.option("--input", "input_text", required=True, help="Input text or path to text file")
@click.option("--target", default="en", help="Target language code (default: en)")
@click.option("--config", default="config/config.toml", help="Config file path")
@click.option("--output", default=None, help="Output file path")
@click.option("--verbose", is_flag=True, help="Show step-by-step progress")
def main(input_text, target, config, output, verbose):
    """Run the Standard humanization pipeline."""
    import os

    if os.path.isfile(input_text):
        with open(input_text, "r", encoding="utf-8") as f:
            input_text = f.read()

    cfg = toml.load(config)
    result = run_standard_pipeline(input_text, cfg, target_lang=target)

    if verbose:
        click.echo("\n--- Pipeline Steps ---")
        for s in result["steps"]:
            click.echo(f"  Step {s['step']}: {s['engine']} | {s['direction']} | {s['length']} chars")
        click.echo(f"  Total: {result['processing_time_ms']}ms\n")

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result["result"])
        click.echo(f"Written to {output}")
    else:
        click.echo(result["result"])


if __name__ == "__main__":
    main()

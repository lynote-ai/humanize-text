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

from .llm_client import resolve_llm_config
from .translators import google_translate, niutrans_translate
from .llm_rewriter import llm_rewrite




def _validate_pipeline_config(config: dict, provider: str) -> None:
    """Pre-flight check: validate all required keys exist and are non-empty.

    Raises ValueError listing every missing config value so the operator
    can fix them all at once instead of discovering them one step at a time.
    Called before any API calls to avoid wasting LLM credits when a later
    step would fail due to missing credentials.
    """
    errors = []

    # Niutrans key (Step 4) — not validated by resolve_llm_config
    niutrans_key = config.get("api_keys", {}).get("niutrans_api_key", "")
    if not niutrans_key:
        errors.append(
            "niutrans_api_key is empty. "
            "Set api_keys.niutrans_api_key in config.toml "
            "(get a free key at niutrans.com)"
        )

    # Intermediate language sanity check
    intermediate = config.get("pipeline", {}).get("intermediate_lang", "fi")
    known_codes = {
        "en", "zh", "ja", "ko", "fr", "de", "es", "pt",
        "ru", "ar", "it", "nl", "fi",
    }
    if intermediate not in known_codes:
        errors.append(
            f"intermediate_lang={intermediate!r} is not a recognized "
            f"language code. Known codes: {sorted(known_codes)}"
        )

    if errors:
        raise ValueError(
            "Pipeline config validation failed:
  - "
            + "
  - ".join(errors)
        )


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
    llm = resolve_llm_config(config)
    _validate_pipeline_config(config, llm["provider"])
    niutrans_key = config["api_keys"]["niutrans_api_key"]
    intermediate_lang = config.get("pipeline", {}).get("intermediate_lang", "fi")
    engine_name = llm["display_name"]

    steps = []
    start = time.time()

    # Step 1: LLM — Input (EN) → Chinese humanization rewrite
    step1 = llm_rewrite(
        text=text,
        target_language="中文",
        api_key=llm["api_key"],
        base_url=llm["base_url"],
        model=llm["model"],
        history=None,
        temperature=llm["temperature"],
        extra_headers=llm["extra_headers"],
        provider=llm["provider"],
    )
    steps.append({
        "step": 1, "engine": engine_name,
        "direction": "Input → Chinese (中文改写)",
        "output": step1, "length": len(step1),
    })

    # Step 2: LLM — Chinese → Japanese (carries step 1 as history)
    step2 = llm_rewrite(
        text=step1,
        target_language="日语",
        api_key=llm["api_key"],
        base_url=llm["base_url"],
        model=llm["model"],
        history={"input": text, "output": step1},
        temperature=llm["temperature"],
        extra_headers=llm["extra_headers"],
        provider=llm["provider"],
    )
    steps.append({
        "step": 2, "engine": engine_name,
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

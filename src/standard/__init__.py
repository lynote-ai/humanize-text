"""Standard Pipeline (v1.5.1) — production path.

This is the recommended path for actual use. The Standard Pipeline integrates
Method 1 (Translation Chain) and Method 2 (LLM Rewriting) from the v1.0
methodologies into a fixed, validated 4-step chain.

Quick start:

    from src.standard.pipeline import run_standard_pipeline
    import toml

    config = toml.load("config/config.toml")
    result = run_standard_pipeline("Your text here", config, target_lang="en")
    print(result["result"])
"""

from .pipeline import run_standard_pipeline
from .llm_rewriter import deepseek_rewrite
from .translators import google_translate, niutrans_translate

__all__ = [
    "run_standard_pipeline",
    "deepseek_rewrite",
    "google_translate",
    "niutrans_translate",
]

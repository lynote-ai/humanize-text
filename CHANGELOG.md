# Changelog

## [1.5.0] - 2026-05-18

### Added — Standard Pipeline (Production)
- **`src/pipeline.py`** — Production Standard Pipeline integrating Method 1 (Translation Chain) + Method 2 (LLM Rewriting) into a fixed 5-step chain
- **`src/llm_rewriter.py`** — DeepSeek-based humanization rewriter with history-context carrying (temperature 1.3)
- **`src/translators.py`** — Google Translate (deep-translator) + Niutrans API clients with chunking for long text
- **`n8n/humanize_standard.json`** — Importable n8n workflow for no-code automation
- CLI entry: `python -m src.pipeline --input ... --target ...`
- Bilingual README (English + Chinese)
- Quality metrics from expert evaluation on 50 text pairs (9.1/10 overall)

### Positioning
- v1.5 Standard Pipeline is now the **recommended production path**
- v1.0 four methodologies remain in `src/` as **reference implementations** for research and customization

## [1.0.0] - 2025-12-15

### Added — Four Humanization Methodologies (Reference)
- **Method 1: Translation Chain** (`src/translation_chain.py`) — Multi-language translation hops
- **Method 2: Multi-Turn LLM Rewriting** (`src/humanizer.py`, partial) — Iterative LLM rewrites
- **Method 3: Detection-Guided Feedback Loop** (`src/detection_pipeline.py`, `src/detectors/`) — Binoculars-inspired + RoBERTa scoring loop
- **Method 4: Mixed-Engine Translation** (`src/mixed_engine.py`) — Multiple NMT engines combined
- Documentation of all four methodologies in `docs/techniques.md`
- Comparison examples in `examples/comparison/`

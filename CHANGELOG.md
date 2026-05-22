# Changelog

## [1.5.2] - 2026-05-22

### Restructured
- **`src/` split into `src/standard/` + `src/methodologies/`** — visual separation of v1.5 production code vs v1.0 reference implementations
- `src/standard/`: `pipeline.py`, `llm_rewriter.py`, `translators.py` (production)
- `src/methodologies/`: `humanizer.py`, `translation_chain.py`, `llm_rewriter.py` (restored `LLMRewriteProcessor`), `detection_pipeline.py`, `mixed_engine.py`, `postprocess.py`, `detectors/`, `utils/` (reference)
- All import paths updated: `python -m src.standard.pipeline`, `from src.standard import run_standard_pipeline`
- `setup.py`, `scripts/start.*`, `Dockerfile`, all docs, all examples updated to match

### Added
- **`tests/test_smoke.py`** — 12 smoke tests: import verification, public API surface, pure-function unit tests, showcase file integrity (all pass, no API keys required)
- **`docs/README.md`** — documentation navigation index with audience-based routing

### Fixed
- Restored missing `LLMRewriteProcessor` class in `src/methodologies/llm_rewriter.py` (was lost during v1.5 merge — `humanizer.py` dispatcher referenced it but the file only had `deepseek_rewrite`)
- `docs/faq.md`: chain description updated from DE→ES to FI (was stale from v1.5.0)
- `docs/installation.md`: repo URL pointed to `molly554/ai-humanize` instead of `lynote-ai/humanize-text`
- `docs/api-reference.md`: rewritten to document both Standard Pipeline and v1.0 dispatcher

## [1.5.1] - 2026-05-22

### Added
- **`examples/showcase/`** — 5 end-to-end input/output traces with **all intermediate step outputs** (中文改写 / 日语改写 / 一轮翻译 / 二轮翻译) plus AI-detection verdicts
- `examples/showcase/README.md` — index with detection-confidence table
- Pipeline result dict now includes `output` for each step (was only `length`)
- New config option `[pipeline].intermediate_lang` to swap the intermediate translation language

### Changed
- **Pipeline aligned with production reality**: chain is now 4 steps (was documented as 5) — `EN → ZH (DeepSeek) → JA (DeepSeek) → FI (Google) → EN (Niutrans)`. Finnish replaces the German→Spanish double-hop based on empirical validation.
- README.md / README-zh.md / docs/pipeline.md updated to match the actual chain
- Step labels now use Chinese conventions (中文改写 / 日语改写 / 一轮翻译 / 二轮翻译) for consistency with internal terminology

### Why this change
The v1.5 documented chain (5 steps with German→Spanish→target) didn't match the actual production pipeline used to generate validation samples. v1.5.1 fixes this so code, docs, and showcase examples are all consistent.

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

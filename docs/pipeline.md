# Standard Pipeline (v1.5.1) — Production Path

> **Positioning:** The Standard Pipeline is the **production-grade integration** added in v1.5 and tuned in v1.5.1 against real samples. It combines Method 1 (Translation Chain) and Method 2 (LLM Rewriting) from the [4 methodologies](techniques.md) into a fixed, validated 4-step chain. This is the recommended path for actual use.
>
> See [`examples/showcase/`](../examples/showcase/) for 5 end-to-end traces of every intermediate step on real input texts.

## Architecture

```
Input Text (EN)
    ↓
Step 1: LLM (temp 1.3)                    ── 中文改写
    Input → Chinese + Humanization Rewrite
    ↓
Step 2: LLM (temp 1.3, with history)       ── 日语改写
    Chinese → Japanese + Humanization Rewrite
    ↓
Step 3: Google Translate                    ── 一轮翻译
    Japanese → Finnish
    ↓
Step 4: Niutrans                            ── 二轮翻译
    Finnish → Target Language (EN)
    ↓
Output (Humanized EN)
```

Steps 1–2 call any **OpenAI-compatible** chat API. The default provider is DeepSeek; set `[llm].provider = "openrouter"` to route through [OpenRouter](https://openrouter.ai). See [configuration.md](configuration.md).

## Why Each Step Matters

### Steps 1-2: LLM Humanization Rewrite

These steps do the heavy lifting. The configured LLM at temperature 1.3 doesn't just translate — it rewrites. The key differences from plain translation:

- **Sentence restructuring:** AI-typical uniform sentence patterns get broken
- **Vocabulary diversification:** Formal/robotic word choices get replaced with natural alternatives
- **Rhythm variation:** The output has varied sentence lengths (burstiness)

Step 2 carries the conversation history from Step 1. This gives the LLM context about what was already changed, preventing it from reverting patterns that Step 1 disrupted.

### Steps 3-4: Cross-Engine Translation Chain

Two translation hops through two different engines compound structural changes:

- **Google (Step 3):** Neural machine translation with the largest training corpus, applied to the Japanese → Finnish hop
- **Niutrans (Step 4):** Different NMT architecture and training data, applied to the Finnish → English hop

Using different engines prevents any single-engine fingerprint from surviving. Each engine restructures grammar differently, and the cumulative effect produces text that doesn't match any known AI generation pattern.

### Language Distance Strategy

The chain maximizes linguistic distance at each hop:

| Hop | Languages | Distance |
|-----|-----------|----------|
| 1 | English → Chinese | High (different family, no shared script) |
| 2 | Chinese → Japanese | Medium (shared characters, different grammar) |
| 3 | Japanese → Finnish | Very High (Japonic → Uralic, SOV → SVO, agglutinative) |
| 4 | Finnish → English | High (Uralic → Germanic) |

Finnish was selected for the intermediate step because of its agglutinative morphology — it forces deep restructuring of word forms and clause boundaries, which is hard to reverse-engineer back into AI-typical patterns.

## Parameters

| Parameter | Value | Why |
|-----------|-------|-----|
| LLM provider | `deepseek` (default), `openrouter`, or `atlascloud` | Set via `[llm].provider` in `config.toml`. All use OpenAI-compatible `/chat/completions`. |
| Temperature | 1.3 | Higher than default (1.0) to increase creative variation. Too high (>1.5) causes incoherence. |
| Model | Provider default or `[llm].model` | `deepseek-chat` (DeepSeek), `deepseek/deepseek-chat` (OpenRouter), or `qwen/qwen3.5-flash` (Atlas Cloud). Any compatible model slug works. |
| Base URL | Provider default or `[llm].base_url` | Override to point at a custom OpenAI-compatible proxy. |
| History | 1 round | Step 2 sees Step 1's context. More rounds didn't improve quality in testing. |
| Intermediate language | `fi` (Finnish) | Configurable via `[pipeline].intermediate_lang` in `config.toml`. |

## Validation

We ran the pipeline end-to-end on 5 input texts across diverse topics (quantum computing, supply chains, financial literacy, peer review, etc.) and saved every intermediate step output.

**Results:** All 5 final outputs were classified as `human` by the AI detector. Confidence scores ranged from 0.7218 to 0.9997.

See [`examples/showcase/`](../examples/showcase/) for the full traces.

---

> **Want more tiers?** [Lynote.ai](https://lynote.ai) adds Advanced (multi-round LLM) and Focus (detection-guided feedback loop) tiers on top of Standard.

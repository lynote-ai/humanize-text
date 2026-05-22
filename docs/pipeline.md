# Standard Pipeline (v1.5) — Production Path

> **Positioning:** The Standard Pipeline is the **production-grade integration** added in v1.5. It combines Method 1 (Translation Chain) and Method 2 (LLM Rewriting) from the [4 methodologies](techniques.md) into a fixed, validated 5-step chain. This is the recommended path for actual use.

## Architecture

```
Input Text
    ↓
Step 1: DeepSeek (temp 1.3)
    Input → Chinese + Humanization Rewrite
    ↓
Step 2: DeepSeek (temp 1.3) [with Step 1 history]
    Chinese → Japanese + Humanization Rewrite
    ↓
Step 3: Google Translate
    Japanese → German
    ↓
Step 4: Niutrans
    German → Spanish
    ↓
Step 5: Niutrans
    Spanish → Target Language
    ↓
Output
```

## Why Each Step Matters

### Steps 1-2: LLM Humanization Rewrite

These steps do the heavy lifting. DeepSeek at temperature 1.3 doesn't just translate — it rewrites. The key differences from plain translation:

- **Sentence restructuring:** AI-typical uniform sentence patterns get broken
- **Vocabulary diversification:** Formal/robotic word choices get replaced with natural alternatives
- **Rhythm variation:** The output has varied sentence lengths (burstiness)

Step 2 carries the conversation history from Step 1. This gives DeepSeek context about what was already changed, preventing it from reverting patterns that Step 1 disrupted.

### Steps 3-5: Multi-Engine Translation Chain

Three translation hops through three different engines compound structural changes:

- **Google (Step 3):** Neural machine translation with the largest training corpus
- **Niutrans (Steps 4-5):** Different NMT architecture, different training data

Using different engines prevents any single-engine fingerprint from surviving. Each engine restructures grammar differently, and the cumulative effect produces text that doesn't match any known AI generation pattern.

### Language Distance Strategy

The chain maximizes linguistic distance at each hop:

| Hop | Languages | Distance |
|-----|-----------|----------|
| 1 | Input → Chinese | High (if input is English) |
| 2 | Chinese → Japanese | Medium (shared characters, different grammar) |
| 3 | Japanese → German | Very High (SOV → SVO, different morphology) |
| 4 | German → Spanish | Medium (both Indo-European, different structure) |
| 5 | Spanish → Target | Varies |

## Parameters

| Parameter | Value | Why |
|-----------|-------|-----|
| Temperature | 1.3 | Higher than default (1.0) to increase creative variation. Too high (>1.5) causes incoherence. |
| Model | deepseek-chat | Good balance of quality, speed, and cost for rewriting tasks. |
| History | 1 round | Step 2 sees Step 1's context. More rounds didn't improve quality in testing. |

---

> **Want more tiers?** [Lynote.ai](https://lynote.ai) adds Advanced (multi-round LLM) and Focus (detection-guided feedback loop) tiers on top of Standard.

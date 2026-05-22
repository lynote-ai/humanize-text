# FAQ

### What's the difference between this repo and ai-humanize?

[ai-humanize](https://github.com/molly554/ai-humanize) documents 4 theoretical approaches. This repo (`humanize-text`) provides the **actual working Standard pipeline** with real code you can run.

### What API keys do I need?

- **DeepSeek** (free tier available) — for LLM humanization rewriting
- **Niutrans** (free tier available) — for translation steps

Google Translate (Step 3) uses the free public API and doesn't require a key.

### How long does processing take?

Typically 10-30 seconds per text, depending on length. The LLM rewriting steps (1-2) take the most time.

### Can I change the language chain?

The current chain (Chinese → Japanese → Finnish → English) is optimized for English input. Changing it requires modifying `src/standard/pipeline.py` or setting `[pipeline].intermediate_lang` in `config.toml`. Different chains may produce different quality levels.

### Why temperature 1.3?

Lower temperatures (1.0) produce more predictable, AI-detectable output. Higher temperatures (>1.5) cause incoherence. 1.3 is the sweet spot found through testing.

### How does this compare to Lynote.ai?

This repo provides the Standard tier only. [Lynote.ai](https://lynote.ai) combines Standard + Advanced + Focus tiers and automatically selects the best approach for each text passage.

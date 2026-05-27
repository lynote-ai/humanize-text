## Free Humanize Text: Open-source toolkit to rewrite AI-generated content into natural
<p align="center">
  <img src="presentation/banner.png" alt="Humanize-Text" width="600"/>
</p>

<p align="center">
  <a href="https://github.com/lynote-ai/humanize-text/stargazers"><img src="https://img.shields.io/github/stars/lynote-ai/humanize-text?style=social" alt="Stars"></a>
  <a href="https://github.com/lynote-ai/humanize-text/network/members"><img src="https://img.shields.io/github/forks/lynote-ai/humanize-text?style=social" alt="Forks"></a>
  <a href="https://github.com/lynote-ai/humanize-text/blob/main/LICENSE"><img src="https://img.shields.io/github/license/lynote-ai/humanize-text" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
  <a href="https://lynote.ai"><img src="https://img.shields.io/badge/Try-Lynote.ai-brightgreen?style=for-the-badge" alt="Lynote.ai"></a>
</p>

<p align="center">
  English | <a href="README-zh.md">中文</a>
</p>

---

## What is Humanize-Text?

An AI text humanization toolkit. This repo evolved through two stages:

- **v1.0** — Documented **4 humanization methodologies** as reference implementations (translation chain, multi-turn LLM rewriting, detection-guided feedback loop, mixed-engine translation). See [docs/techniques.md](docs/techniques.md).
- **v1.5 (current)** — Added the **Standard Pipeline**: a production-grade integration of Method 1 (Translation Chain) + Method 2 (LLM Rewriting), fixed as a 5-step chain we actually run and recommend.

### v1.5.1 — Standard Pipeline (Recommended)

The Standard Pipeline preserves the original writing style while routing text through a 4-step chain: two DeepSeek humanization rewrites followed by two cross-engine translation hops.

```
Input (EN) → Chinese (DeepSeek) → Japanese (DeepSeek) → Finnish (Google) → English (Niutrans)
```

**See [`examples/showcase/`](examples/showcase/) for 5 real samples with full intermediate-step outputs and AI-detection verdicts.**

**Characteristics:**
- Best original style preservation among all approaches
- Fast processing speed
- 100% key information retention (verified on 50 text pairs)
- Expert quality score: 9.1/10

> The 4 underlying methodologies live in `src/methodologies/` as reference implementations for research and customization. The Standard Pipeline (`src/standard/pipeline.py`) is the recommended production path.

> **Want higher bypass rates + all methods combined?**
> Lynote.ai fuses Standard + Advanced + Focus pipelines into one intelligent system — auto-selects the optimal approach for each passage.
>
> **[Try Lynote.ai Free →](https://lynote.ai)**

---

## How It Works

### Step-by-Step Pipeline

| Step | Engine | From → To | Purpose |
|------|--------|-----------|---------|
| 1 | DeepSeek (temp 1.3) | Input → Chinese (Chinese Rewriting) | LLM humanization rewrite + language shift |
| 2 | DeepSeek (temp 1.3) | Chinese → Japanese (Japanese Rewriting) | Second LLM humanization, carries Step 1 as history |
| 3 | Google Translate | Japanese → Finnish (First Round of Translation) | First translation hop — distant language structural disruption |
| 4 | Niutrans | Finnish → English (Second-Round Translation) | Second translation hop — cross-engine reconstruction |

### Why This Chain Works

1. **Steps 1–2 (LLM Rewrite):** DeepSeek at temperature 1.3 rewrites while translating, breaking AI statistical fingerprints with creative variation. Step 2 carries Step 1 as conversation history for coherent humanization.
2. **Steps 3–4 (Multi-Engine Translation):** Two different NMT engines (Google → Niutrans) introduce compounding structural changes. No single-engine fingerprint survives.
3. **Distant Languages:** Chinese → Japanese → Finnish maximizes linguistic distance at each hop, ensuring thorough restructuring before reconstruction to English.

---

## Lynote.ai — Beyond Standard

<p align="center">
  <a href="https://lynote.ai">
    <img src="presentation/lynote_banner.png" alt="Lynote.ai" width="500"/>
  </a>
</p>

The Standard pipeline above is **one of three tiers** available. Each has different trade-offs:

| Tier | Style Preservation | Speed | Approach |
|------|-------------------|-------|----------|
| **Standard** (this repo) | Best | Fast | Translation chain |
| **Advanced** | Good | Medium | Translation chain + LLM multi-round rewriting |
| **Focus** | Moderate | Slower | Translation chain + Detection-guided feedback loop |

**Lynote.ai** combines all three tiers and automatically selects the optimal approach for each text passage:

- **Intelligent Tier Selection** — Analyzes text and picks Standard, Advanced, or Focus per-passage
- **Adaptive Combination** — Can mix tiers within a single document
- **10+ Languages** — English, Chinese, Japanese, Korean, Spanish, French, German, and more
- **Paste & Go** — No setup, no API keys, no configuration

<p align="center">
  <a href="https://lynote.ai"><img src="https://img.shields.io/badge/Try_Lynote.ai_Free-brightgreen?style=for-the-badge" alt="Try Lynote.ai Free"></a>
</p>

---

## Quick Start

| Method | Who It's For | How |
|--------|-------------|-----|
| Lynote.ai | Everyone — all tiers, zero setup | Visit lynote.ai|
| n8n Workflow | No-code automation users | Import [`n8n/humanize_standard.json`](n8n/humanize_standard.json) |
| Python Script | Developers | See below |

### Python

```bash
git clone https://github.com/lynote-ai/humanize-text.git
cd humanize-text
pip install -r requirements.txt
cp config/config.example.toml config/config.toml
# Fill in your API keys in config.toml
python -m src.standard.pipeline --input "Your AI-generated text here"
```

### n8n Workflow

1. Import `n8n/humanize_standard.json` into your n8n instance
2. Configure DeepSeek API key in the HTTP Request nodes
3. Run — input text goes in, humanized text comes out

---

## Showcase — 5 Real Examples with Step-by-Step Outputs

We ran the pipeline end-to-end on 5 real input texts and saved every intermediate step. All 5 final outputs were classified as `human` by the AI detector.

| # | Topic | Detection | Confidence |
|---|-------|-----------|------------|
| [01](examples/showcase/example_01.md) | Quantum Computing | `human` | 0.9997 |
| [02](examples/showcase/example_02.md) | Quantum Readiness Strategy | `human` | 0.9982 |
| [03](examples/showcase/example_03.md) | Sustainable Supply Chains | `human` | 0.7810 |
| [04](examples/showcase/example_04.md) | Financial Literacy | `human` | 0.9924 |
| [05](examples/showcase/example_05.md) | Peer Review in Science | `human` | 0.7218 |

Each example shows: original input → Step 1 (中文改写) → Step 2 (日语改写) → Step 3 (一轮翻译) → Step 4 (二轮翻译, final). See [`examples/showcase/`](examples/showcase/) for full traces.

---

## Quality Metrics

Tested on 50 text pairs with expert evaluation:

| Dimension | Score (out of 10) |
|-----------|-------------------|
| Information Completeness | 10.0 |
| Language Fluency | 9.0 |
| Style Adaptability | 8.8 |
| Readability | 9.2 |
| Creativity & Impact | 8.5 |
| **Overall** | **9.1** |

- **Key Information Retention:** 100% (50/50 pairs)
- All texts preserved original key information without distortion

---

## Comparison with Other Tiers

| | Standard (this repo) | Lynote.ai |
|---|---|---|
| Tiers Available | Standard only | Standard + Advanced + Focus |
| Tier Selection | Manual | Automatic per-passage |
| Style Preservation | Best | Adaptive — best possible per passage |
| Setup | Python + API keys | Zero setup |
| Best For | Style-sensitive content | Any content type |

---

## Documentation

- [Standard Pipeline Technical Details](docs/pipeline.md) — v1.5 production pipeline
- [4 Methodologies Reference](docs/techniques.md) — v1.0 underlying methods
- [Configuration Guide](docs/configuration.md)
- [n8n Workflow Guide](docs/n8n-guide.md)
- [Lynote.ai vs Open Source Comparison](docs/lynote-comparison.md)
- [FAQ](docs/faq.md)

### Repo Structure

```
src/
├── standard/                # ★ v1.5.1 production Standard Pipeline (recommended)
│   ├── pipeline.py          # 4-step chain, CLI entry
│   ├── llm_rewriter.py      # DeepSeek humanization rewrite
│   └── translators.py       # Google + Niutrans engines
│
└── methodologies/           # v1.0 four-methodology reference implementations
    ├── humanizer.py         # v1.0 dispatcher + FastAPI app
    ├── translation_chain.py # Method 1
    ├── llm_rewriter.py      # Method 2
    ├── detection_pipeline.py# Method 3
    ├── mixed_engine.py      # Method 4
    ├── postprocess.py
    ├── detectors/           # Method 3 detectors
    └── utils/

examples/
├── example_usage.py         # ★ v1.5.1 minimal entry
├── showcase/                # ★ 5 real samples with intermediate-step outputs
└── legacy/                  # v1.0 examples + 4-method comparison outputs
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Links

- [Lynote.ai — AI Humanization Platform](https://lynote.ai)
- [Report a Bug](https://github.com/lynote-ai/humanize-text/issues)

### Recommended Projects

- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) — AI short video generator
- [AiToEarn](https://github.com/yikart/AiToEarn) — AI content publishing tool

---

## Star History

<p align="center">
  <a href="https://star-history.com/#lynote-ai/humanize-text&Date">
    <img src="https://api.star-history.com/svg?repos=lynote-ai/humanize-text&type=Date" alt="Star History Chart" width="500">
  </a>
</p>

---

<p align="center">
  <b>If this project helps you, please give it a ⭐!</b>
</p>

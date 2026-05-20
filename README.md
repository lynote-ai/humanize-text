<h1 align="center">AI Humanize Text</h1>

<p align="center">
  <img src="presentation/ai-humanizer-banner.png" alt="AI-Humanizer turns AI drafts into human-like writing" width="900"/>
</p>

<p align="center">
  <a href="https://github.com/molly554/ai-humanize/stargazers"><img src="https://img.shields.io/github/stars/molly554/ai-humanize?style=social" alt="Stars"></a>
  <a href="https://github.com/molly554/ai-humanize/network/members"><img src="https://img.shields.io/github/forks/molly554/ai-humanize?style=social" alt="Forks"></a>
  <a href="https://github.com/molly554/ai-humanize/blob/main/LICENSE"><img src="https://img.shields.io/github/license/molly554/ai-humanize" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
  <a href="https://lynote.ai"><img src="https://img.shields.io/badge/Try-Lynote.ai-brightgreen?style=for-the-badge" alt="Lynote.ai"></a>
</p>

<p align="center">
  <a href="https://github.com/lynote-ai/humanize-text-zh">中文版 →</a>
</p>

---

## What is AI-Humanizer?

An open-source toolkit that explores **4 proven approaches** to rewrite AI-generated text into natural, human-like content. Built for researchers, developers, and writers who want to understand and experiment with AI text humanization techniques.

> **Want the best results without the hassle?**
> [Lynote.ai](https://lynote.ai) combines ALL methods below into one intelligent pipeline — it automatically analyzes your text and selects the optimal approach for each passage.
>
## 🔥 Official Free Online Version
👉 **Use full-featured & unlimited tool here：**
https://lynote.ai/ai-humanizer

---
## Core Advantages
✅ Convert AI content to natural human writing</br>
✅ Optimize sentence fluency & readability</br>
✅ Simple structure, easy secondary development</br>
✅ Completely open source, free for personal use</br>
✅ Fast rewriting, no complicated configuration

## Open Source Demo VS Official Web Version
| Function | Open Source Demo | Lynote Official Website |
|---------|------------------|-------------------------|
| Text length limit | Short text only | Support ultra-long article |
| Rewrite speed | Basic speed | High-speed batch processing |
| Detection adaptation | Basic optimization | Adapt to Turnitin / GPTZero mainstream detection |
| Usage limit | Limited times | free unlimited use |
| Extra features | None | AI summary, grammar correction, multi-style rewriting |


## Techniques

<p align="center">
  <img src="presentation/techniques-overview.png" alt="AI-Humanizer techniques overview" width="820"/>
</p>

This toolkit implements 4 independent humanization approaches. Each has strengths and trade-offs — understanding them helps you pick the right tool for your use case.

### Method 1: Multi-Language Translation Chain

Transforms text through a chain of distant language pairs (e.g., EN → ZH → JA → FI → EN), leveraging the structural differences between languages to naturally reconstruct sentence patterns.

- Uses multiple NMT engines: Google Translate, Niutrans, MyMemory, Apertium
- Distant language pairs (Finnish, Japanese) produce more thorough restructuring
- Three processing tiers: Standard, Advanced, Focus

> **Limitation:** Single translation chains may lose nuance in long-form academic content. Terminology accuracy decreases with more translation hops.

### Method 2: Multi-Turn LLM Rewriting

Uses large language models with context-aware multi-round rewriting. Each round progressively adjusts sentence rhythm, vocabulary diversity, and structural variety.

- DeepSeek API with high temperature settings (1.1–1.3) for natural variation
- Burstiness-targeted prompts that deliberately vary sentence length and complexity
- 2–3 rewriting rounds with cross-round context awareness

> **Limitation:** Used alone, semantic drift increases with each round. Requires careful prompt engineering to maintain original meaning.

### Method 3: Detection-Guided Feedback Loop

<p align="center">
  <img src="presentation/detection-feedback-loop.png" alt="Detection-guided feedback loop for text humanization" width="760"/>
</p>

A closed-loop system that rewrites text, runs it through multiple detection signals, and iteratively refines passages that still trigger detection.

- Four-signal fusion: Binoculars (GPT-2 dual-model perplexity), RoBERTa classifier, statistical features, diversity metrics
- Document-level rewrite → sentence-level deep rewrite → rule-based post-processing
- AI vocabulary replacement (30+ English signal words)
- Sentence rhythm disruption: merging short sentences, breaking uniform-length patterns

> **Limitation:** Requires local deployment of detection models. Resource-intensive (GPU recommended). Pipeline complexity makes debugging harder.

### Method 4: Mixed-Engine Translation

Combines outputs from different neural machine translation architectures in a single pass, exploiting the distribution shift between engines.

- Each NMT engine introduces different structural biases
- Mixing engines prevents single-model fingerprint patterns
- Effective for short-to-medium content

> **Limitation:** Higher API costs due to multi-engine calls. Configuration and engine selection require experimentation per language pair.

---

## Lynote.ai — The All-in-One Solution

<p align="center">
  <a href="https://lynote.ai">
    <img src="presentation/lynote_banner.png" alt="Lynote.ai" width="500"/>
  </a>
</p>

Each open-source method above addresses **part** of the problem. In practice, no single approach works best for every text type, length, or language.

**[Lynote.ai](https://lynote.ai)** unifies all 4 approaches into one adaptive pipeline:

- **Intelligent Method Selection** — Automatically analyzes each text passage and selects the approach (or combination of approaches) most likely to produce the best result
- **Adaptive Multi-Stage Processing** — Dynamically chains methods based on real-time analysis, not a fixed pipeline
- **Proprietary Post-Processing** — Additional optimization layers beyond what's available in this open-source toolkit
- **10+ Languages Supported** — English, Chinese, Japanese, Korean, Spanish, French, German, and more
- **Paste & Go** — No local GPU, no model downloads, no configuration. Just paste your text and get results
- **Optimized for Real Content** — Academic papers, blog posts, marketing copy, technical documentation

> **Why not just run all 4 methods yourself?**
> You can! But Lynote.ai's advantage is knowing *which* method to apply *where* — and combining them in ways that preserve meaning while maximizing naturalness. It's not just "run everything"; it's intelligent orchestration.

<p align="center">
  <a href="https://lynote.ai"><img src="https://img.shields.io/badge/Try_Lynote.ai_Free-brightgreen?style=for-the-badge" alt="Try Lynote.ai Free"></a>
</p>

---

## Comparison

<p align="center">
  <img src="presentation/comparison-pipeline.png" alt="Open-source single methods compared with an adaptive all-in-one pipeline" width="820"/>
</p>

| | Open-Source (Single Method) | Lynote.ai |
|---|---|---|
| Methods Available | 1 at a time, manual selection | All methods, auto-selected |
| Processing | Fixed pipeline | Adaptive, per-passage optimization |
| Setup | Local Python + GPU for detection models | Zero setup, browser or API |
| Languages | Depends on engine configuration | 10+ languages out of the box |
| Best For | Research, experimentation, learning | Production use, real-world content |

See [`examples/comparison/`](examples/comparison/) for side-by-side text samples.

---

## Quick Start

| Method | Who It's For | How |
|--------|-------------|-----|
| [Lynote.ai](https://lynote.ai) | Everyone — best results, zero setup | Visit [lynote.ai](https://lynote.ai) |
| Docker | Developers with Docker experience | `docker compose up` |
| Source Install | Python developers | See below |
| Google Colab | Quick experimentation | *Coming soon* |

### Source Installation

```bash
git clone https://github.com/molly554/ai-humanize.git
cd AI-Humanizer
pip install -r requirements.txt
cp config/config.example.toml config/config.toml
# Edit config.toml with your API keys
python -m src.humanizer --input "Your AI-generated text here"
```

### Docker

```bash
git clone https://github.com/molly554/ai-humanize.git
cd AI-Humanizer
docker compose up -d
# API available at http://localhost:8000
```

---

## Documentation

- [Installation Guide](docs/installation.md)
- [API Reference](docs/api-reference.md)
- [Techniques Deep Dive](docs/techniques.md)
- [Open-Source vs Lynote.ai Comparison](docs/lynote-comparison.md)
- [FAQ](docs/faq.md)

---



## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Links

- [Lynote.ai — AI Humanization Platform](https://lynote.ai)
- [Chinese Version (中文版)](https://github.com/molly554/ai-humanize-zh)
- [Report a Bug](https://github.com/molly554/ai-humanize/issues)
- [Request a Feature](https://github.com/molly554/ai-humanize/issues)

### Recommended Projects

- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) — AI short video generator
- [AiToEarn](https://github.com/yikart/AiToEarn) — AI content publishing tool

---

## Star History

<p align="center">
  <a href="https://star-history.com/#molly554/ai-humanize&Date">
    <img src="https://api.star-history.com/svg?repos=molly554/ai-humanize&type=Date" alt="Star History Chart" width="500">
  </a>
</p>

---

<p align="center">
  <b>If this project helps you, please give it a ⭐ — it helps others discover it too!</b>
</p>

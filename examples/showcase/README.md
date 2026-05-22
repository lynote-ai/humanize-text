# Pipeline Showcase — 5 Real Samples with Intermediate Step Outputs

This folder contains **5 end-to-end traces** of the Standard Pipeline (v1.5.1)
on real input texts. Each example shows the output of **all 4 intermediate steps**
plus the final AI-detection verdict.

## Samples

| # | Topic | Final Detection | Confidence |
|---|-------|-----------------|------------|
| [01](example_01.md) | Quantum Computing | `human` | 0.9997 |
| [02](example_02.md) | Quantum Readiness Strategy | `human` | 0.9982 |
| [03](example_03.md) | Sustainable Supply Chains | `human` | 0.7810 |
| [04](example_04.md) | Financial Literacy | `human` | 0.9924 |
| [05](example_05.md) | Peer Review in Science | `human` | 0.7218 |

All 5 samples were classified as `human` by the detector. Confidence is the
detector's probability that the text is human-written.

## Pipeline Chain (v1.5.1)

```
Input (EN)
    │
    ▼  Step 1: DeepSeek (temp 1.3)  ──  中文改写
    │
    ▼  Step 2: DeepSeek (temp 1.3)  ──  日语改写  (carries history)
    │
    ▼  Step 3: Google Translate     ──  一轮翻译 (JA → FI)
    │
    ▼  Step 4: Niutrans             ──  二轮翻译 (FI → EN)
    │
    ▼
Final Output (EN, humanized)
```

## How to Read an Example

Each `example_NN.md` file shows:

1. **Original Input** — the raw AI-generated English text
2. **Step 1 output** — Chinese humanization rewrite (DeepSeek)
3. **Step 2 output** — Japanese humanization rewrite (DeepSeek, history-aware)
4. **Step 3 output** — Finnish translation (Google)
5. **Step 4 output** — final English text (Niutrans)
6. **Detection verdict** — class + confidence

## Reproducing These Results

```bash
# Install deps
pip install -r requirements.txt

# Configure API keys
cp config/config.example.toml config/config.toml
# Fill in deepseek_api_key and niutrans_api_key

# Run on any sample's original text
python -m src.standard.pipeline \
  --input "Quantum computing has been proposed as..." \
  --target en \
  --verbose
```

The pipeline is non-deterministic at Steps 1–2 (DeepSeek temperature 1.3),
so your output will differ in wording while preserving meaning.

---

> **Want even higher confidence + style-adaptive selection?**
> [Lynote.ai](https://lynote.ai) combines Standard + Advanced + Focus pipelines
> and auto-selects the optimal approach per passage. Paste & go — no setup.

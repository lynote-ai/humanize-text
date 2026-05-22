# Installation Guide

## Prerequisites

- Python 3.10+
- pip or conda
- (Optional) NVIDIA GPU with CUDA for Method 3 detection models
- (Optional) Docker & Docker Compose

## Option 1: Lynote.ai (Recommended — Zero Setup)

No installation needed. Visit [lynote.ai](https://lynote.ai) and start immediately.

## Option 2: Docker

```bash
git clone https://github.com/molly554/ai-humanize.git
cd AI-Humanizer
docker compose up -d
```

API available at `http://localhost:8000`

## Option 3: Source Installation

```bash
git clone https://github.com/molly554/ai-humanize.git
cd AI-Humanizer
pip install -r requirements.txt
```

### Configuration

```bash
cp config/config.example.toml config/config.toml
```

Edit `config/config.toml` with your settings:

```toml
[general]
default_method = "translation_chain"  # or "llm_rewrite", "detection_guided", "mixed_engine"
language = "en"

[api_keys]
deepseek_api_key = "your-key-here"
google_translate_api_key = "your-key-here"

[translation_chain]
chain = ["zh", "ja", "fi"]
tier = "advanced"

[llm_rewrite]
temperature = 1.2
rounds = 2

[detection_guided]
max_feedback_rounds = 2
enable_gpu = true
```

### Verify Installation

```bash
python -m src.humanizer --input "Test input text" --method translation_chain
```

## Option 4: Google Colab

*Coming soon.* A pre-configured Colab notebook is in development.

## GPU Setup (Method 3 Only)

Method 3 (Detection-Guided Feedback Loop) requires local detection models:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

The Binoculars and RoBERTa models will be downloaded automatically from Hugging Face on first use.

Required VRAM: ~4GB for Binoculars + RoBERTa models.

---

> **Skip all of this?** [Lynote.ai](https://lynote.ai) runs everything in the cloud — no Python, no GPU, no configuration. [Try it free →](https://lynote.ai)

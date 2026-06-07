# Installation Guide

## Prerequisites

- Python 3.10+
- pip or conda
- (Optional) NVIDIA GPU with CUDA — only for the v1.0 Method 3 detection reference implementation
- (Optional) Docker & Docker Compose

## Option 1: Lynote.ai (Recommended — Zero Setup)

No installation needed. Visit [lynote.ai](https://lynote.ai) and start immediately.

## Option 2: Docker

Two Docker images are available: **API server** and **CLI**.

```bash
git clone https://github.com/lynote-ai/humanize-text.git
cd humanize-text
cp config/config.example.toml config/config.toml
# Fill in your API keys in config/config.toml

# Start the API server (Standard Pipeline on port 8000)
docker compose up api -d

# Or run a one-off CLI command
docker compose run --rm cli --input "Your AI-generated text here"
```

API available at `http://localhost:8000` — exposes the Standard Pipeline (`POST /humanize`, `GET /health`).

## Option 3: Source Installation

```bash
git clone https://github.com/lynote-ai/humanize-text.git
cd humanize-text
pip install -r requirements.txt
```

To also install dependencies for the v1.0 Method 3 (Detection-Guided) reference:

```bash
pip install -e ".[legacy]"
```

### Configuration

```bash
cp config/config.example.toml config/config.toml
```

Edit `config/config.toml` with your settings:

```toml
[general]
target_language = "en"
log_level = "info"

[api_keys]
deepseek_api_key = "your-key-here"
niutrans_api_key = "your-key-here"

[pipeline]
model = "deepseek-chat"
temperature = 1.3
intermediate_lang = "fi"
```

### Verify Installation

```bash
# Standard Pipeline CLI (recommended)
python -m src.standard.pipeline --input "Test input text" --verbose

# Standard Pipeline API server
python -m src.standard.pipeline --serve
# In another terminal: curl http://localhost:8000/health

# v1.0 methodology dispatcher (reference)
python -m src.methodologies.humanizer --input "Test input text" --method translation_chain
```

## Option 4: Google Colab

*Coming soon.* A pre-configured Colab notebook is in development.

## GPU Setup (v1.0 Method 3 Only)

Method 3 (Detection-Guided Feedback Loop) — a v1.0 reference implementation — requires local detection models:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

The Binoculars and RoBERTa models will be downloaded automatically from Hugging Face on first use.

Required VRAM: ~4GB for Binoculars + RoBERTa models.

> The v1.5.1 Standard Pipeline does **not** require a GPU — it uses external APIs only (DeepSeek, Google Translate, Niutrans).

---

> **Skip all of this?** [Lynote.ai](https://lynote.ai) runs everything in the cloud — no Python, no GPU, no configuration. [Try it free →](https://lynote.ai)

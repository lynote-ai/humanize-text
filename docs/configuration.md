# Configuration Guide

## Setup

```bash
cp config/config.example.toml config/config.toml
```

Edit `config/config.toml` with your API keys.

## Required API Keys

### LLM Provider (Steps 1-2)

The pipeline uses an OpenAI-compatible chat API. Choose a provider in `[llm]`:

#### DeepSeek (default)

1. Go to [platform.deepseek.com](https://platform.deepseek.com)
2. Create an account and generate an API key
3. Add to config: `deepseek_api_key = "sk-..."`

#### OpenRouter (optional)

OpenRouter exposes many models via a single OpenAI-compatible endpoint.

1. Go to [openrouter.ai](https://openrouter.ai)
2. Create an account and generate an API key
3. Configure:

```toml
[api_keys]
openrouter_api_key = "sk-or-..."

[llm]
provider = "openrouter"
model = "deepseek/deepseek-chat"   # or anthropic/claude-3.5-sonnet, etc.
```

#### Atlas Cloud (optional)

Atlas Cloud exposes LLMs through an OpenAI-compatible endpoint.

```toml
[api_keys]
atlascloud_api_key = "ak-..."

[llm]
provider = "atlascloud"
model = "qwen/qwen3.5-flash"
```

#### Provider defaults

| Provider | Default `base_url` | Default `model` | Config key |
|----------|-------------------|-----------------|------------|
| `deepseek` | `https://api.deepseek.com` | `deepseek-chat` | `api_keys.deepseek_api_key` |
| `openrouter` | `https://openrouter.ai/api/v1` | `deepseek/deepseek-chat` | `api_keys.openrouter_api_key` |
| `atlascloud` | `https://api.atlascloud.ai/v1` | `qwen/qwen3.5-flash` | `api_keys.atlascloud_api_key` |

Set `base_url` in `[llm]` to override the provider preset (e.g. a self-hosted OpenAI-compatible proxy). Leave empty to use the default for the selected provider.

**Custom endpoint example:**

```toml
[llm]
provider = "openrouter"
base_url = "https://my-proxy.example.com/v1"
model = "deepseek/deepseek-chat"
```

### Niutrans API Key

Used for Steps 4-5 (translation).

1. Go to [niutrans.com](https://niutrans.com)
2. Register and get a free API key (free tier available)
3. Add to config: `niutrans_api_key = "your-key"`

## Configuration Options

```toml
[general]
target_language = "en"    # Final output language
log_level = "info"        # debug, info, warning, error

[api_keys]
deepseek_api_key = ""     # Required when llm.provider = "deepseek"
openrouter_api_key = ""   # Required when llm.provider = "openrouter"
atlascloud_api_key = ""   # Required when llm.provider = "atlascloud"
niutrans_api_key = ""     # Required

[llm]
provider = "deepseek"     # "deepseek" | "openrouter" | "atlascloud"
base_url = ""             # empty = provider default; set to override
model = ""                # empty = provider default model
temperature = 1.3         # 1.1-1.5 range (1.3 recommended)
http_referer = ""         # OpenRouter optional attribution
app_title = ""            # OpenRouter optional attribution

[pipeline]
model = "deepseek-chat"   # Fallback if [llm].model is empty
temperature = 1.3
intermediate_lang = "fi"
```

## Environment Variable Overrides

Optional runtime overrides (take precedence over TOML):

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `deepseek`, `openrouter`, or `atlascloud` |
| `LLM_BASE_URL` | Override API base URL |
| `LLM_API_KEY` | Generic API key override |
| `OPENROUTER_API_KEY` | OpenRouter key when provider is `openrouter` |
| `DEEPSEEK_API_KEY` | DeepSeek key when provider is `deepseek` |
| `ATLASCLOUD_API_KEY` | Atlas Cloud key when provider is `atlascloud` |
| `LLM_MODEL` | Override model slug |

**Example — switch to OpenRouter via environment (no TOML edit):**

```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=sk-or-...
export LLM_MODEL=deepseek/deepseek-chat
python -m src.standard.pipeline --input "Your text here"
```

## Supported Target Languages

| Code | Language |
|------|----------|
| en | English |
| zh | Chinese |
| ja | Japanese |
| ko | Korean |
| fr | French |
| de | German |
| es | Spanish |
| pt | Portuguese |
| ru | Russian |
| ar | Arabic |
| it | Italian |
| nl | Dutch |

# Configuration Guide

## Setup

```bash
cp config/config.example.toml config/config.toml
```

Edit `config/config.toml` with your API keys.

## Required API Keys

### DeepSeek API Key

Used for Steps 1-2 (LLM humanization rewrite).

1. Go to [platform.deepseek.com](https://platform.deepseek.com)
2. Create an account and generate an API key
3. Add to config: `deepseek_api_key = "sk-..."`

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
deepseek_api_key = ""     # Required
niutrans_api_key = ""     # Required

[pipeline]
model = "deepseek-chat"   # DeepSeek model
temperature = 1.3         # 1.1-1.5 range (1.3 recommended)
chain = ["zh", "ja", "de", "es"]  # Language chain
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

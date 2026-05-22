# API Reference

## CLI Usage

```bash
python -m src.humanizer [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--input` | string | required | Input text or path to text file |
| `--method` | string | `translation_chain` | Method: `translation_chain`, `llm_rewrite`, `detection_guided`, `mixed_engine` |
| `--output` | string | stdout | Output file path |
| `--language` | string | `en` | Target language code |
| `--tier` | string | `standard` | Processing tier: `standard`, `advanced`, `focus` |
| `--config` | string | `config/config.toml` | Path to config file |

### Examples

```bash
# Basic usage
python -m src.humanizer --input "Your AI text here"

# Use specific method
python -m src.humanizer --input input.txt --method llm_rewrite --output result.txt

# Advanced tier translation chain
python -m src.humanizer --input input.txt --method translation_chain --tier advanced

# Detection-guided with custom config
python -m src.humanizer --input input.txt --method detection_guided --config my_config.toml
```

## Python API

```python
from src.humanizer import Humanizer

h = Humanizer(config_path="config/config.toml")

# Single method
result = h.process("Your AI text here", method="translation_chain")

# With options
result = h.process(
    text="Your AI text here",
    method="llm_rewrite",
    temperature=1.2,
    rounds=3
)

print(result.text)
print(result.method_used)
print(result.processing_time)
```

## REST API (Docker)

When running via Docker, the API is available at `http://localhost:8000`.

### POST /humanize

```bash
curl -X POST http://localhost:8000/humanize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your AI text here",
    "method": "translation_chain",
    "language": "en",
    "tier": "advanced"
  }'
```

**Response:**

```json
{
  "result": "Humanized text output...",
  "method": "translation_chain",
  "processing_time_ms": 2340
}
```

### GET /methods

Returns available methods and their configurations.

### GET /health

Health check endpoint.

---

> **Want a managed API with intelligent method selection?** [Lynote.ai API](https://lynote.ai) handles method selection automatically. [Learn more →](https://lynote.ai)

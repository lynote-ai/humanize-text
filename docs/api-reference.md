# API Reference

> Two entry points are available:
>
> - **`src.standard.pipeline`** — v1.5.1 production Standard Pipeline (recommended)
> - **`src.methodologies.humanizer`** — v1.0 multi-method dispatcher (reference)

---

## Standard Pipeline (v1.5.1, recommended)

### CLI

```bash
python -m src.standard.pipeline [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--input` | string | required | Input text or path to text file |
| `--target` | string | `en` | Target language code |
| `--config` | string | `config/config.toml` | Path to config file |
| `--output` | string | stdout | Output file path |
| `--verbose` | flag | off | Show step-by-step progress |

**Examples:**

```bash
# Basic usage
python -m src.standard.pipeline --input "Your AI text here"

# With verbose step tracing
python -m src.standard.pipeline --input input.txt --output result.txt --verbose

# Different target language
python -m src.standard.pipeline --input input.txt --target zh
```

### Python API

```python
from src.standard import run_standard_pipeline
import toml

config = toml.load("config/config.toml")
result = run_standard_pipeline(
    text="Your AI text here",
    config=config,
    target_lang="en",
)

print(result["result"])               # final humanized text
print(result["processing_time_ms"])    # total elapsed time
for step in result["steps"]:
    print(step["step"], step["engine"], step["direction"], step["length"])
```

---

## v1.0 Methodology Dispatcher (reference)

### CLI

```bash
python -m src.methodologies.humanizer [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--input` | string | required | Input text or path to text file |
| `--method` | string | `translation_chain` | `translation_chain`, `llm_rewrite`, `detection_guided`, `mixed_engine` |
| `--output` | string | stdout | Output file path |
| `--language` | string | `en` | Target language code |
| `--tier` | string | `standard` | Processing tier |
| `--config` | string | `config/config.toml` | Path to config file |
| `--serve` | flag | off | Start FastAPI server on port 8000 |

**Examples:**

```bash
# Basic usage with a methodology
python -m src.methodologies.humanizer --input "Your AI text here" --method llm_rewrite

# Detection-guided with custom config
python -m src.methodologies.humanizer --input input.txt --method detection_guided --config my_config.toml
```

### Python API

```python
from src.methodologies.humanizer import Humanizer

h = Humanizer(config_path="config/config.toml")
result = h.process("Your AI text here", method="translation_chain")
print(result.text)
```

### REST API (Docker)

When running via Docker, the v1.0 dispatcher's FastAPI app is exposed at `http://localhost:8000`.

```bash
curl -X POST http://localhost:8000/humanize \
  -H "Content-Type: application/json" \
  -d '{"text": "Your AI text here", "method": "translation_chain"}'
```

Endpoints:

- `POST /humanize` — run a methodology
- `GET /methods` — list available methodologies
- `GET /health` — health check

---

> **Want a managed API with intelligent tier selection?** [Lynote.ai](https://lynote.ai) handles tier selection automatically. Paste & go.

# Legacy Examples (v1.0)

These examples target the **v1.0 four-methodology reference implementations**
(`src/methodologies/humanizer.py`, `src/methodologies/translation_chain.py`,
`src/methodologies/detection_pipeline.py`, `src/methodologies/mixed_engine.py`). They are kept for users studying the original
methodologies.

For the **v1.5.1 production Standard Pipeline**, see:

- `examples/example_usage.py` — minimal Python entry
- `examples/showcase/` — 5 real samples with intermediate step outputs

## Files

- `basic_usage.py` — single-text run via the v1.0 `Humanizer` dispatcher
- `batch_process.py` — batch loop over multiple inputs
- `comparison/` — pre-generated output text for each of the 4 methodologies
  on a shared input, plus a Lynote.ai reference output

## Note on dependencies

The v1.0 detection-guided method (Method 3) requires extra dependencies
(`transformers`, `torch`, `nltk`, `langdetect`). Install them with:

```bash
pip install -e ".[legacy]"
```

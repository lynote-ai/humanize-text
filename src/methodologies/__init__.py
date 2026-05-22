"""v1.0 Humanization Methodologies (reference implementations).

This package contains the four original humanization methodologies we explored
in v1.0. They are kept here as **reference implementations** for research,
education, and customization.

For production use, see `src.standard` (the v1.5.1 Standard Pipeline).

Methodologies:
    - Method 1: Translation Chain (`translation_chain.py`)
    - Method 2: Multi-Turn LLM Rewriting (`llm_rewriter.py`)
    - Method 3: Detection-Guided Feedback Loop (`detection_pipeline.py`)
    - Method 4: Mixed-Engine Translation (`mixed_engine.py`)

The `humanizer.py` module exposes a dispatcher (`Humanizer` class) and a
FastAPI app that routes between these four methodologies.

Note on dependencies: Method 3 requires `transformers` and `torch`. Install
with `pip install -e ".[legacy]"` to get those extras.
"""

__all__ = []

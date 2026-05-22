"""Smoke tests — no API keys required.

These tests verify that the package layout is sane: modules import, the
public surface is what we documented, and pure helpers behave correctly.
They do NOT make any network calls.

Run with:
    pytest tests/ -v
"""

import importlib

import pytest


# -----------------------------------------------------------------------------
# Package layout: importability of v1.5.1 standard + v1.0 methodologies
# -----------------------------------------------------------------------------

def test_version_string_is_set():
    import src
    assert hasattr(src, "__version__")
    assert isinstance(src.__version__, str)
    assert src.__version__.count(".") == 2  # semver: MAJOR.MINOR.PATCH


def test_standard_package_public_surface():
    from src.standard import (
        run_standard_pipeline,
        deepseek_rewrite,
        google_translate,
        niutrans_translate,
    )
    # All four must be callable
    assert callable(run_standard_pipeline)
    assert callable(deepseek_rewrite)
    assert callable(google_translate)
    assert callable(niutrans_translate)


@pytest.mark.parametrize("module_name", [
    "src.methodologies.humanizer",
    "src.methodologies.translation_chain",
    "src.methodologies.llm_rewriter",
    "src.methodologies.mixed_engine",
])
def test_methodologies_modules_import(module_name):
    """v1.0 reference modules should import without errors.

    Method 3 (detection_pipeline) is excluded — it depends on `transformers`
    and `torch`, which are optional (`pip install -e ".[legacy]"`).
    """
    importlib.import_module(module_name)


def test_humanizer_dispatcher_has_four_methods():
    from src.methodologies.humanizer import Humanizer
    assert set(Humanizer.METHODS.keys()) == {
        "translation_chain",
        "llm_rewrite",
        "detection_guided",
        "mixed_engine",
    }


# -----------------------------------------------------------------------------
# Pure-function unit tests (no network)
# -----------------------------------------------------------------------------

def test_lang_code_mapping_known_codes():
    from src.standard.pipeline import _lang_code_to_niutrans
    assert _lang_code_to_niutrans("en") == "en"
    assert _lang_code_to_niutrans("zh") == "zh"
    assert _lang_code_to_niutrans("fi") == "fi"


def test_lang_code_mapping_passthrough_for_unknown():
    from src.standard.pipeline import _lang_code_to_niutrans
    assert _lang_code_to_niutrans("xx") == "xx"


def test_split_text_respects_max_length():
    from src.standard.translators import _split_text
    sentence = "This is a test sentence. " * 200  # ~5000 chars
    chunks = _split_text(sentence, max_len=1000)
    assert all(len(c) <= 1100 for c in chunks)  # tolerance for sentence boundary
    assert "".join(c.replace(" ", "") for c in chunks) != ""  # not empty


def test_split_text_short_input_single_chunk():
    from src.standard.translators import _split_text
    short = "One sentence."
    chunks = _split_text(short, max_len=4500)
    assert chunks == [short]


# -----------------------------------------------------------------------------
# Showcase examples integrity
# -----------------------------------------------------------------------------

def test_showcase_examples_exist():
    """The 5 showcase markdowns should all be present and non-trivial."""
    from pathlib import Path
    showcase_dir = Path(__file__).parent.parent / "examples" / "showcase"
    assert showcase_dir.is_dir()
    examples = sorted(showcase_dir.glob("example_*.md"))
    assert len(examples) == 5, f"Expected 5 examples, found {len(examples)}"
    for ex in examples:
        text = ex.read_text(encoding="utf-8")
        # Each example must show all 4 intermediate steps
        assert "Step 1" in text
        assert "Step 2" in text
        assert "Step 3" in text
        assert "Step 4" in text
        # And a detection verdict
        assert "human" in text.lower()

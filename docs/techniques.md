# AI Humanization Methodologies (v1.0) — Reference

> **Positioning:** This document covers the **4 humanization methodologies** we originally explored in v1.0. They remain in `src/` as **reference implementations** for research, education, and customization.
>
> For the **production path**, see the [Standard Pipeline](pipeline.md) added in v1.5 — it integrates Method 1 (Translation Chain) + Method 2 (LLM Rewriting) into a fixed 5-step chain we actually run.
>
> For the **complete solution** (Standard + Advanced + Focus tiers, auto-selected per passage), see [Lynote.ai](https://lynote.ai).

This document provides a detailed technical explanation of the 4 humanization methodologies.

---

## Method 1: Multi-Language Translation Chain

### Principle

AI-generated text carries statistical fingerprints — predictable token distributions, uniform sentence lengths, and repetitive n-gram patterns. Neural machine translation (NMT) engines restructure text at a fundamental level: word order changes, grammar transforms, and vocabulary shifts.

By chaining translations through **distant language pairs**, each hop introduces structural disruption that progressively dismantles these fingerprints.

### How It Works

```
Original (EN) → Chinese → Japanese → Finnish → Back to English
```

Each language introduces unique structural transformations:
- **Chinese:** Subject-verb-object reordering, removal of articles
- **Japanese:** SOV word order, particle-based grammar
- **Finnish:** Agglutinative morphology, 15 grammatical cases

The cumulative effect produces English text with naturally varied sentence structures.

### Engine Selection

| Engine | Strength | Best For |
|--------|----------|----------|
| Google Translate | Highest fluency | General content |
| Niutrans | Academic terminology | Research papers |
| MyMemory | Translation memory integration | Repetitive content |
| Apertium | Rule-based, predictable transforms | Short-form content |

### Processing Tiers

- **Standard:** 3-language chain (EN → ZH → JA → EN)
- **Advanced:** 4-language chain with mixed engines
- **Focus:** 5-language chain with post-processing refinement

### Limitations

- Terminology accuracy decreases with each translation hop
- Cultural idioms may be lost or awkwardly reconstructed
- Long academic texts (5000+ words) may show inconsistent quality across sections

---

## Method 2: Multi-Turn LLM Rewriting

### Principle

AI detectors identify text through statistical uniformity — even token probability, consistent sentence length, and predictable vocabulary. Multi-turn LLM rewriting uses a language model to progressively inject natural variation while maintaining semantic fidelity.

### How It Works

**Round 1 — Structural Variation:**
- Rewrite with focus on sentence length diversity (burstiness)
- Alternate between short (3–8 words) and long (25–40 words) sentences
- Introduce paragraph-level structural changes

**Round 2 — Vocabulary & Style:**
- Replace formal/AI-typical vocabulary with natural alternatives
- Add colloquial expressions where appropriate
- Introduce rhetorical devices (questions, asides, qualifiers)

**Round 3 (Optional) — Context Refinement:**
- Cross-reference with original for semantic accuracy
- Fine-tune transitions and logical flow
- Final naturalness pass

### Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Temperature | 1.1–1.3 | Increases output randomness beyond typical generation |
| Top-p | 0.9 | Allows diverse token selection |
| Rounds | 2–3 | Balance between variation and semantic preservation |

### Prompt Strategy

Burstiness-targeted prompts explicitly instruct the model to:
- Vary sentence lengths dramatically within paragraphs
- Use concrete examples instead of abstract statements
- Break uniform rhythm patterns that AI detectors flag

### Limitations

- Semantic drift accumulates across rounds — meaning may shift subtly
- Requires API access to capable LLMs (DeepSeek, GPT-4, Claude)
- Processing time scales linearly with round count
- Without detection feedback, it's hard to know when "enough" rewriting has been done

---

## Method 3: Detection-Guided Feedback Loop

### Principle

Rather than blindly rewriting, this method creates a closed-loop system: rewrite → detect → identify weak spots → re-rewrite. It uses multiple detection signals to find passages that still appear AI-generated and targets them specifically.

### Architecture

```
Input Text
    ↓
Language Detection
    ↓
Document-Level Rewrite (LLM)
    ↓
Sentence Segmentation
    ↓
Multi-Signal Detection ←──────────┐
    ↓                              │
Identify Flagged Sentences         │
    ↓                              │
Sentence-Level Deep Rewrite        │
    ↓                              │
Rule-Based Post-Processing         │
    ↓                              │
Re-Detection ──── Still flagged? ──┘
    ↓ (pass)
Output
```

### Detection Signals

1. **Binoculars:** Uses GPT-2 with two different decoding heads to measure perplexity ratio. Low ratio = likely AI-generated.
2. **RoBERTa Classifier:** Fine-tuned binary classifier on AI vs. human text datasets.
3. **Statistical Features:** Sentence length variance, vocabulary richness (TTR), n-gram diversity.
4. **Diversity Metrics:** Unique token ratio, hapax legomena count, Yule's K measure.

### Post-Processing Rules

**AI Vocabulary Replacement:**
- 30+ English signal words (e.g., "utilize" → "use", "facilitate" → "help", "comprehensive" → "full")
- 11+ Chinese boilerplate phrases with natural alternatives

**Sentence Rhythm Disruption:**
- Merge consecutive short sentences (< 8 words each) into compound sentences
- Detect and break 3+ sentence uniform-length patterns
- Insert transitional variety (short interjection, question, aside)

### Limitations

- Requires local deployment of Binoculars + RoBERTa models (GPU recommended)
- Detection models may not correlate with commercial detectors (GPTZero, Originality.ai)
- Maximum 2 feedback rounds to avoid over-processing
- Pipeline complexity makes customization and debugging challenging

---

## Method 4: Mixed-Engine Translation

### Principle

Different NMT engines are trained on different data with different architectures, producing systematically different outputs for the same input. By combining outputs from multiple engines, the result doesn't match the fingerprint of any single model — exploiting what's called "distribution shift."

### How It Works

1. Send source text to 2–3 different NMT engines simultaneously
2. Segment outputs at sentence or clause level
3. Select the best segment from each engine based on:
   - Naturalness scoring
   - Vocabulary diversity
   - Structural difference from the original
4. Merge selected segments into final output

### Engine Combinations

| Combination | Character |
|-------------|-----------|
| Google + DeepL | High fluency, natural phrasing |
| Niutrans + Apertium | Academic accuracy + structural variety |
| Google + MyMemory + Apertium | Maximum diversity, three-way merge |

### Limitations

- API costs multiply with each additional engine
- Segment boundaries may produce awkward transitions
- Engine selection matters — random combinations don't always improve results
- Most effective for short-to-medium content (< 2000 words)

---

## Which Method Should You Use?

| Content Type | Recommended Method | Why |
|-------------|-------------------|-----|
| Short social posts | Method 1 (Translation Chain) | Fast, sufficient for informal content |
| Blog articles | Method 2 (LLM Rewriting) | Preserves voice and style best |
| Academic papers | Method 3 (Detection-Guided) | Highest precision, handles technical vocabulary |
| Product descriptions | Method 4 (Mixed-Engine) | Good balance of speed and variety |
| **Any content** | **[Lynote.ai](https://lynote.ai)** | **Automatically selects the best method for each passage** |

---

> **Why settle for one method?** [Lynote.ai](https://lynote.ai) analyzes your text and intelligently selects — or combines — the optimal approach for each section. No configuration, no GPU, no guesswork. [Try it free →](https://lynote.ai)

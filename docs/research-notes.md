# Research Notes: what actually separates human and AI writing

Short field notes on the detection research that shapes how we think about
humanization — why surface-level rewriting has a ceiling, and where the
durable signal actually lives. These are our reading notes, not the authors'
claims; see the primary source for the authoritative version.

**Primary source:** *StoryScope: Investigating idiosyncrasies in AI fiction* —
Russell, Rajendhran, Pham, Iyyer (UMD) & Wieting (Google DeepMind), COLM 2026.

- Paper: <https://arxiv.org/abs/2604.03136>
- Code & data (10,272 prompts · 61,608 stories · per-story narrative features): <https://github.com/jenna-russell/storyscope>

---

## TL;DR

Most detectors key on **surface style** — word choice, sentence rhythm,
em-dashes. Style is highly discriminative but **brittle**: it can be rewritten
away. StoryScope isolates a second, **structural** signal that survives style
edits — *discourse-level narrative features* (plot shape, character agency,
temporal structure). That is the part a translation chain or a paraphrase
cannot launder.

| Detection signal | Macro-F1 (human vs AI) | Survives style edits? |
|---|---|---|
| Full-text baseline (ModernBERT) | 99.9% | No — brittle to paraphrase |
| Style features only | 85.8% | No |
| **Narrative features only (no style)** | **93.2%** | **Yes** |
| Narrative features, on style-rewritten stories (LAMP) | 93.9% | — |
| Narrative, compact 30-feature core | 84.8% | Yes |

Two numbers worth internalizing:

- Fine-tuning a model to mimic human **style** drops creative-writing AI
  detection from **97% → 3%** (Chakrabarty et al., 2026). Style laundering
  works — against style detectors.
- A **narrative-feature** classifier still catches those same style-laundered
  stories at **93.9%**. Structure does not launder.

## Why style-only humanization has a ceiling

This repo's Standard Pipeline (LLM rewrite ×2 + NMT ×2) is fundamentally a
**style / lexical transform**: it changes surface tokens and phrasing, and the
translation hops perturb sentence structure. It does **not** restructure the
narrative — plot stays single-track, themes stay over-explained, chronology
stays linear. Against a style detector that is plenty. Against a
narrative-level detector the underlying structure is unchanged and still
fingerprintable. That is the concrete reason a pure translate-and-reword chain
plateaus.

## The durable signal: how human and AI narratives differ

Across five models (Claude, DeepSeek, Gemini, GPT, Kimi), AI stories converge
into a **tight, shared region** of narrative space; human stories are more
diverse and statistically rarer (mean rarity percentile 0.71 human vs 0.49
AI). Concretely, human writing tends to:

- integrate subplots into the central theme more often (42% vs 21%)
- give protagonists morally ambiguous choices more often (59% vs 38%)
- use more locations, more dialogue relative to narration, and nonlinear
  time (flashbacks, discontinuity)

AI writing tends to over-explain themes and favor tidy, single-track
resolution. Each model also carries a **fingerprint** useful for attribution —
e.g. Claude → flat event escalation, GPT → gossip as a plot device, Gemini →
external character description.

## Implications for this project

- **Humanize side:** to move past a style detector's ceiling, edits have to
  reach the **structural** layer — reorder chronology, build real subplot /
  theme interplay, introduce moral ambiguity — not just swap vocabulary. This
  is why serious work here is model-based, not rule- or translation-based.
- **Detect side:** narrative-structure features are a strong, style-robust
  axis to train on. They degrade gracefully as base models evolve, because
  they capture *what the model decides*, not *how it phrases things*.

> **Scope caveat.** StoryScope studies long-form fiction (~5,000-word
> stories); the exact feature list does not transfer 1:1 to short or
> non-narrative text. What generalizes is the **style-vs-structure
> distinction**, not the specific features.

---

*Lynote.ai's detection work builds on this line of research. For the current
humanizer and detector, see [Lynote.ai](https://lynote.ai).*

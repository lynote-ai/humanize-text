# Architecture

[Chinese](ARCHITECTURE.zh-CN.md)

The source-specific intake, merge, split, Prompt assignment, and KTO construction methodology is documented in [DATA_CONSTRUCTION.md](DATA_CONSTRUCTION.md).

## Stage contracts

```mermaid
flowchart LR
    source["Registered SFT bundle"] --> A["A · Reserve SFT for KTO"]
    policy["YAML policies"] --> A
    manifest["manifest.yaml"] --> A
    A --> reservation["Reservation bundle"]
    reservation --> B["B · Validate reservation"]
    reservation --> C["C · Generate candidates"]
    C --> candidates["Aligned candidate bundle"]
    reservation --> D["D · Select negatives"]
    candidates --> D
    D --> kto["Balanced KTO bundle"]
    kto --> E["E · Validate KTO"]
    reservation --> F["F · Build structure-first refresh"]
    candidates --> F
    F --> refresh["Structure-first KTO bundle"]
    manifest --> B
    manifest --> C
    manifest --> D
    manifest --> E
    manifest --> F
```

| Stage | Module | Input | Output | Primary invariant |
|---|---|---|---|---|
| A. Reservation | `a_reserve_sft_for_kto.py` | SFT train, validation, sample index, reservation policy | retained SFT splits, KTO seeds, partition index | SFT and KTO inputs are disjoint; validation is unchanged |
| B. Reservation validation | `b_validate_sft_kto_reservation.py` | reservation bundle and upstream registration | validation report | counts, hashes, quotas, schemas, and disjointness match |
| C. Candidate generation | `c_generate_kto_candidates.py` | KTO seeds and explicit remote endpoint | aligned multi-round candidates | one deterministic identity record per input; resumable prefix only |
| D. Negative selection | `d_select_kto_negatives.py` | seeds, candidates, selector policy | balanced KTO rows, sample index, review sample | one positive and one mechanically supported negative per input |
| E. KTO validation | `e_validate_kto_dataset.py` | selected KTO bundle | validation report | labels, pair identities, negative types, counts, and hashes match |
| F. Structure refresh | `f_build_structure_first_kto_refresh.py` | seeds, six candidate chains, refresh policy | 60/20/20 KTO bundle | exact negative mixture and explicit fallback provenance |

## Design choices

- **Streaming JSONL**: dataset readers iterate line by line so memory use is bounded.
- **Stable selection**: seeded SHA-256 ordering provides reproducible sampling without depending on input loading order.
- **Versioned policy**: thresholds and quotas live in YAML instead of being hidden in recipes.
- **Controlled Prompt diversity**: wording variants are generated ahead of time and assigned per sample through seeded pseudo-random sampling; the task contract does not change.
- **Two-layer validation**: builders validate inputs while independent validators re-check output schemas, counts, identities, hashes, and manifest registration.
- **Human gate**: mechanical classification helps surface candidates; it does not replace semantic review.
- **Safe remote calls**: generation has no default endpoint and requires two explicit authorization flags.
- **Bounded release data**: `demo-validate` requires five known JSONL files, exactly 50 records each, and rejects extra files.

## Data identity

Records retain normalized SHA-256 identifiers for the AI source, human target, and source-target pair. Candidate and KTO stages verify these fields before joining records, avoiding positional joins that could silently mix examples.

```mermaid
flowchart LR
    source_text["AI source text"] --> source_norm["Normalize"] --> source_hash["source_sha256"]
    target_text["Human target text"] --> target_norm["Normalize"] --> target_hash["target_sha256"]
    source_hash --> pair_hash["pair_sha256"]
    target_hash --> pair_hash
    source_hash --> index["Sample index"]
    target_hash --> index
    pair_hash --> index
    index --> seeds["KTO seeds"] --> candidates["Candidate rows"] --> kto["KTO pairs"]
    validators["Independent validators"] -.-> index
    validators -.-> candidates
    validators -.-> kto
```

## What remains external

Full source data, model weights, the OpenAI-compatible generation service, training infrastructure, and human-review decisions remain outside this repository. Their identities and parameters must be supplied explicitly for a full run.

The Prompt methodology and five public examples are documented in [PROMPTS.md](PROMPTS.md).

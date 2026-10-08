# Demo data

[Chinese](README.zh-CN.md)

Only the `demos/` subtree is intended for publication. It contains exactly 50 JSONL records for each of the five public pipeline stages. `demos/manifest.yaml` pins the paths, counts, selection policy, and SHA-256 hashes.

Where a source field is present, `crawl` means public open-source data and `private` means internal company data. Internal dataset names and source-specific identifiers are not published.

## Schemas

- `01_sft`: three-message SFT rows (`system`, `user`, `assistant`).
- `02_reservation`: two-message generation prompts plus the held-out desirable response and identity hashes.
- `03_generation`: input identity plus six candidate chains and their generation metadata.
- `04_negative_selection`: three-message KTO rows with a Boolean `label`.
- `05_structure_refresh`: three-message KTO rows with a Boolean `label`, built from the structure-first policy.

System Prompts remain in the records as originally assigned. Their seeded random sampling method and five representative examples are documented in [the Prompt design document](../docs/PROMPTS.md).

## Release guard

Run:

```bash
make demo-validate
```

The validator fails if a stage is missing, a file has anything other than 50 records, a hash changes without updating the manifest, JSON is invalid, or an extra JSONL file appears under `data/demos`.

Before publishing to GitHub, a human must still review the 250 demo records for source licensing, personal or confidential information, and redistribution rights. The automated guard limits volume and checks integrity; it does not make a legal or privacy determination.

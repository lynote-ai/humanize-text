"""Export bounded public demo datasets from a complete source artifact."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

import yaml


DEMO_RECORD_LIMIT = 50

DEMO_SOURCES = (
    (
        "01_sft/sft_train_demo.jsonl",
        "data/train/sft_kto_reservation_20260916_155642/sft_train.jsonl",
        "Retained SFT training records after KTO reservation",
    ),
    (
        "02_reservation/kto_seed_demo.jsonl",
        "data/train/sft_kto_reservation_20260916_155642/kto_train_seed.jsonl",
        "Reserved inputs with held-out desirable responses",
    ),
    (
        "03_generation/kto_candidates_demo.jsonl",
        "data/train/sft_kto_reservation_20260916_155642/kto_train_candidates.jsonl",
        "Generated rewrite candidates aligned with reservation seeds",
    ),
    (
        "04_negative_selection/kto_train_demo.jsonl",
        "data/train/sft_heldout_kto_20260917_114400/train.jsonl",
        "Balanced desirable and undesirable KTO rows",
    ),
    (
        "05_structure_refresh/kto_train_demo.jsonl",
        "data/train/sft_humanize_structure_kto_20260917_173737/train.jsonl",
        "Structure-first refreshed KTO rows",
    ),
)


def parse_args() -> argparse.Namespace:
    """Parse the source snapshot and release destination paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact-dir", required=True, type=Path)
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--internal-source-name", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for one file."""
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_demo(
    source_path: Path,
    destination_path: Path,
    internal_source_name: str,
) -> int:
    """Stream exactly the first 50 valid JSON mappings into one demo file."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with source_path.open("r", encoding="utf-8") as input_file, destination_path.open(
        "w", encoding="utf-8"
    ) as output_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                raise ValueError(f"blank source line at {source_path}:{line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid JSON at {source_path}:{line_number}: {error}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(f"record must be a mapping at {source_path}:{line_number}")
            record = sanitize_public_metadata(record, internal_source_name)
            output_file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            output_file.write("\n")
            written += 1
            if written == DEMO_RECORD_LIMIT:
                break
    if written != DEMO_RECORD_LIMIT:
        raise ValueError(
            f"{source_path} contains {written} records; {DEMO_RECORD_LIMIT} are required"
        )
    return written


def sanitize_public_metadata(
    record: dict[str, object],
    internal_source_name: str,
) -> dict[str, object]:
    """Replace internal source labels in public metadata without editing text content."""
    sanitized = dict(record)
    if sanitized.get("source") == internal_source_name:
        sanitized["source"] = "private"
    for field in ("input_id", "sample_id"):
        value = sanitized.get(field)
        if isinstance(value, str):
            sanitized[field] = value.replace(
                f"{internal_source_name}:", "private:"
            ).replace(
                f"{internal_source_name}-", "private-"
            )
    return sanitized


def main() -> int:
    """Create the bounded, reproducible open-source snapshot."""
    args = parse_args()
    source_root = args.source_artifact_dir.resolve()
    project_root = args.project_dir.resolve()
    print("target: demo-export")
    print(f"source_artifact_dir: {source_root}")
    print(f"project_dir: {project_root}")
    print(f"started_at: {datetime.now().astimezone().isoformat()}")
    try:
        if not (source_root / "manifest.yaml").is_file():
            raise ValueError(f"source artifact manifest is missing: {source_root}")
        if not args.internal_source_name.strip():
            raise ValueError("internal source name must be non-empty")
        demo_entries: list[dict[str, object]] = []
        demo_root = project_root / "data" / "demos"
        for destination, source, description in DEMO_SOURCES:
            source_path = source_root / source
            if not source_path.is_file():
                raise ValueError(f"demo source is missing: {source_path}")
            destination_path = demo_root / destination
            record_count = export_demo(
                source_path,
                destination_path,
                args.internal_source_name,
            )
            demo_entries.append(
                {
                    "stage": destination.split("/", 1)[0],
                    "description": description,
                    "path": str(destination_path.relative_to(project_root)),
                    "record_count": record_count,
                    "sha256": sha256_file(destination_path),
                }
            )

        demo_manifest = {
            "schema_version": 1,
            "record_limit_per_stage": DEMO_RECORD_LIMIT,
            "selection_policy": "first-50-aligned-records-from-the-source-artifact",
            "stages": demo_entries,
        }
        manifest_path = demo_root / "manifest.yaml"
        with manifest_path.open("w", encoding="utf-8") as output_file:
            yaml.safe_dump(demo_manifest, output_file, allow_unicode=True, sort_keys=False)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        print("status: failed")
        print(f"error: {error}")
        return 2
    print(f"demo_stage_count: {len(DEMO_SOURCES)}")
    print(f"records_per_stage: {DEMO_RECORD_LIMIT}")
    print("status: success")
    print(f"finished_at: {datetime.now().astimezone().isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

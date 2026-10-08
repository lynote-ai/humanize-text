"""Validate bounded public demo datasets and their release manifest."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

import yaml


EXPECTED_STAGE_FILES = {
    "01_sft": "sft_train_demo.jsonl",
    "02_reservation": "kto_seed_demo.jsonl",
    "03_generation": "kto_candidates_demo.jsonl",
    "04_negative_selection": "kto_train_demo.jsonl",
    "05_structure_refresh": "kto_train_demo.jsonl",
}
PROMPT_EXAMPLE_COUNT = 5


def parse_args() -> argparse.Namespace:
    """Parse the demo root and manifest supplied by the Make target."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--prompt-examples", required=True, type=Path)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for one demo file."""
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_jsonl(path: Path, record_limit: int) -> int:
    """Validate one JSONL demo and enforce its exact public record limit."""
    count = 0
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                raise ValueError(f"blank line at {path}:{line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON at {path}:{line_number}: {error}") from error
            if not isinstance(record, dict):
                raise ValueError(f"record must be a mapping at {path}:{line_number}")
            source = record.get("source")
            if source is not None and source not in {"crawl", "private"}:
                raise ValueError(f"non-public source label at {path}:{line_number}")
            if source in {"crawl", "private"}:
                input_id = record.get("input_id")
                if not isinstance(input_id, str) or not input_id.startswith(f"{source}:"):
                    raise ValueError(
                        f"public input_id prefix mismatch at {path}:{line_number}"
                    )
            count += 1
            if count > record_limit:
                raise ValueError(f"{path} exceeds the {record_limit}-record public limit")
    if count != record_limit:
        raise ValueError(f"{path} has {count} records; expected exactly {record_limit}")
    return count


def validate_prompt_examples(path: Path) -> int:
    """Require exactly five distinct, non-empty public System Prompt examples."""
    with path.open("r", encoding="utf-8") as input_file:
        prompts = json.load(input_file)
    if not isinstance(prompts, list) or len(prompts) != PROMPT_EXAMPLE_COUNT:
        raise ValueError(
            f"prompt examples must contain exactly {PROMPT_EXAMPLE_COUNT} entries"
        )
    if not all(isinstance(prompt, str) and prompt.strip() for prompt in prompts):
        raise ValueError("every prompt example must be a non-empty string")
    if len(set(prompts)) != PROMPT_EXAMPLE_COUNT:
        raise ValueError("prompt examples must be distinct")
    return len(prompts)


def validate_demo_release(demo_root: Path, manifest_path: Path) -> dict[str, int]:
    """Validate stage coverage, JSON records, hashes, and the no-extra-data rule."""
    with manifest_path.open("r", encoding="utf-8") as input_file:
        manifest = yaml.safe_load(input_file)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("demo manifest schema_version must equal 1")
    record_limit = manifest.get("record_limit_per_stage")
    if record_limit != 50:
        raise ValueError("demo record_limit_per_stage must equal 50")
    stages = manifest.get("stages")
    if not isinstance(stages, list) or len(stages) != len(EXPECTED_STAGE_FILES):
        raise ValueError("demo manifest must register every expected stage exactly once")

    registered: dict[str, dict[str, object]] = {}
    for entry in stages:
        if not isinstance(entry, dict) or not isinstance(entry.get("stage"), str):
            raise ValueError("each demo stage entry must be a mapping with a stage name")
        stage = str(entry["stage"])
        if stage in registered:
            raise ValueError(f"duplicate demo stage registration: {stage}")
        registered[stage] = entry
    if set(registered) != set(EXPECTED_STAGE_FILES):
        raise ValueError("registered demo stages do not match the expected pipeline")

    expected_paths: set[Path] = set()
    counts: dict[str, int] = {}
    project_root = demo_root.parent.parent
    for stage, filename in EXPECTED_STAGE_FILES.items():
        path = demo_root / stage / filename
        expected_paths.add(path.resolve())
        entry = registered[stage]
        if entry.get("path") != path.relative_to(project_root).as_posix():
            raise ValueError(f"manifest path mismatch for {stage}")
        counts[stage] = validate_jsonl(path, record_limit)
        if entry.get("record_count") != counts[stage]:
            raise ValueError(f"manifest record count mismatch for {stage}")
        if entry.get("sha256") != sha256_file(path):
            raise ValueError(f"manifest SHA-256 mismatch for {stage}")

    discovered_paths = {path.resolve() for path in demo_root.rglob("*.jsonl")}
    if discovered_paths != expected_paths:
        extra = sorted(str(path) for path in discovered_paths - expected_paths)
        missing = sorted(str(path) for path in expected_paths - discovered_paths)
        raise ValueError(f"unexpected demo JSONL set; extra={extra}, missing={missing}")
    return counts


def main() -> int:
    """Validate all public demos and return a reliable process exit code."""
    args = parse_args()
    print("target: demo-validate")
    print(f"demo_root: {args.demo_root.resolve()}")
    print(f"manifest: {args.manifest.resolve()}")
    print(f"prompt_examples: {args.prompt_examples.resolve()}")
    print(f"started_at: {datetime.now().astimezone().isoformat()}")
    try:
        counts = validate_demo_release(args.demo_root.resolve(), args.manifest.resolve())
        prompt_count = validate_prompt_examples(args.prompt_examples.resolve())
    except (json.JSONDecodeError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        print("status: failed")
        print(f"error: {error}")
        return 2
    for stage, count in counts.items():
        print(f"{stage}_record_count: {count}")
    print(f"prompt_example_count: {prompt_count}")
    print("status: success")
    print(f"finished_at: {datetime.now().astimezone().isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

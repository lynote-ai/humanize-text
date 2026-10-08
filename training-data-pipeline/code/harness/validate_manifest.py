"""Validate the metadata contract for one Humanize version."""

import argparse
from datetime import date, datetime
from pathlib import Path

import yaml


ALLOWED_STATUSES = {"draft", "prepared", "trained", "evaluated", "released"}


def parse_args() -> argparse.Namespace:
    """Parse command-line parameters."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--require-writable", action="store_true")
    return parser.parse_args()


def require_mapping(value: object, name: str) -> dict[str, object]:
    """Return one required mapping."""
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def require_list(value: object, name: str) -> list[object]:
    """Return one required list."""
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def require_text(value: object, name: str) -> str:
    """Return one non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def validate_manifest(path: Path, require_writable: bool = False) -> str:
    """Validate required version, source, build, and artifact metadata."""
    with path.open("r", encoding="utf-8") as manifest_file:
        manifest = require_mapping(yaml.safe_load(manifest_file), "manifest")
    if manifest.get("schema_version") != 1:
        raise ValueError("schema_version must equal 1")
    version = require_mapping(manifest.get("version"), "version")
    version_id = require_text(version.get("id"), "version.id")
    if version_id != path.resolve().parent.name:
        raise ValueError("version.id must match the version directory")
    status = require_text(version.get("status"), "version.status")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"unsupported version.status: {status}")
    if require_writable and status == "released":
        raise ValueError("released versions cannot start write workflows")
    date.fromisoformat(require_text(version.get("created_on"), "version.created_on"))
    require_text(version.get("objective"), "version.objective")
    planned = require_mapping(manifest.get("planned_training"), "planned_training")
    if not require_list(planned.get("stages"), "planned_training.stages"):
        raise ValueError("planned_training.stages must not be empty")
    inputs = require_mapping(manifest.get("inputs"), "inputs")
    require_list(inputs.get("data_revisions"), "inputs.data_revisions")
    for index, value in enumerate(require_list(inputs.get("candidate_sources"), "candidate_sources")):
        source = require_mapping(value, f"candidate_sources[{index}]")
        for name in ("id", "status", "path", "format", "file_pattern", "intended_use"):
            require_text(source.get(name), f"candidate_sources[{index}].{name}")
    require_mapping(manifest.get("build_parameters"), "build_parameters")
    artifacts = require_mapping(manifest.get("artifacts"), "artifacts")
    for name in ("processed_data", "checkpoints", "evaluations"):
        require_list(artifacts.get(name), f"artifacts.{name}")
    require_list(manifest.get("notes"), "notes")
    return version_id


def main() -> int:
    """Validate the manifest and report status."""
    args = parse_args()
    print("target: manifest-validate")
    print(f"manifest: {args.manifest.resolve()}")
    print(f"started_at: {datetime.now().astimezone().isoformat()}")
    try:
        version_id = validate_manifest(args.manifest.resolve(), args.require_writable)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        print("status: failed")
        print(f"error: {error}")
        return 2
    print(f"version_id: {version_id}")
    print("status: success")
    print(f"finished_at: {datetime.now().astimezone().isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate a disjoint SFT train and KTO generation-seed reservation bundle."""

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import cast

import yaml

from data_process.a_reserve_sft_for_kto import (
    bucket_for,
    iter_jsonl,
    load_yaml_mapping,
    parse_policy,
    sha256_file,
    text_hash,
    training_messages,
    validate_source_registration,
)


OUTPUT_FILENAMES = {
    "sft_train": "sft_train.jsonl",
    "sft_validation": "sft_validation.jsonl",
    "kto_train_seed": "kto_train_seed.jsonl",
    "kto_validation_seed": "kto_validation_seed.jsonl",
    "partition_index": "partition_index.jsonl",
}


def parse_args() -> argparse.Namespace:
    """Parse parameters supplied by the version Makefile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--source-bundle", required=True, type=Path)
    parser.add_argument("--source-artifact-id", required=True)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--bundle", required=True, type=Path)
    return parser.parse_args()


def output_metadata(statistics: dict[str, object], name: str) -> dict[str, object]:
    """Return one required output metadata mapping."""
    outputs = statistics.get("outputs")
    if not isinstance(outputs, dict) or not isinstance(outputs.get(name), dict):
        raise ValueError(f"statistics outputs.{name} must be a mapping")
    return cast(dict[str, object], outputs[name])


def validate_file_metadata(
    path: Path,
    metadata: dict[str, object],
    description: str,
) -> int:
    """Verify one output path, count, size, and SHA-256."""
    expected_count = metadata.get("record_count")
    expected_size = metadata.get("size_bytes")
    expected_hash = metadata.get("sha256")
    if not isinstance(expected_count, int) or expected_count < 0:
        raise ValueError(f"{description} record count is invalid")
    if not isinstance(expected_size, int) or expected_size < 0:
        raise ValueError(f"{description} size is invalid")
    if not isinstance(expected_hash, str):
        raise ValueError(f"{description} SHA-256 is invalid")
    if path.stat().st_size != expected_size:
        raise ValueError(f"{description} size differs from statistics")
    if sha256_file(path) != expected_hash:
        raise ValueError(f"{description} SHA-256 differs from statistics")
    actual_count = sum(1 for _line_number, _line, _record in iter_jsonl(path, description))
    if actual_count != expected_count:
        raise ValueError(f"{description} count differs from statistics")
    return actual_count


def validate_sft_file(path: Path, expected_count: int, description: str) -> int:
    """Validate every generated SFT record."""
    count = 0
    for line_number, _line, record in iter_jsonl(path, description):
        training_messages(record, f"{description} line {line_number}")
        count += 1
    if count != expected_count:
        raise ValueError(f"{description} count changed during schema validation")
    return count


def validate_seed_file(
    path: Path,
    expected_count: int,
    expected_split: str,
    buckets: list[object],
) -> tuple[set[str], set[str], Counter[str]]:
    """Validate prompts, desirable responses, hashes, split, and stratum counts."""
    pair_hashes: set[str] = set()
    target_hashes: set[str] = set()
    quotas: Counter[str] = Counter()
    required = {
        "input_id",
        "source",
        "split",
        "length_bucket",
        "ai_word_count",
        "human_word_count",
        "messages",
        "desirable_response",
        "source_sha256",
        "target_sha256",
        "pair_sha256",
        "system_prompt_id",
    }
    for line_number, _line, record in iter_jsonl(path, f"KTO {expected_split} seed"):
        if set(record) != required:
            raise ValueError(f"invalid KTO seed fields at line {line_number}")
        if record["source"] not in {"crawl", "private"} or record["split"] != expected_split:
            raise ValueError(f"invalid KTO seed source/split at line {line_number}")
        messages = record["messages"]
        if not isinstance(messages, list) or len(messages) != 2:
            raise ValueError(f"KTO seed messages are invalid at line {line_number}")
        if not all(isinstance(message, dict) for message in messages):
            raise ValueError(f"KTO seed message types are invalid at line {line_number}")
        if [message.get("role") for message in messages] != ["system", "user"]:
            raise ValueError(f"KTO seed roles are invalid at line {line_number}")
        user_text = messages[1].get("content")
        desirable = record["desirable_response"]
        if not isinstance(user_text, str) or not isinstance(desirable, str):
            raise ValueError(f"KTO seed text is invalid at line {line_number}")
        if text_hash(user_text) != record["source_sha256"]:
            raise ValueError(f"KTO seed source hash mismatch at line {line_number}")
        if text_hash(desirable) != record["target_sha256"]:
            raise ValueError(f"KTO seed target hash mismatch at line {line_number}")
        word_count = record["ai_word_count"]
        if not isinstance(word_count, int) or isinstance(word_count, bool):
            raise ValueError(f"KTO seed word count is invalid at line {line_number}")
        # parse_policy returns LengthBucket objects; object typing avoids exporting internals here.
        bucket_name = bucket_for(word_count, cast(list, buckets))
        if bucket_name != record["length_bucket"]:
            raise ValueError(f"KTO seed bucket mismatch at line {line_number}")
        pair_digest = str(record["pair_sha256"])
        target_digest = str(record["target_sha256"])
        if pair_digest in pair_hashes or target_digest in target_hashes:
            raise ValueError(f"duplicate KTO pair or target at line {line_number}")
        pair_hashes.add(pair_digest)
        target_hashes.add(target_digest)
        quotas[f"{record['source']}:{bucket_name}"] += 1
    if len(pair_hashes) != expected_count:
        raise ValueError(f"KTO {expected_split} seed count differs from metadata")
    return pair_hashes, target_hashes, quotas


def validate_partition_index(
    path: Path,
    expected_count: int,
) -> tuple[Counter[str], dict[str, set[str]], dict[str, set[str]]]:
    """Validate unique identities and collect partition-level pair and target hashes."""
    counts: Counter[str] = Counter()
    pairs: dict[str, set[str]] = {
        name: set() for name in ("sft_train", "sft_validation", "kto_train", "kto_validation")
    }
    targets: dict[str, set[str]] = {name: set() for name in pairs}
    seen_pairs: set[str] = set()
    for line_number, _line, record in iter_jsonl(path, "partition index"):
        partition = record.get("partition")
        pair_digest = record.get("pair_sha256")
        target_digest = record.get("target_sha256")
        original_split = record.get("original_split")
        if partition not in pairs:
            raise ValueError(f"invalid partition at index line {line_number}")
        if not isinstance(pair_digest, str) or pair_digest in seen_pairs:
            raise ValueError(f"duplicate or invalid pair at index line {line_number}")
        if not isinstance(target_digest, str):
            raise ValueError(f"invalid target at index line {line_number}")
        if partition == "sft_validation" and original_split != "validation":
            raise ValueError("SFT validation contains a non-validation source row")
        if partition != "sft_validation" and original_split != "train":
            raise ValueError("a source validation row was moved out of SFT validation")
        seen_pairs.add(pair_digest)
        pairs[str(partition)].add(pair_digest)
        targets[str(partition)].add(target_digest)
        counts[str(partition)] += 1
    if len(seen_pairs) != expected_count:
        raise ValueError("partition index count differs from statistics")
    return counts, pairs, targets


def validate_manifest_registration(
    manifest_path: Path,
    bundle: Path,
    statistics_sha256: str,
) -> None:
    """Require one exact artifact registration for this bundle."""
    manifest = load_yaml_mapping(manifest_path, "manifest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("processed_data"), list):
        raise ValueError("manifest artifacts.processed_data must be a list")
    relative_statistics = str(
        (bundle / "statistics.yaml").resolve().relative_to(manifest_path.resolve().parent)
    )
    matches = [
        artifact
        for artifact in artifacts["processed_data"]
        if isinstance(artifact, dict) and artifact.get("statistics_path") == relative_statistics
    ]
    if len(matches) != 1:
        raise ValueError("bundle must have exactly one manifest artifact registration")
    artifact = matches[0]
    if artifact.get("status") != "mechanically-validated-awaiting-negative-generation":
        raise ValueError("artifact status must make the missing negative generation explicit")
    if artifact.get("statistics_sha256") != statistics_sha256:
        raise ValueError("manifest statistics SHA-256 differs from bundle")


def validate_bundle(args: argparse.Namespace) -> dict[str, int]:
    """Validate registration, schemas, counts, hashes, quotas, and disjointness."""
    source_metadata = validate_source_registration(
        args.source_manifest.resolve(),
        args.source_bundle.resolve(),
        args.source_artifact_id,
    )
    config = load_yaml_mapping(args.config, "reservation config")
    buckets, quotas, selection = parse_policy(config)
    statistics_path = args.bundle / "statistics.yaml"
    statistics = load_yaml_mapping(statistics_path, "bundle statistics")
    if statistics.get("version_id") != args.manifest.resolve().parent.name:
        raise ValueError("statistics version_id differs from the current version")
    if statistics.get("target") != "reservation-build" or statistics.get("status") != "success":
        raise ValueError("statistics target/status is invalid")

    counts: dict[str, int] = {}
    for name, filename in OUTPUT_FILENAMES.items():
        path = args.bundle / filename
        if not path.is_file():
            raise ValueError(f"bundle output is missing: {path}")
        counts[name] = validate_file_metadata(
            path, output_metadata(statistics, name), name
        )
    validate_sft_file(args.bundle / "sft_train.jsonl", counts["sft_train"], "SFT train")
    validate_sft_file(
        args.bundle / "sft_validation.jsonl",
        counts["sft_validation"],
        "SFT validation",
    )
    train_pairs, train_targets, train_quotas = validate_seed_file(
        args.bundle / "kto_train_seed.jsonl", counts["kto_train_seed"], "train", buckets
    )
    validation_pairs, validation_targets, validation_quotas = validate_seed_file(
        args.bundle / "kto_validation_seed.jsonl",
        counts["kto_validation_seed"],
        "validation",
        buckets,
    )
    if train_pairs & validation_pairs or train_targets & validation_targets:
        raise ValueError("KTO train and validation overlap")

    index_counts, index_pairs, index_targets = validate_partition_index(
        args.bundle / "partition_index.jsonl", counts["partition_index"]
    )
    if train_pairs != index_pairs["kto_train"]:
        raise ValueError("KTO train seed differs from partition index")
    if validation_pairs != index_pairs["kto_validation"]:
        raise ValueError("KTO validation seed differs from partition index")
    sft_targets = index_targets["sft_train"] | index_targets["sft_validation"]
    kto_targets = index_targets["kto_train"] | index_targets["kto_validation"]
    if sft_targets & kto_targets:
        raise ValueError("SFT and KTO target leakage exists")

    combined_quotas = train_quotas + validation_quotas
    for (source, bucket), expected in quotas.items():
        if combined_quotas[f"{source}:{bucket}"] != expected:
            raise ValueError(f"reservation quota mismatch for {source}/{bucket}")
        expected_validation = int(expected * float(selection["kto_validation_ratio"]))
        if validation_quotas[f"{source}:{bucket}"] != expected_validation:
            raise ValueError(f"KTO validation quota mismatch for {source}/{bucket}")

    source_train = cast(dict[str, object], source_metadata["train"])
    source_validation = cast(dict[str, object], source_metadata["validation"])
    if counts["sft_train"] + counts["kto_train_seed"] + counts["kto_validation_seed"] != source_train["record_count"]:
        raise ValueError("source train count does not reconcile")
    if counts["sft_validation"] != source_validation["record_count"]:
        raise ValueError("source validation count does not reconcile")
    if sha256_file(args.bundle / "sft_validation.jsonl") != source_validation["sha256"]:
        raise ValueError("SFT validation is not byte-identical to the registered source")
    if index_counts["sft_train"] != counts["sft_train"]:
        raise ValueError("SFT train index count mismatch")
    if index_counts["sft_validation"] != counts["sft_validation"]:
        raise ValueError("SFT validation index count mismatch")

    statistics_sha256 = sha256_file(statistics_path)
    validate_manifest_registration(args.manifest, args.bundle, statistics_sha256)
    return counts


def main() -> int:
    """Validate one bundle and return a reliable process exit code."""
    args = parse_args()
    print("target: reservation-validate")
    print(f"manifest: {args.manifest.resolve()}")
    print(f"source_manifest: {args.source_manifest.resolve()}")
    print(f"source_bundle: {args.source_bundle.resolve()}")
    print(f"bundle: {args.bundle.resolve()}")
    print(f"started_at: {datetime.now().astimezone().isoformat()}")
    try:
        counts = validate_bundle(args)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        print("status: failed")
        print(f"error: {error}")
        return 2
    for name, count in counts.items():
        print(f"{name}_record_count: {count}")
    print(f"source_artifact_id: {args.source_artifact_id}")
    print("status: success")
    print(f"finished_at: {datetime.now().astimezone().isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

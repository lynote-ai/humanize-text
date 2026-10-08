"""Validate one mechanically selected, review-blocked KTO dataset bundle."""

import argparse
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

import yaml

from data_process.a_reserve_sft_for_kto import text_hash
from data_process.c_generate_kto_candidates import load_yaml_mapping, sha256_file
from data_process.d_select_kto_negatives import NEGATIVE_TYPES, iter_jsonl


OUTPUT_FILENAMES = {
    "train": "train.jsonl",
    "validation": "validation.jsonl",
    "sample_index": "sample_index.jsonl",
    "review_sample": "review_sample.jsonl",
}
ALL_NEGATIVE_TYPES = ("source_copy", *NEGATIVE_TYPES)


@dataclass(frozen=True)
class PairSummary:
    """Fields needed to reconcile one KTO pair with its review row."""

    input_id: str
    split: str
    source: str
    length_bucket: str
    negative_type: str
    positive_sha256: str
    negative_sha256: str
    selected_chain_id: int | None


def parse_args() -> argparse.Namespace:
    """Parse parameters supplied by the version Makefile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--bundle", required=True, type=Path)
    return parser.parse_args()


def output_metadata(statistics: Mapping[str, object], name: str) -> dict[str, object]:
    """Return one required output metadata mapping."""
    outputs = statistics.get("outputs")
    if not isinstance(outputs, dict) or not isinstance(outputs.get(name), dict):
        raise ValueError(f"statistics outputs.{name} must be a mapping")
    return cast(dict[str, object], outputs[name])


def validate_file_metadata(
    path: Path,
    metadata: Mapping[str, object],
    description: str,
) -> int:
    """Verify one output count, byte size, and SHA-256."""
    expected_count = metadata.get("record_count")
    expected_size = metadata.get("size_bytes")
    expected_hash = metadata.get("sha256")
    if not isinstance(expected_count, int) or isinstance(expected_count, bool):
        raise ValueError(f"{description} record count is invalid")
    if not isinstance(expected_size, int) or isinstance(expected_size, bool):
        raise ValueError(f"{description} size is invalid")
    if not isinstance(expected_hash, str):
        raise ValueError(f"{description} SHA-256 is invalid")
    if path.stat().st_size != expected_size:
        raise ValueError(f"{description} size differs from statistics")
    if sha256_file(path) != expected_hash:
        raise ValueError(f"{description} SHA-256 differs from statistics")
    actual_count = sum(1 for _line, _record in iter_jsonl(path, description))
    if actual_count != expected_count:
        raise ValueError(f"{description} count differs from statistics")
    return actual_count


def validate_input_metadata(statistics: Mapping[str, object]) -> None:
    """Require every pinned source file to retain its recorded bytes and hash."""
    inputs = statistics.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("statistics inputs must be a mapping")
    for name in (
        "train_seed",
        "validation_seed",
        "train_candidates",
        "validation_candidates",
        "selector_config",
    ):
        metadata = inputs.get(name)
        if not isinstance(metadata, dict):
            raise ValueError(f"statistics inputs.{name} must be a mapping")
        path_value = metadata.get("path")
        if not isinstance(path_value, str):
            raise ValueError(f"statistics inputs.{name}.path is invalid")
        path = Path(path_value)
        if path.stat().st_size != metadata.get("size_bytes"):
            raise ValueError(f"{name} size differs from statistics")
        if sha256_file(path) != metadata.get("sha256"):
            raise ValueError(f"{name} SHA-256 differs from statistics")


def message_texts(record: Mapping[str, object], description: str) -> tuple[str, str, str]:
    """Validate one ms-swift KTO record and return its three message texts."""
    if set(record) != {"messages", "label"} or not isinstance(record.get("label"), bool):
        raise ValueError(f"invalid KTO fields at {description}")
    messages = record.get("messages")
    if not isinstance(messages, list) or len(messages) != 3:
        raise ValueError(f"invalid KTO messages at {description}")
    if not all(isinstance(message, dict) for message in messages):
        raise ValueError(f"invalid KTO message mapping at {description}")
    if [message.get("role") for message in messages] != ["system", "user", "assistant"]:
        raise ValueError(f"invalid KTO roles at {description}")
    contents = [message.get("content") for message in messages]
    if not all(isinstance(content, str) and content.strip() for content in contents):
        raise ValueError(f"empty KTO content at {description}")
    return cast(tuple[str, str, str], tuple(contents))


def validate_index_pair(
    positive: Mapping[str, object],
    negative: Mapping[str, object],
    split: str,
    pair_number: int,
) -> None:
    """Validate the shared identity and label-specific fields of one index pair."""
    required = {
        "input_id",
        "source",
        "split",
        "length_bucket",
        "label",
        "response_role",
        "source_sha256",
        "target_sha256",
        "pair_sha256",
        "response_sha256",
        "selected_chain_id",
        "selection_metrics",
    }
    if set(positive) != required or set(negative) != required:
        raise ValueError(f"invalid sample-index fields at {split} pair {pair_number}")
    identity_fields = (
        "input_id",
        "source",
        "split",
        "length_bucket",
        "source_sha256",
        "target_sha256",
        "pair_sha256",
        "selected_chain_id",
    )
    if any(positive[name] != negative[name] for name in identity_fields):
        raise ValueError(f"sample-index pair identity mismatch at {split} pair {pair_number}")
    if positive["split"] != split or positive["source"] not in {"crawl", "private"}:
        raise ValueError(f"sample-index source/split mismatch at {split} pair {pair_number}")
    if positive["label"] is not True or negative["label"] is not False:
        raise ValueError(f"sample-index label order mismatch at {split} pair {pair_number}")
    if positive["response_role"] != "held_out_human_positive":
        raise ValueError(f"invalid positive role at {split} pair {pair_number}")
    if negative["response_role"] not in ALL_NEGATIVE_TYPES:
        raise ValueError(f"invalid negative role at {split} pair {pair_number}")
    if positive["selection_metrics"] is not None or not isinstance(
        negative["selection_metrics"], dict
    ):
        raise ValueError(f"invalid selection metrics at {split} pair {pair_number}")
    chain_id = negative["selected_chain_id"]
    if negative["response_role"] == "source_copy":
        if chain_id is not None:
            raise ValueError(f"source-copy chain must be null at {split} pair {pair_number}")
    elif not isinstance(chain_id, int) or isinstance(chain_id, bool) or chain_id not in range(6):
        raise ValueError(f"candidate chain is invalid at {split} pair {pair_number}")


def validate_training_split(
    data_path: Path,
    index_iterator: Iterator[tuple[int, dict[str, object]]],
    split: str,
    expected_inputs: int,
    seen_pairs: set[str],
) -> tuple[Counter[str], dict[str, PairSummary]]:
    """Validate paired labels, prompt equality, hashes, and unique identities."""
    data_iterator = iter_jsonl(data_path, f"KTO {split}")
    type_counts: Counter[str] = Counter()
    summaries: dict[str, PairSummary] = {}
    for pair_number in range(1, expected_inputs + 1):
        try:
            _positive_line, positive = next(data_iterator)
            _negative_line, negative = next(data_iterator)
            _positive_index_line, positive_index = next(index_iterator)
            _negative_index_line, negative_index = next(index_iterator)
        except StopIteration as error:
            raise ValueError(f"{split} data or sample index ended early") from error
        validate_index_pair(positive_index, negative_index, split, pair_number)
        if positive.get("label") is not True or negative.get("label") is not False:
            raise ValueError(f"KTO label order mismatch at {split} pair {pair_number}")
        positive_system, positive_user, positive_response = message_texts(
            positive, f"{split} positive pair {pair_number}"
        )
        negative_system, negative_user, negative_response = message_texts(
            negative, f"{split} negative pair {pair_number}"
        )
        if (positive_system, positive_user) != (negative_system, negative_user):
            raise ValueError(f"KTO prompts differ inside {split} pair {pair_number}")
        if text_hash(positive_user) != positive_index["source_sha256"]:
            raise ValueError(f"source hash mismatch at {split} pair {pair_number}")
        if text_hash(positive_response) != positive_index["response_sha256"]:
            raise ValueError(f"positive response hash mismatch at {split} pair {pair_number}")
        if positive_index["response_sha256"] != positive_index["target_sha256"]:
            raise ValueError(f"positive is not held-out target at {split} pair {pair_number}")
        if text_hash(negative_response) != negative_index["response_sha256"]:
            raise ValueError(f"negative response hash mismatch at {split} pair {pair_number}")
        if negative_index["response_sha256"] == negative_index["target_sha256"]:
            raise ValueError(f"negative equals positive target at {split} pair {pair_number}")
        if negative_index["response_role"] == "source_copy":
            if negative_index["response_sha256"] != negative_index["source_sha256"]:
                raise ValueError(f"source-copy hash mismatch at {split} pair {pair_number}")
        elif negative_index["response_sha256"] == negative_index["source_sha256"]:
            raise ValueError(f"generated negative equals source at {split} pair {pair_number}")
        pair_digest = positive_index["pair_sha256"]
        if not isinstance(pair_digest, str) or pair_digest in seen_pairs:
            raise ValueError(f"duplicate or invalid pair at {split} pair {pair_number}")
        seen_pairs.add(pair_digest)
        negative_type = str(negative_index["response_role"])
        type_counts[negative_type] += 1
        summaries[pair_digest] = PairSummary(
            input_id=str(positive_index["input_id"]),
            split=split,
            source=str(positive_index["source"]),
            length_bucket=str(positive_index["length_bucket"]),
            negative_type=negative_type,
            positive_sha256=str(positive_index["response_sha256"]),
            negative_sha256=str(negative_index["response_sha256"]),
            selected_chain_id=cast(int | None, negative_index["selected_chain_id"]),
        )
    try:
        next(data_iterator)
    except StopIteration:
        return type_counts, summaries
    raise ValueError(f"{split} data contains extra rows")


def validate_review_sample(
    path: Path,
    summaries: Mapping[str, PairSummary],
    expected_per_type: int,
) -> Counter[str]:
    """Validate review stratification and exact linkage to selected pairs."""
    counts: Counter[str] = Counter()
    seen_pairs: set[str] = set()
    for line_number, record in iter_jsonl(path, "KTO review sample"):
        pair_digest = record.get("pair_sha256")
        if not isinstance(pair_digest, str) or pair_digest in seen_pairs:
            raise ValueError(f"invalid review pair at line {line_number}")
        summary = summaries.get(pair_digest)
        if summary is None:
            raise ValueError(f"unknown review pair at line {line_number}")
        expected_fields = {
            "input_id": summary.input_id,
            "source": summary.source,
            "split": summary.split,
            "length_bucket": summary.length_bucket,
            "negative_type": summary.negative_type,
            "selected_chain_id": summary.selected_chain_id,
        }
        if any(record.get(name) != value for name, value in expected_fields.items()):
            raise ValueError(f"review metadata mismatch at line {line_number}")
        if text_hash(str(record.get("desirable_response", ""))) != summary.positive_sha256:
            raise ValueError(f"review positive mismatch at line {line_number}")
        if text_hash(str(record.get("selected_negative", ""))) != summary.negative_sha256:
            raise ValueError(f"review negative mismatch at line {line_number}")
        messages = record.get("messages")
        if not isinstance(messages, list) or len(messages) != 2:
            raise ValueError(f"review prompt is invalid at line {line_number}")
        if [message.get("role") for message in messages if isinstance(message, dict)] != [
            "system",
            "user",
        ]:
            raise ValueError(f"review prompt roles are invalid at line {line_number}")
        counts[summary.negative_type] += 1
        seen_pairs.add(pair_digest)
    expected = Counter({negative_type: expected_per_type for negative_type in ALL_NEGATIVE_TYPES})
    if counts != expected:
        raise ValueError(f"review type counts differ: {dict(counts)}")
    return counts


def validate_manifest_registration(
    manifest_path: Path,
    bundle: Path,
    statistics_sha256: str,
) -> None:
    """Require one exact, review-blocked artifact registration for this bundle."""
    manifest = load_yaml_mapping(manifest_path, "manifest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("processed_data"), list):
        raise ValueError("manifest artifacts.processed_data must be a list")
    relative_bundle = str(bundle.resolve().relative_to(manifest_path.resolve().parent))
    matches = [
        artifact
        for artifact in artifacts["processed_data"]
        if isinstance(artifact, dict)
        and isinstance(artifact.get("parameters"), dict)
        and artifact["parameters"].get("bundle_path") == relative_bundle
    ]
    if len(matches) != 1:
        raise ValueError("bundle must have exactly one manifest artifact registration")
    artifact = matches[0]
    if artifact.get("status") != "mechanically-selected-pending-human-review":
        raise ValueError("KTO artifact must remain blocked on human review")
    if artifact.get("statistics_sha256") != statistics_sha256:
        raise ValueError("manifest statistics SHA-256 differs from bundle")


def expected_type_counts(config: Mapping[str, object], input_count: int) -> Counter[str]:
    """Convert configured split-level fractions to exact expected counts."""
    selection = config.get("selection")
    targets = config.get("negative_type_targets")
    if not isinstance(selection, dict) or not isinstance(targets, dict):
        raise ValueError("statistics config is invalid")
    fractions = {"source_copy": selection.get("source_copy_fraction"), **targets}
    counts: Counter[str] = Counter()
    for negative_type in ALL_NEGATIVE_TYPES:
        fraction = fractions.get(negative_type)
        if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
            raise ValueError(f"invalid configured fraction for {negative_type}")
        value = input_count * float(fraction)
        if not value.is_integer():
            raise ValueError(f"non-integral configured count for {negative_type}")
        counts[negative_type] = int(value)
    if sum(counts.values()) != input_count:
        raise ValueError("configured negative counts do not sum to split size")
    return counts


def validate_bundle(manifest_path: Path, bundle: Path) -> dict[str, int]:
    """Validate hashes, schemas, pairing, ratios, review rows, and registration."""
    statistics_path = bundle / "statistics.yaml"
    statistics = load_yaml_mapping(statistics_path, "KTO statistics")
    if statistics.get("target") != "kto-negative-build" or statistics.get("status") != "success":
        raise ValueError("statistics target/status is invalid")
    if statistics.get("version_id") != manifest_path.resolve().parent.name:
        raise ValueError("statistics version_id differs from current version")
    counts: dict[str, int] = {}
    for name, filename in OUTPUT_FILENAMES.items():
        path = bundle / filename
        if not path.is_file():
            raise ValueError(f"bundle output is missing: {path}")
        counts[name] = validate_file_metadata(
            path, output_metadata(statistics, name), name
        )
    expected_counts = {
        "train": 9000,
        "validation": 1000,
        "sample_index": 10000,
        "review_sample": 150,
    }
    if counts != expected_counts:
        raise ValueError(f"KTO output counts differ: {counts}")
    validate_input_metadata(statistics)

    index_iterator = iter_jsonl(bundle / "sample_index.jsonl", "KTO sample index")
    seen_pairs: set[str] = set()
    train_types, train_summaries = validate_training_split(
        bundle / "train.jsonl", index_iterator, "train", 4500, seen_pairs
    )
    validation_types, validation_summaries = validate_training_split(
        bundle / "validation.jsonl", index_iterator, "validation", 500, seen_pairs
    )
    try:
        next(index_iterator)
    except StopIteration:
        pass
    else:
        raise ValueError("sample index contains extra rows")
    config = statistics.get("config")
    if not isinstance(config, dict):
        raise ValueError("statistics config must be a mapping")
    if train_types != expected_type_counts(config, 4500):
        raise ValueError(f"train negative-type counts differ: {dict(train_types)}")
    if validation_types != expected_type_counts(config, 500):
        raise ValueError(f"validation negative-type counts differ: {dict(validation_types)}")
    summaries = {**train_summaries, **validation_summaries}
    if len(summaries) != 5000:
        raise ValueError("KTO train and validation pair identities overlap")
    selection = cast(dict[str, object], config["selection"])
    review_count = selection.get("review_count_per_negative_type")
    if not isinstance(review_count, int) or isinstance(review_count, bool):
        raise ValueError("review_count_per_negative_type is invalid")
    validate_review_sample(bundle / "review_sample.jsonl", summaries, review_count)
    statistics_sha256 = sha256_file(statistics_path)
    validate_manifest_registration(manifest_path, bundle, statistics_sha256)
    return counts


def main() -> int:
    """Validate one KTO bundle and return a reliable process exit code."""
    args = parse_args()
    print("target: kto-negative-validate")
    print(f"manifest: {args.manifest.resolve()}")
    print(f"bundle: {args.bundle.resolve()}")
    print(f"started_at: {datetime.now().astimezone().isoformat()}")
    try:
        counts = validate_bundle(args.manifest.resolve(), args.bundle.resolve())
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        print("status: failed")
        print(f"error: {error}")
        return 2
    for name, count in counts.items():
        print(f"{name}_record_count: {count}")
    print("unique_input_count: 5000")
    print("artifact_status: mechanically-selected-pending-human-review")
    print("status: success")
    print(f"finished_at: {datetime.now().astimezone().isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

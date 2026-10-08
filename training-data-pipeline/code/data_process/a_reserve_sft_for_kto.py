"""Reserve a deterministic, disjoint subset of SFT train inputs for later KTO."""

import argparse
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
import hashlib
import heapq
import json
from pathlib import Path
import shutil
import unicodedata

import yaml


SOURCE_FILES = {
    "train": "train.jsonl",
    "validation": "validation.jsonl",
    "sample_index": "sample_index.jsonl",
}


@dataclass(frozen=True)
class LengthBucket:
    """Inclusive word-count interval used for deterministic quota sampling."""

    name: str
    min_words: int
    max_words: int | None

    def contains(self, word_count: int) -> bool:
        """Return whether a word count belongs to this interval."""
        return word_count >= self.min_words and (
            self.max_words is None or word_count <= self.max_words
        )


def parse_args() -> argparse.Namespace:
    """Parse parameters supplied by the version Makefile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--source-bundle", required=True, type=Path)
    parser.add_argument("--source-artifact-id", required=True)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--inspect-only", action="store_true")
    return parser.parse_args()


def load_yaml_mapping(path: Path, description: str) -> dict[str, object]:
    """Load one required YAML mapping."""
    if not path.is_file():
        raise ValueError(f"{description} does not exist: {path}")
    with path.open("r", encoding="utf-8") as input_file:
        value = yaml.safe_load(input_file)
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a mapping")
    return value


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for one file."""
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    """Match the normalization used by the upstream SFT builder."""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def text_hash(text: str) -> str:
    """Return a stable SHA-256 over normalized text."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def iter_jsonl(path: Path, description: str) -> Iterator[tuple[int, str, dict[str, object]]]:
    """Stream non-empty JSON mappings while preserving original serialized lines."""
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                raise ValueError(f"blank {description} line at {line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid {description} JSON at line {line_number}: {error}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(f"{description} line {line_number} must be a mapping")
            yield line_number, line, record


def parse_policy(
    config: Mapping[str, object],
) -> tuple[list[LengthBucket], dict[tuple[str, str], int], dict[str, object]]:
    """Validate the reservation policy and return buckets, quotas, and selection settings."""
    if config.get("schema_version") != 1:
        raise ValueError("config schema_version must equal 1")
    raw_selection = config.get("selection")
    raw_buckets = config.get("length_buckets")
    raw_quotas = config.get("quotas")
    if not isinstance(raw_selection, dict):
        raise ValueError("config selection must be a mapping")
    if not isinstance(raw_buckets, list) or not raw_buckets:
        raise ValueError("config length_buckets must be a non-empty list")
    if not isinstance(raw_quotas, dict):
        raise ValueError("config quotas must be a mapping")

    buckets: list[LengthBucket] = []
    for index, raw_bucket in enumerate(raw_buckets):
        if not isinstance(raw_bucket, dict):
            raise ValueError(f"length_buckets[{index}] must be a mapping")
        name = raw_bucket.get("name")
        min_words = raw_bucket.get("min_words")
        max_words = raw_bucket.get("max_words")
        if not isinstance(name, str) or not name:
            raise ValueError(f"length_buckets[{index}].name must be non-empty")
        if not isinstance(min_words, int) or isinstance(min_words, bool) or min_words < 0:
            raise ValueError(f"length_buckets[{index}].min_words must be non-negative")
        if max_words is not None and (
            not isinstance(max_words, int)
            or isinstance(max_words, bool)
            or max_words < min_words
        ):
            raise ValueError(f"length_buckets[{index}].max_words is invalid")
        buckets.append(LengthBucket(name, min_words, max_words))
    if len({bucket.name for bucket in buckets}) != len(buckets):
        raise ValueError("length bucket names must be unique")

    quotas: dict[tuple[str, str], int] = {}
    for source in ("crawl", "private"):
        source_quotas = raw_quotas.get(source)
        if not isinstance(source_quotas, dict):
            raise ValueError(f"quotas.{source} must be a mapping")
        if set(source_quotas) != {bucket.name for bucket in buckets}:
            raise ValueError(f"quotas.{source} must name every length bucket exactly once")
        for bucket in buckets:
            quota = source_quotas[bucket.name]
            if not isinstance(quota, int) or isinstance(quota, bool) or quota < 0:
                raise ValueError(f"quota for {source}/{bucket.name} must be non-negative")
            quotas[(source, bucket.name)] = quota

    target = raw_selection.get("target_input_count")
    selection_seed = raw_selection.get("selection_seed")
    validation_seed = raw_selection.get("kto_validation_seed")
    validation_ratio = raw_selection.get("kto_validation_ratio")
    if not isinstance(target, int) or isinstance(target, bool) or target <= 0:
        raise ValueError("selection.target_input_count must be positive")
    if sum(quotas.values()) != target:
        raise ValueError("sum of quotas must equal selection.target_input_count")
    if not isinstance(selection_seed, int) or isinstance(selection_seed, bool):
        raise ValueError("selection.selection_seed must be an integer")
    if not isinstance(validation_seed, int) or isinstance(validation_seed, bool):
        raise ValueError("selection.kto_validation_seed must be an integer")
    if not isinstance(validation_ratio, (int, float)) or not 0 < validation_ratio < 1:
        raise ValueError("selection.kto_validation_ratio must be between zero and one")
    for stratum, quota in quotas.items():
        validation_count = quota * float(validation_ratio)
        if not validation_count.is_integer():
            raise ValueError(f"validation ratio does not produce an integer for {stratum}")
    return buckets, quotas, raw_selection


def bucket_for(word_count: int, buckets: list[LengthBucket]) -> str:
    """Return the unique configured bucket for one word count."""
    matches = [bucket.name for bucket in buckets if bucket.contains(word_count)]
    if len(matches) != 1:
        raise ValueError(f"word count {word_count} maps to {len(matches)} buckets")
    return matches[0]


def stable_score(seed: int, identity: str) -> int:
    """Return a deterministic pseudo-random rank without relying on file order."""
    payload = f"{seed}:{identity}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest(), "big")


def validate_index_record(record: Mapping[str, object], line_number: int) -> None:
    """Validate the upstream fields needed for reservation and alignment."""
    required = {
        "sample_id",
        "source",
        "split",
        "source_sha256",
        "target_sha256",
        "pair_sha256",
        "system_prompt_id",
        "ai_word_count",
        "human_word_count",
    }
    if not required.issubset(record):
        raise ValueError(f"sample index fields missing at line {line_number}")
    if record["source"] not in {"crawl", "private"}:
        raise ValueError(f"unknown source at sample index line {line_number}")
    if record["split"] not in {"train", "validation"}:
        raise ValueError(f"unknown split at sample index line {line_number}")
    for field in ("sample_id", "source_sha256", "target_sha256", "pair_sha256"):
        if not isinstance(record[field], str) or not str(record[field]).strip():
            raise ValueError(f"invalid {field} at sample index line {line_number}")
    word_count = record["ai_word_count"]
    if not isinstance(word_count, int) or isinstance(word_count, bool) or word_count < 0:
        raise ValueError(f"invalid ai_word_count at sample index line {line_number}")


def select_reserved_inputs(
    index_path: Path,
    buckets: list[LengthBucket],
    quotas: Mapping[tuple[str, str], int],
    selection: Mapping[str, object],
) -> tuple[dict[str, dict[str, object]], Counter[tuple[str, str]], Counter[str]]:
    """Stream the index and retain only each stratum's deterministically lowest ranks."""
    seed = int(selection["selection_seed"])
    heaps: dict[tuple[str, str], list[tuple[int, str, dict[str, object]]]] = {
        stratum: [] for stratum, quota in quotas.items() if quota > 0
    }
    supply: Counter[tuple[str, str]] = Counter()
    split_counts: Counter[str] = Counter()
    target_hashes: set[str] = set()
    pair_hashes: set[str] = set()
    require_unique_targets = selection.get("require_unique_target_hashes") is True

    for line_number, _line, record in iter_jsonl(index_path, "sample index"):
        validate_index_record(record, line_number)
        split = str(record["split"])
        split_counts[split] += 1
        pair_digest = str(record["pair_sha256"])
        if pair_digest in pair_hashes:
            raise ValueError(f"duplicate pair hash at sample index line {line_number}")
        pair_hashes.add(pair_digest)
        if split != "train":
            continue
        target_digest = str(record["target_sha256"])
        if require_unique_targets and target_digest in target_hashes:
            raise ValueError("train contains a repeated target hash; group-level reservation is required")
        target_hashes.add(target_digest)
        bucket = bucket_for(int(record["ai_word_count"]), buckets)
        stratum = (str(record["source"]), bucket)
        supply[stratum] += 1
        quota = quotas[stratum]
        if quota == 0:
            continue
        sample_id = str(record["sample_id"])
        score = stable_score(seed, sample_id)
        candidate = dict(record)
        candidate["length_bucket"] = bucket
        heap = heaps[stratum]
        item = (-score, sample_id, candidate)
        if len(heap) < quota:
            heapq.heappush(heap, item)
        elif score < -heap[0][0]:
            heapq.heapreplace(heap, item)

    selected: dict[str, dict[str, object]] = {}
    for stratum, quota in quotas.items():
        if supply[stratum] < quota:
            raise ValueError(
                f"insufficient supply for {stratum}: {supply[stratum]} available, {quota} required"
            )
        for _negative_score, _sample_id, record in heaps.get(stratum, []):
            pair_digest = str(record["pair_sha256"])
            if pair_digest in selected:
                raise ValueError("one pair was selected into multiple strata")
            selected[pair_digest] = record
    if len(selected) != int(selection["target_input_count"]):
        raise ValueError("selected input count differs from configured target")
    return selected, supply, split_counts


def assign_kto_validation(
    selected: Mapping[str, Mapping[str, object]],
    quotas: Mapping[tuple[str, str], int],
    selection: Mapping[str, object],
) -> set[str]:
    """Create an exact, source-and-length-stratified KTO validation subset."""
    seed = int(selection["kto_validation_seed"])
    ratio = float(selection["kto_validation_ratio"])
    by_stratum: dict[tuple[str, str], list[tuple[int, str]]] = {
        stratum: [] for stratum in quotas
    }
    for pair_digest, record in selected.items():
        stratum = (str(record["source"]), str(record["length_bucket"]))
        by_stratum[stratum].append(
            (stable_score(seed, str(record["sample_id"])), pair_digest)
        )
    validation: set[str] = set()
    for stratum, quota in quotas.items():
        expected = int(quota * ratio)
        ordered = sorted(by_stratum[stratum])
        validation.update(pair_digest for _score, pair_digest in ordered[:expected])
    return validation


def validate_source_registration(
    source_manifest_path: Path,
    source_bundle: Path,
    source_artifact_id: str,
) -> dict[str, object]:
    """Verify the exact registered upstream artifact, counts, paths, and hashes."""
    manifest = load_yaml_mapping(source_manifest_path, "source manifest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("processed_data"), list):
        raise ValueError("source manifest processed_data must be a list")
    matches = [
        artifact
        for artifact in artifacts["processed_data"]
        if isinstance(artifact, dict) and artifact.get("id") == source_artifact_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"source manifest must register exactly one {source_artifact_id}"
        )
    artifact = matches[0]
    parameters = artifact.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError("source artifact parameters must be a mapping")
    expected = {
        "train": (artifact.get("record_count"), artifact.get("sha256")),
        "validation": (
            parameters.get("sft_validation_record_count"),
            parameters.get("sft_validation_sha256"),
        ),
        "sample_index": (
            parameters.get("sample_index_record_count"),
            parameters.get("sample_index_sha256"),
        ),
    }
    metadata: dict[str, object] = {}
    for name, filename in SOURCE_FILES.items():
        path = source_bundle / filename
        count, expected_hash = expected[name]
        if not path.is_file() or not isinstance(count, int) or not isinstance(expected_hash, str):
            raise ValueError(f"source {name} registration is incomplete")
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise ValueError(f"source {name} SHA-256 differs from its manifest")
        metadata[name] = {
            "path": str(path.resolve()),
            "record_count": count,
            "size_bytes": path.stat().st_size,
            "sha256": actual_hash,
        }
    metadata["manifest_sha256"] = sha256_file(source_manifest_path)
    return metadata


def training_messages(record: Mapping[str, object], description: str) -> list[dict[str, object]]:
    """Validate one upstream SFT record and return its three messages."""
    messages = record.get("messages")
    if not isinstance(messages, list) or len(messages) != 3:
        raise ValueError(f"{description} must contain exactly three messages")
    if not all(isinstance(message, dict) for message in messages):
        raise ValueError(f"{description} messages must be mappings")
    typed_messages = [dict(message) for message in messages]
    if [message.get("role") for message in typed_messages] != ["system", "user", "assistant"]:
        raise ValueError(f"{description} roles are invalid")
    if typed_messages[2].get("loss") is not True:
        raise ValueError(f"{description} assistant loss must be true")
    for message in typed_messages:
        if not isinstance(message.get("content"), str) or not str(message["content"]).strip():
            raise ValueError(f"{description} contains empty content")
    return typed_messages


def next_aligned_record(
    iterator: Iterator[tuple[int, str, dict[str, object]]],
    description: str,
) -> tuple[str, dict[str, object]]:
    """Consume one split-specific record or report a premature end."""
    try:
        _line_number, raw_line, record = next(iterator)
    except StopIteration as error:
        raise ValueError(f"{description} ended before sample index") from error
    return raw_line, record


def ensure_exhausted(
    iterator: Iterator[tuple[int, str, dict[str, object]]], description: str
) -> None:
    """Require one split iterator to end exactly with the sample index."""
    try:
        next(iterator)
    except StopIteration:
        return
    raise ValueError(f"{description} has records not represented in sample index")


def write_partitioned_outputs(
    source_bundle: Path,
    output_paths: Mapping[str, Path],
    selected: Mapping[str, Mapping[str, object]],
    kto_validation: set[str],
    buckets: list[LengthBucket],
) -> dict[str, object]:
    """Stream aligned source files into mutually exclusive SFT and KTO preparation files."""
    train_iterator = iter_jsonl(source_bundle / "train.jsonl", "source train")
    validation_iterator = iter_jsonl(
        source_bundle / "validation.jsonl", "source validation"
    )
    counts: Counter[str] = Counter()
    quota_counts: Counter[str] = Counter()
    selected_targets: set[str] = set()
    sft_targets: set[str] = set()
    selected_pairs_written: set[str] = set()

    with (
        output_paths["sft_train"].open("x", encoding="utf-8") as sft_train_file,
        output_paths["sft_validation"].open("x", encoding="utf-8") as sft_validation_file,
        output_paths["kto_train_seed"].open("x", encoding="utf-8") as kto_train_file,
        output_paths["kto_validation_seed"].open("x", encoding="utf-8") as kto_validation_file,
        output_paths["partition_index"].open("x", encoding="utf-8") as index_file,
    ):
        for line_number, _index_line, index_record in iter_jsonl(
            source_bundle / "sample_index.jsonl", "sample index"
        ):
            validate_index_record(index_record, line_number)
            original_split = str(index_record["split"])
            source_iterator = train_iterator if original_split == "train" else validation_iterator
            raw_line, training_record = next_aligned_record(
                source_iterator, f"source {original_split}"
            )
            messages = training_messages(training_record, f"source {original_split} record")
            user_text = str(messages[1]["content"])
            assistant_text = str(messages[2]["content"])
            if text_hash(user_text) != index_record["source_sha256"]:
                raise ValueError(f"source hash mismatch at sample index line {line_number}")
            if text_hash(assistant_text) != index_record["target_sha256"]:
                raise ValueError(f"target hash mismatch at sample index line {line_number}")

            pair_digest = str(index_record["pair_sha256"])
            length_bucket = bucket_for(int(index_record["ai_word_count"]), buckets)
            output_index = dict(index_record)
            output_index["original_split"] = original_split
            output_index["length_bucket"] = length_bucket
            if original_split == "validation":
                partition = "sft_validation"
                sft_validation_file.write(raw_line)
                counts[partition] += 1
                sft_targets.add(str(index_record["target_sha256"]))
            elif pair_digest not in selected:
                partition = "sft_train"
                sft_train_file.write(raw_line)
                counts[partition] += 1
                sft_targets.add(str(index_record["target_sha256"]))
            else:
                kto_split = "validation" if pair_digest in kto_validation else "train"
                partition = f"kto_{kto_split}"
                seed_record = {
                    "input_id": index_record["sample_id"],
                    "source": index_record["source"],
                    "split": kto_split,
                    "length_bucket": length_bucket,
                    "ai_word_count": index_record["ai_word_count"],
                    "human_word_count": index_record["human_word_count"],
                    "messages": [messages[0], messages[1]],
                    "desirable_response": assistant_text,
                    "source_sha256": index_record["source_sha256"],
                    "target_sha256": index_record["target_sha256"],
                    "pair_sha256": pair_digest,
                    "system_prompt_id": index_record["system_prompt_id"],
                }
                output_file = (
                    kto_validation_file if kto_split == "validation" else kto_train_file
                )
                output_file.write(
                    json.dumps(seed_record, ensure_ascii=False, separators=(",", ":")) + "\n"
                )
                counts[partition] += 1
                quota_counts[f"{index_record['source']}:{length_bucket}"] += 1
                selected_pairs_written.add(pair_digest)
                selected_targets.add(str(index_record["target_sha256"]))
            output_index["partition"] = partition
            index_file.write(
                json.dumps(output_index, ensure_ascii=False, separators=(",", ":")) + "\n"
            )

    ensure_exhausted(train_iterator, "source train")
    ensure_exhausted(validation_iterator, "source validation")
    if selected_pairs_written != set(selected):
        raise ValueError("not every selected KTO pair was written exactly once")
    if selected_targets & sft_targets:
        raise ValueError("Human target leakage exists between SFT and KTO partitions")
    return {
        "partition_counts": dict(sorted(counts.items())),
        "quota_counts": dict(sorted(quota_counts.items())),
        "sft_kto_target_overlap_count": len(selected_targets & sft_targets),
        "selected_pair_count": len(selected_pairs_written),
    }


def file_metadata(path: Path, record_count: int) -> dict[str, object]:
    """Return stable metadata for one generated file."""
    return {
        "path": str(path),
        "record_count": record_count,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def print_supply(
    supply: Mapping[tuple[str, str], int],
    quotas: Mapping[tuple[str, str], int],
) -> None:
    """Print compact source-and-length supply diagnostics."""
    print(f"{'source':<10} {'bucket':<12} {'available':>10} {'reserved':>10} {'remaining':>10}")
    for source, bucket in quotas:
        available = supply[(source, bucket)]
        reserved = quotas[(source, bucket)]
        print(f"{source:<10} {bucket:<12} {available:>10} {reserved:>10} {available-reserved:>10}")


def register_artifact(
    manifest_path: Path,
    bundle_dir: Path,
    timestamp: str,
    outputs: Mapping[str, Mapping[str, object]],
    statistics_path: Path,
    statistics_sha256: str,
    config_path: Path,
) -> None:
    """Register the mechanically validated preparation artifact in this version."""
    manifest = load_yaml_mapping(manifest_path, "manifest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("processed_data"), list):
        raise ValueError("manifest artifacts.processed_data must be a list")
    artifact_id = f"sft-kto-reservation-{timestamp.replace('_', '-')}"
    if any(
        isinstance(artifact, dict) and artifact.get("id") == artifact_id
        for artifact in artifacts["processed_data"]
    ):
        raise ValueError(f"artifact already registered: {artifact_id}")
    version_dir = manifest_path.resolve().parent

    def relative(path_value: object) -> str:
        return str(Path(str(path_value)).resolve().relative_to(version_dir))

    artifact = {
        "id": artifact_id,
        "status": "mechanically-validated-awaiting-negative-generation",
        "purpose": "disjoint-sft-train-and-kto-generation-seed-reservation",
        "source_id": "crawl-private-sft-snapshot",
        "path": relative(outputs["sft_train"]["path"]),
        "statistics_path": relative(statistics_path),
        "format": "ms-swift-sft-jsonl-and-kto-generation-seed-jsonl",
        "created_at": datetime.now().astimezone().isoformat(),
        "record_count": outputs["sft_train"]["record_count"],
        "size_bytes": outputs["sft_train"]["size_bytes"],
        "sha256": outputs["sft_train"]["sha256"],
        "statistics_sha256": statistics_sha256,
        "parameters": {
            "sft_validation_path": relative(outputs["sft_validation"]["path"]),
            "sft_validation_record_count": outputs["sft_validation"]["record_count"],
            "sft_validation_sha256": outputs["sft_validation"]["sha256"],
            "kto_train_seed_path": relative(outputs["kto_train_seed"]["path"]),
            "kto_train_input_count": outputs["kto_train_seed"]["record_count"],
            "kto_train_seed_sha256": outputs["kto_train_seed"]["sha256"],
            "kto_validation_seed_path": relative(outputs["kto_validation_seed"]["path"]),
            "kto_validation_input_count": outputs["kto_validation_seed"]["record_count"],
            "kto_validation_seed_sha256": outputs["kto_validation_seed"]["sha256"],
            "partition_index_path": relative(outputs["partition_index"]["path"]),
            "partition_index_record_count": outputs["partition_index"]["record_count"],
            "partition_index_sha256": outputs["partition_index"]["sha256"],
            "reservation_config_path": str(config_path),
            "reservation_config_sha256": sha256_file(config_path),
            "bundle_path": relative(bundle_dir),
        },
    }
    artifacts["processed_data"].append(artifact)
    version = manifest.get("version")
    if isinstance(version, dict):
        version["status"] = "prepared"
    planned = manifest.get("planned_training")
    if isinstance(planned, dict) and isinstance(planned.get("stages"), list):
        for stage in planned["stages"]:
            if isinstance(stage, dict) and stage.get("name") == "sft-kto-reservation":
                stage["status"] = "completed"
    with manifest_path.open("w", encoding="utf-8") as output_file:
        yaml.safe_dump(manifest, output_file, allow_unicode=True, sort_keys=False)


def build_statistics(
    started_at: str,
    finished_at: str,
    manifest_path: Path,
    source_manifest_path: Path,
    source_metadata: Mapping[str, object],
    config_path: Path,
    config: Mapping[str, object],
    supply: Mapping[tuple[str, str], int],
    quotas: Mapping[tuple[str, str], int],
    split_counts: Mapping[str, int],
    summary: Mapping[str, object],
    outputs: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Build the reproducibility and validation report for this reservation."""
    return {
        "version_id": manifest_path.resolve().parent.name,
        "target": "reservation-build",
        "manifest": str(manifest_path.resolve()),
        "started_at": started_at,
        "finished_at": finished_at,
        "status": "success",
        "inputs": {
            "source_manifest": {
                "path": str(source_manifest_path.resolve()),
                "sha256": source_metadata["manifest_sha256"],
            },
            "source_files": {
                name: value for name, value in source_metadata.items() if name != "manifest_sha256"
            },
            "reservation_config": {
                "path": str(config_path.resolve()),
                "sha256": sha256_file(config_path),
            },
        },
        "config": config,
        "source_split_counts": dict(sorted(split_counts.items())),
        "supply": {
            f"{source}:{bucket}": supply[(source, bucket)] for source, bucket in quotas
        },
        "reservation_quotas": {
            f"{source}:{bucket}": quota for (source, bucket), quota in quotas.items()
        },
        "partition": summary,
        "outputs": outputs,
        "code_sha256": {
            "code/data_process/a_reserve_sft_for_kto.py": sha256_file(Path(__file__))
        },
        "limitations": [
            "KTO seed files contain prompts and desirable responses only; they are not train-ready.",
            "Undesirable responses require later model generation and semantic quality review.",
            "Word-count strata are not tokenizer-token length strata.",
            "No model inference, model loading, training, GPU task, or detector request was run.",
        ],
    }


def main() -> int:
    """Inspect or build the deterministic SFT/KTO reservation."""
    args = parse_args()
    started_at = datetime.now().astimezone().isoformat()
    print(f"target: {'reservation-inspect' if args.inspect_only else 'reservation-build'}")
    print(f"manifest: {args.manifest.resolve()}")
    print(f"source_manifest: {args.source_manifest.resolve()}")
    print(f"source_bundle: {args.source_bundle.resolve()}")
    print(f"config: {args.config.resolve()}")
    print(f"started_at: {started_at}")
    temporary_dir: Path | None = None
    try:
        manifest = load_yaml_mapping(args.manifest, "manifest")
        version = manifest.get("version")
        if not isinstance(version, dict) or version.get("status") == "released":
            raise ValueError("released or invalid version cannot build data")
        config = load_yaml_mapping(args.config, "reservation config")
        buckets, quotas, selection = parse_policy(config)
        source_metadata = validate_source_registration(
            args.source_manifest.resolve(),
            args.source_bundle.resolve(),
            args.source_artifact_id,
        )
        selected, supply, split_counts = select_reserved_inputs(
            args.source_bundle / "sample_index.jsonl", buckets, quotas, selection
        )
        kto_validation = assign_kto_validation(selected, quotas, selection)
        print_supply(supply, quotas)
        print(f"source_train_count: {split_counts['train']}")
        print(f"source_validation_count: {split_counts['validation']}")
        print(f"reserved_input_count: {len(selected)}")
        print(f"kto_train_input_count: {len(selected) - len(kto_validation)}")
        print(f"kto_validation_input_count: {len(kto_validation)}")
        if args.inspect_only:
            print("status: success")
            print(f"finished_at: {datetime.now().astimezone().isoformat()}")
            return 0

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"sft_kto_reservation_{timestamp}"
        output_root = args.output_dir.resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        final_dir = output_root / bundle_name
        temporary_dir = output_root / f".{bundle_name}.tmp"
        temporary_dir.mkdir(exist_ok=False)
        final_paths = {
            "sft_train": final_dir / "sft_train.jsonl",
            "sft_validation": final_dir / "sft_validation.jsonl",
            "kto_train_seed": final_dir / "kto_train_seed.jsonl",
            "kto_validation_seed": final_dir / "kto_validation_seed.jsonl",
            "partition_index": final_dir / "partition_index.jsonl",
        }
        temporary_paths = {
            name: temporary_dir / path.name for name, path in final_paths.items()
        }
        summary = write_partitioned_outputs(
            args.source_bundle.resolve(), temporary_paths, selected, kto_validation, buckets
        )
        partition_counts = summary["partition_counts"]
        if not isinstance(partition_counts, dict):
            raise ValueError("partition counts were not produced")
        expected_counts = {
            "sft_train": split_counts["train"] - len(selected),
            "sft_validation": split_counts["validation"],
            "kto_train_seed": len(selected) - len(kto_validation),
            "kto_validation_seed": len(kto_validation),
            "partition_index": split_counts["train"] + split_counts["validation"],
        }
        outputs = {
            name: file_metadata(temporary_paths[name], expected_counts[name])
            for name in temporary_paths
        }
        for name, metadata in outputs.items():
            metadata["path"] = str(final_paths[name])
        source_validation = source_metadata["validation"]
        if not isinstance(source_validation, dict):
            raise ValueError("source validation metadata is invalid")
        if outputs["sft_validation"]["sha256"] != source_validation["sha256"]:
            raise ValueError("SFT validation output is not byte-identical to the source")
        finished_at = datetime.now().astimezone().isoformat()
        statistics = build_statistics(
            started_at,
            finished_at,
            args.manifest,
            args.source_manifest,
            source_metadata,
            args.config,
            config,
            supply,
            quotas,
            split_counts,
            summary,
            outputs,
        )
        statistics_temp = temporary_dir / "statistics.yaml"
        with statistics_temp.open("x", encoding="utf-8") as output_file:
            yaml.safe_dump(statistics, output_file, allow_unicode=True, sort_keys=False)
        temporary_dir.rename(final_dir)
        temporary_dir = None
        statistics_path = final_dir / "statistics.yaml"
        statistics_sha256 = sha256_file(statistics_path)
        register_artifact(
            args.manifest,
            final_dir,
            timestamp,
            outputs,
            statistics_path,
            statistics_sha256,
            args.config,
        )
        print(f"output_bundle: {final_dir}")
        print(f"sft_train_record_count: {expected_counts['sft_train']}")
        print(f"sft_validation_record_count: {expected_counts['sft_validation']}")
        print(f"kto_train_input_count: {expected_counts['kto_train_seed']}")
        print(f"kto_validation_input_count: {expected_counts['kto_validation_seed']}")
        print(f"statistics_sha256: {statistics_sha256}")
        print("status: success")
        print(f"finished_at: {finished_at}")
        return 0
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        if temporary_dir is not None and temporary_dir.is_dir():
            shutil.rmtree(temporary_dir)
        print("status: failed")
        print(f"error: {error}")
        print(f"finished_at: {datetime.now().astimezone().isoformat()}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

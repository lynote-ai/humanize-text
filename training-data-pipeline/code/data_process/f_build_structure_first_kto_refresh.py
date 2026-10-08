"""Build refreshed KTO pairs from Humanize positives and six candidates."""

import argparse
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import shutil
from typing import cast
import unicodedata

from tqdm import tqdm
import yaml

from data_process.structure_first_metrics import (
    StructureMetrics,
    calculate_metrics,
    positive_is_eligible,
    severe_failure_type,
    under_edit_is_eligible,
)


@dataclass(frozen=True)
class UnderEditOption:
    """One eligible generated under-edit and its structure metrics."""

    chain_id: int
    rewrite: str
    metrics: StructureMetrics


@dataclass(frozen=True)
class InputAnalysis:
    """One aligned input and its best eligible generated under-edit."""

    pair_sha256: str
    input_id: str
    split: str
    source: str
    length_bucket: str
    option: UnderEditOption | None


@dataclass(frozen=True)
class NegativeSelection:
    """The negative role and optional generated chain chosen for one input."""

    negative_type: str
    chain_id: int | None


def parse_args() -> argparse.Namespace:
    """Parse parameters supplied by the version Makefile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--train-seed", required=True, type=Path)
    parser.add_argument("--validation-seed", required=True, type=Path)
    parser.add_argument("--train-candidates", required=True, type=Path)
    parser.add_argument("--validation-candidates", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def load_yaml(path: Path, description: str) -> dict[str, object]:
    """Load one required YAML mapping."""
    if not path.is_file():
        raise ValueError(f"{description} does not exist: {path}")
    with path.open("r", encoding="utf-8") as input_file:
        value = yaml.safe_load(input_file)
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a mapping")
    return value


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    """Normalize text for stable response hashing."""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def text_hash(text: str) -> str:
    """Return a stable SHA-256 digest over normalized text."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def stable_score(seed: int, identity: str) -> int:
    """Return a deterministic rank independent of file order."""
    return int.from_bytes(
        hashlib.sha256(f"{seed}:{identity}".encode("utf-8")).digest(), "big"
    )


def iter_jsonl(path: Path, description: str) -> Iterator[tuple[int, dict[str, object]]]:
    """Stream non-empty JSON mappings with line numbers."""
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
            yield line_number, record


def validate_seed(record: Mapping[str, object], split: str, line_number: int) -> None:
    """Validate the structure-positive seed fields used by this builder."""
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
    if set(record) != required:
        raise ValueError(f"invalid seed fields at {split}:{line_number}")
    if record["split"] != split:
        raise ValueError(f"seed split mismatch at {split}:{line_number}")
    messages = record["messages"]
    if not isinstance(messages, list) or len(messages) != 2:
        raise ValueError(f"invalid seed messages at {split}:{line_number}")
    if [message.get("role") for message in messages if isinstance(message, dict)] != [
        "system",
        "user",
    ]:
        raise ValueError(f"invalid seed roles at {split}:{line_number}")
    if not isinstance(record["desirable_response"], str) or not str(record["desirable_response"]).strip():
        raise ValueError(f"empty desirable response at {split}:{line_number}")


def validate_candidates(
    record: Mapping[str, object], seed: Mapping[str, object], split: str, line_number: int
) -> list[dict[str, object]]:
    """Validate an aligned one-round, three-candidate generation row."""
    required = {
        "input_id",
        "source",
        "split",
        "length_bucket",
        "source_sha256",
        "target_sha256",
        "pair_sha256",
        "rounds",
        "num_results",
        "results",
    }
    if set(record) != required:
        raise ValueError(f"invalid candidate fields at {split}:{line_number}")
    for field in (
        "input_id",
        "source",
        "split",
        "length_bucket",
        "source_sha256",
        "target_sha256",
        "pair_sha256",
    ):
        if record[field] != seed[field]:
            raise ValueError(f"candidate {field} mismatch at {split}:{line_number}")
    if record["rounds"] != 2 or record["num_results"] != 6:
        raise ValueError(f"candidate generation shape mismatch at {split}:{line_number}")
    results = record["results"]
    if not isinstance(results, list) or len(results) != 6:
        raise ValueError(f"candidate results must contain six rows at {split}:{line_number}")
    typed: list[dict[str, object]] = []
    for chain_id, result in enumerate(results):
        if not isinstance(result, dict) or result.get("chain_id") != chain_id:
            raise ValueError(f"candidate chain order mismatch at {split}:{line_number}")
        if not isinstance(result.get("rewrite"), str) or not str(result["rewrite"]).strip():
            raise ValueError(f"empty candidate rewrite at {split}:{line_number}")
        typed.append(result)
    return typed


def iter_aligned(
    seed_path: Path, candidate_path: Path, split: str
) -> Iterator[tuple[int, dict[str, object], list[dict[str, object]]]]:
    """Stream exact seed/candidate pairs and reject count or identity drift."""
    for pair in zip_longest(
        iter_jsonl(seed_path, f"{split} seed"),
        iter_jsonl(candidate_path, f"{split} candidates"),
    ):
        if pair[0] is None or pair[1] is None:
            raise ValueError(f"{split} seed and candidate counts differ")
        (seed_line, seed), (candidate_line, candidate) = cast(tuple, pair)
        if seed_line != candidate_line:
            raise ValueError(f"{split} seed and candidate line numbers differ")
        validate_seed(seed, split, seed_line)
        results = validate_candidates(candidate, seed, split, candidate_line)
        yield seed_line, seed, results


def analyze_split(
    seed_path: Path,
    candidate_path: Path,
    split: str,
    expected_count: int,
    policy: Mapping[str, object],
) -> tuple[list[InputAnalysis], Counter[str]]:
    """Select the smallest eligible lexical edit for every aligned input."""
    analyses: list[InputAnalysis] = []
    funnel: Counter[str] = Counter()
    for _line, seed, results in tqdm(
        iter_aligned(seed_path, candidate_path, split),
        total=expected_count,
        desc=f"Analyzing {split} under-edits",
    ):
        messages = cast(list[dict[str, object]], seed["messages"])
        source_text = str(messages[1]["content"])
        options: list[UnderEditOption] = []
        for result in results:
            rewrite = str(result["rewrite"])
            metrics = calculate_metrics(source_text, rewrite)
            funnel["candidate:scanned"] += 1
            if under_edit_is_eligible(metrics, policy):
                funnel["candidate:eligible_under_edit"] += 1
                options.append(
                    UnderEditOption(int(result["chain_id"]), rewrite, metrics)
                )
            else:
                funnel["candidate:rejected"] += 1
        option = min(
            options,
            key=lambda value: (value.metrics.edit_distance, value.chain_id),
            default=None,
        )
        if option is None:
            funnel["input:no_eligible_under_edit"] += 1
        else:
            funnel["input:eligible_under_edit"] += 1
        analyses.append(
            InputAnalysis(
                pair_sha256=str(seed["pair_sha256"]),
                input_id=str(seed["input_id"]),
                split=split,
                source=str(seed["source"]),
                length_bucket=str(seed["length_bucket"]),
                option=option,
            )
        )
    if len(analyses) != expected_count:
        raise ValueError(f"{split} input count is {len(analyses)}; expected {expected_count}")
    return analyses, funnel


def exact_count(total: int, fraction: float, description: str) -> int:
    """Convert one configured fraction to an exact integral count."""
    value = total * fraction
    if not value.is_integer():
        raise ValueError(f"{description} does not produce an integer count")
    return int(value)


def select_negative_types(
    analyses: list[InputAnalysis], selection: Mapping[str, object]
) -> tuple[dict[str, NegativeSelection], dict[str, dict[str, int]]]:
    """Assign exact 60/20/20 negative roles separately per KTO split."""
    seed = int(selection["seed"])
    selections: dict[str, NegativeSelection] = {}
    diagnostics: dict[str, dict[str, int]] = {}
    for split in ("train", "validation"):
        values = [analysis for analysis in analyses if analysis.split == split]
        under_target = exact_count(
            len(values), float(selection["generated_under_edit_fraction"]), f"{split} under-edit"
        )
        source_target = exact_count(
            len(values), float(selection["source_copy_fraction"]), f"{split} source-copy"
        )
        severe_target = exact_count(
            len(values), float(selection["severe_failure_fraction"]), f"{split} severe"
        )
        eligible = [value for value in values if value.option is not None]
        if len(eligible) < under_target:
            raise ValueError(
                f"{split} has {len(eligible)} inputs with eligible under-edits; {under_target} required"
            )
        eligible.sort(
            key=lambda value: (stable_score(seed, value.pair_sha256), value.pair_sha256)
        )
        under_pairs = {value.pair_sha256 for value in eligible[:under_target]}
        remaining = [value for value in values if value.pair_sha256 not in under_pairs]
        remaining.sort(
            key=lambda value: (stable_score(seed + 1, value.pair_sha256), value.pair_sha256)
        )
        source_pairs = {value.pair_sha256 for value in remaining[:source_target]}
        severe_values = remaining[source_target:]
        if len(severe_values) != severe_target:
            raise ValueError(f"{split} severe assignment count differs from target")
        severe_short_count = severe_target // 2
        for value in values:
            if value.pair_sha256 in under_pairs:
                selections[value.pair_sha256] = NegativeSelection(
                    "generated_under_edit", cast(UnderEditOption, value.option).chain_id
                )
            elif value.pair_sha256 in source_pairs:
                selections[value.pair_sha256] = NegativeSelection("source_copy", None)
        for index, value in enumerate(severe_values):
            negative_type = "severe_short" if index < severe_short_count else "severe_long_repetition"
            selections[value.pair_sha256] = NegativeSelection(negative_type, None)
        diagnostics[split] = {
            "input_count": len(values),
            "eligible_under_edit_supply": len(eligible),
            "selected_generated_under_edit": under_target,
            "selected_source_copy": source_target,
            "selected_severe_short": severe_short_count,
            "selected_severe_long_repetition": severe_target - severe_short_count,
        }
    if len(selections) != len(analyses):
        raise ValueError("negative assignments do not cover every input")
    return selections, diagnostics


def severe_shortening(source_text: str) -> str:
    """Create a deterministic truncation at roughly forty percent of source length."""
    stripped = source_text.strip()
    cut = max(1, int(len(stripped) * 0.40))
    shortened = stripped[:cut].rstrip()
    if len(shortened) >= len(stripped):
        raise ValueError("cannot create a severe shortening from this source")
    return shortened


def severe_expansion(source_text: str) -> str:
    """Create a deterministic two-copy expansion with obvious repetition."""
    stripped = source_text.strip()
    return f"{stripped}\n\n{stripped}"


def metric_summary(metrics: StructureMetrics) -> dict[str, object]:
    """Serialize the selector metrics needed for audit and validation."""
    return {
        "source_sentence_count": metrics.source_sentence_count,
        "rewrite_sentence_count": metrics.rewrite_sentence_count,
        "sentence_delta_abs": metrics.sentence_delta_abs,
        "relative_sentence_delta": round(metrics.relative_sentence_delta, 6),
        "cv_change": round(metrics.cv_change, 6),
        "length_ratio": round(metrics.length_ratio, 6),
        "edit_distance": round(metrics.edit_distance, 6),
        "rouge_l": round(metrics.rouge_l, 6),
        "content_recall": round(metrics.content_recall, 6),
        "repeated_fourgram_fraction": round(metrics.repeated_fourgram_fraction, 6),
    }


def build_training_record(
    messages: list[dict[str, object]], response: str, label: bool
) -> dict[str, object]:
    """Build one ms-swift KTO row with an independent assistant response."""
    return {
        "messages": [
            dict(messages[0]),
            dict(messages[1]),
            {"role": "assistant", "content": response},
        ],
        "label": label,
    }


def choose_review_ids(
    analyses: list[InputAnalysis],
    selections: Mapping[str, NegativeSelection],
    review_count: int,
    seed: int,
) -> set[str]:
    """Choose a deterministic review sample matching the negative mixture."""
    fractions = {
        "generated_under_edit": 0.60,
        "source_copy": 0.20,
        "severe_short": 0.10,
        "severe_long_repetition": 0.10,
    }
    selected: set[str] = set()
    for negative_type, fraction in fractions.items():
        target = exact_count(review_count, fraction, f"review/{negative_type}")
        values = [
            value
            for value in analyses
            if selections[value.pair_sha256].negative_type == negative_type
        ]
        values.sort(
            key=lambda value: (
                stable_score(seed + 2, f"{negative_type}:{value.pair_sha256}"),
                value.pair_sha256,
            )
        )
        if len(values) < target:
            raise ValueError(f"insufficient {negative_type} inputs for review")
        selected.update(value.pair_sha256 for value in values[:target])
    return selected


def resolve_negative(
    source_text: str,
    results: list[dict[str, object]],
    selection: NegativeSelection,
    under_policy: Mapping[str, object],
    severe_policy: Mapping[str, object],
) -> tuple[str, dict[str, object]]:
    """Materialize and revalidate the selected negative response."""
    if selection.negative_type == "generated_under_edit":
        if selection.chain_id is None:
            raise ValueError("generated under-edit selection lacks a chain ID")
        result = results[selection.chain_id]
        negative_text = str(result["rewrite"])
        metrics = calculate_metrics(source_text, negative_text)
        if not under_edit_is_eligible(metrics, under_policy):
            raise ValueError("selected under-edit no longer passes policy")
    elif selection.negative_type == "source_copy":
        negative_text = source_text
        metrics = calculate_metrics(source_text, negative_text)
    elif selection.negative_type == "severe_short":
        negative_text = severe_shortening(source_text)
        metrics = calculate_metrics(source_text, negative_text)
        if severe_failure_type(metrics, severe_policy) != "severe_short":
            raise ValueError("deterministic shortening did not cross the severe threshold")
    elif selection.negative_type == "severe_long_repetition":
        negative_text = severe_expansion(source_text)
        metrics = calculate_metrics(source_text, negative_text)
        if severe_failure_type(metrics, severe_policy) != "severe_long":
            raise ValueError("deterministic expansion did not cross the severe threshold")
    else:
        raise ValueError(f"unknown negative type: {selection.negative_type}")
    return negative_text, metric_summary(metrics)


def write_outputs(
    split_paths: Mapping[str, tuple[Path, Path]],
    output_paths: Mapping[str, Path],
    selections: Mapping[str, NegativeSelection],
    review_ids: set[str],
    positive_policy: Mapping[str, object],
    under_policy: Mapping[str, object],
    severe_policy: Mapping[str, object],
) -> dict[str, object]:
    """Stream aligned inputs and write KTO rows, index, and review sample."""
    counts: Counter[str] = Counter()
    strata: Counter[str] = Counter()
    seen: set[str] = set()
    with (
        output_paths["train"].open("x", encoding="utf-8") as train_file,
        output_paths["validation"].open("x", encoding="utf-8") as validation_file,
        output_paths["sample_index"].open("x", encoding="utf-8") as index_file,
        output_paths["review_sample"].open("x", encoding="utf-8") as review_file,
    ):
        for split in ("train", "validation"):
            seed_path, candidate_path = split_paths[split]
            expected = 4500 if split == "train" else 500
            for _line, seed, results in tqdm(
                iter_aligned(seed_path, candidate_path, split),
                total=expected,
                desc=f"Writing structure-first KTO {split}",
            ):
                pair_digest = str(seed["pair_sha256"])
                if pair_digest in seen:
                    raise ValueError("one pair appears in multiple KTO splits")
                seen.add(pair_digest)
                messages = cast(list[dict[str, object]], seed["messages"])
                source_text = str(messages[1]["content"])
                positive_text = str(seed["desirable_response"])
                positive_metrics = calculate_metrics(source_text, positive_text)
                positive_role = (
                    "held_out_humanize_structure_positive"
                    if positive_is_eligible(positive_metrics, positive_policy)
                    else "held_out_humanize_fallback_positive"
                )
                selection = selections[pair_digest]
                negative_text, negative_metrics = resolve_negative(
                    source_text, results, selection, under_policy, severe_policy
                )
                output_file = train_file if split == "train" else validation_file
                for label, role, response, metrics in (
                    (True, positive_role, positive_text, metric_summary(positive_metrics)),
                    (False, selection.negative_type, negative_text, negative_metrics),
                ):
                    output_file.write(
                        json.dumps(
                            build_training_record(messages, response, label),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
                    index_file.write(
                        json.dumps(
                            {
                                "input_id": seed["input_id"],
                                "source": seed["source"],
                                "split": split,
                                "length_bucket": seed["length_bucket"],
                                "label": label,
                                "response_role": role,
                                "source_sha256": seed["source_sha256"],
                                "target_sha256": seed["target_sha256"],
                                "pair_sha256": pair_digest,
                                "response_sha256": text_hash(response),
                                "selected_chain_id": selection.chain_id if not label else None,
                                "selection_metrics": metrics,
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
                    counts[f"{split}:{'positive' if label else 'negative'}"] += 1
                counts[f"{split}:{positive_role}"] += 1
                strata[f"{split}:{seed['source']}:{seed['length_bucket']}:{selection.negative_type}"] += 1
                if pair_digest in review_ids:
                    review_file.write(
                        json.dumps(
                            {
                                "input_id": seed["input_id"],
                                "source": seed["source"],
                                "split": split,
                                "length_bucket": seed["length_bucket"],
                                "messages": messages,
                                "desirable_response": positive_text,
                                "positive_role": positive_role,
                                "positive_metrics": metric_summary(positive_metrics),
                                "selected_negative": negative_text,
                                "negative_type": selection.negative_type,
                                "selected_chain_id": selection.chain_id,
                                "negative_metrics": negative_metrics,
                                "pair_sha256": pair_digest,
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
                    counts["review"] += 1
    return {
        "label_counts": dict(sorted(counts.items())),
        "negative_stratum_counts": dict(sorted(strata.items())),
        "unique_input_count": len(seen),
    }


def file_metadata(path: Path) -> dict[str, object]:
    """Return validated count, size, and SHA-256 for one generated JSONL."""
    record_count = sum(1 for _line, _record in iter_jsonl(path, path.name))
    return {
        "path": str(path.resolve()),
        "record_count": record_count,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def register_artifact(
    manifest_path: Path,
    bundle: Path,
    statistics_path: Path,
    outputs: Mapping[str, Mapping[str, object]],
    config_path: Path,
) -> None:
    """Register the mechanically built KTO artifact pending human review."""
    manifest = load_yaml(manifest_path, "manifest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("processed_data"), list):
        raise ValueError("manifest artifacts.processed_data must be a list")
    version_dir = manifest_path.resolve().parent

    def relative(path: object) -> str:
        return str(Path(str(path)).resolve().relative_to(version_dir))

    artifacts["processed_data"].append(
        {
            "id": bundle.name.replace("_", "-"),
            "status": "mechanically-selected-pending-human-review",
            "purpose": "humanize-positive-structure-first-kto-refresh-data",
            "source_id": "sft-kto-reservation-and-six-temperature-candidates",
            "path": relative(outputs["train"]["path"]),
            "statistics_path": relative(statistics_path),
            "format": "ms-swift-kto-jsonl",
            "created_at": datetime.now().astimezone().isoformat(),
            "record_count": outputs["train"]["record_count"],
            "size_bytes": outputs["train"]["size_bytes"],
            "sha256": outputs["train"]["sha256"],
            "statistics_sha256": sha256_file(statistics_path),
            "parameters": {
                "bundle_path": relative(bundle),
                "validation_path": relative(outputs["validation"]["path"]),
                "validation_record_count": outputs["validation"]["record_count"],
                "validation_sha256": outputs["validation"]["sha256"],
                "sample_index_path": relative(outputs["sample_index"]["path"]),
                "sample_index_record_count": outputs["sample_index"]["record_count"],
                "sample_index_sha256": outputs["sample_index"]["sha256"],
                "review_sample_path": relative(outputs["review_sample"]["path"]),
                "review_sample_record_count": outputs["review_sample"]["record_count"],
                "review_sample_sha256": outputs["review_sample"]["sha256"],
                "selector_config_path": str(config_path),
                "selector_config_sha256": sha256_file(config_path),
            },
        }
    )
    planned = manifest.get("planned_training")
    if isinstance(planned, dict) and isinstance(planned.get("stages"), list):
        for stage in planned["stages"]:
            if (
                isinstance(stage, dict)
                and stage.get("name") == "kto-structure-refresh-construction"
            ):
                stage["status"] = "completed"
    with manifest_path.open("w", encoding="utf-8") as output_file:
        yaml.safe_dump(manifest, output_file, allow_unicode=True, sort_keys=False)


def main() -> int:
    """Analyze candidate supply, build KTO rows, and register the artifact."""
    args = parse_args()
    started_at = datetime.now().astimezone().isoformat()
    print("target: kto-refresh-build")
    print(f"manifest: {args.manifest.resolve()}")
    print(f"started_at: {started_at}")
    temporary_dir: Path | None = None
    try:
        manifest = load_yaml(args.manifest, "manifest")
        version = manifest.get("version")
        if not isinstance(version, dict) or version.get("status") == "released":
            raise ValueError("released or invalid version cannot build data")
        config = load_yaml(args.config, "selector config")
        selection = config.get("selection")
        positive_policy = config.get("positive")
        under_policy = config.get("under_edit_negative")
        severe_policy = config.get("severe_failure_negative")
        if not all(
            isinstance(value, dict)
            for value in (selection, positive_policy, under_policy, severe_policy)
        ):
            raise ValueError("selector sections must be mappings")
        split_paths = {
            "train": (args.train_seed.resolve(), args.train_candidates.resolve()),
            "validation": (
                args.validation_seed.resolve(),
                args.validation_candidates.resolve(),
            ),
        }
        analyses: list[InputAnalysis] = []
        funnel: Counter[str] = Counter()
        for split, expected in ("train", 4500), ("validation", 500):
            split_analyses, split_funnel = analyze_split(
                split_paths[split][0],
                split_paths[split][1],
                split,
                expected,
                cast(Mapping[str, object], under_policy),
            )
            analyses.extend(split_analyses)
            funnel.update({f"{split}:{key}": value for key, value in split_funnel.items()})
        selections, diagnostics = select_negative_types(
            analyses, cast(Mapping[str, object], selection)
        )
        review_ids = choose_review_ids(
            analyses,
            selections,
            int(cast(Mapping[str, object], selection)["review_count"]),
            int(cast(Mapping[str, object], selection)["seed"]),
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"sft_humanize_structure_kto_{timestamp}"
        output_root = args.output_dir.resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        final_dir = output_root / bundle_name
        temporary_dir = output_root / f".{bundle_name}.tmp"
        temporary_dir.mkdir(exist_ok=False)
        filenames = {
            "train": "train.jsonl",
            "validation": "validation.jsonl",
            "sample_index": "sample_index.jsonl",
            "review_sample": "human_review_sample.jsonl",
        }
        temporary_paths = {name: temporary_dir / filename for name, filename in filenames.items()}
        final_paths = {name: final_dir / filename for name, filename in filenames.items()}
        summary = write_outputs(
            split_paths,
            temporary_paths,
            selections,
            review_ids,
            cast(Mapping[str, object], positive_policy),
            cast(Mapping[str, object], under_policy),
            cast(Mapping[str, object], severe_policy),
        )
        outputs = {name: file_metadata(path) for name, path in temporary_paths.items()}
        for name in outputs:
            outputs[name]["path"] = str(final_paths[name])
        expected_counts = {"train": 9000, "validation": 1000, "sample_index": 10000, "review_sample": 200}
        for name, expected in expected_counts.items():
            if outputs[name]["record_count"] != expected:
                raise ValueError(f"{name} count differs from expected {expected}")
        finished_at = datetime.now().astimezone().isoformat()
        statistics = {
            "version_id": args.manifest.resolve().parent.name,
            "target": "kto-refresh-build",
            "status": "success",
            "started_at": started_at,
            "finished_at": finished_at,
            "inputs": {
                split: {
                    "seed_path": str(paths[0]),
                    "seed_sha256": sha256_file(paths[0]),
                    "candidate_path": str(paths[1]),
                    "candidate_sha256": sha256_file(paths[1]),
                }
                for split, paths in split_paths.items()
            },
            "config": config,
            "candidate_funnel": dict(sorted(funnel.items())),
            "selection": diagnostics,
            "output_summary": summary,
            "outputs": outputs,
            "code_sha256": sha256_file(Path(__file__)),
            "limitations": [
                "Generated under-edits are mechanically selected and require the registered human review.",
                "Severe-short and severe-long negatives are deterministic truncation and duplication failures.",
                "No model inference, training, GPU task, or detector request was run locally.",
            ],
        }
        statistics_temp = temporary_dir / "statistics.yaml"
        with statistics_temp.open("x", encoding="utf-8") as output_file:
            yaml.safe_dump(statistics, output_file, allow_unicode=True, sort_keys=False)
        temporary_dir.rename(final_dir)
        temporary_dir = None
        statistics_path = final_dir / "statistics.yaml"
        register_artifact(args.manifest, final_dir, statistics_path, outputs, args.config)
        print(f"output_bundle: {final_dir}")
        print(f"selection: {diagnostics}")
        print(f"train_record_count: {outputs['train']['record_count']}")
        print(f"validation_record_count: {outputs['validation']['record_count']}")
        print(f"review_record_count: {outputs['review_sample']['record_count']}")
        print(f"statistics_sha256: {sha256_file(statistics_path)}")
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

"""Select one useful undesirable per seed and build balanced KTO data."""

import argparse
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
import hashlib
from itertools import zip_longest
import json
import math
from pathlib import Path
import re
import shutil
from typing import cast

from tqdm import tqdm
import yaml

from data_process.a_reserve_sft_for_kto import text_hash
from data_process.c_generate_kto_candidates import (
    load_yaml_mapping,
    sha256_file,
    validate_seed_record,
)


WORD_PATTERN = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
NUMBER_PATTERN = re.compile(r"(?<!\w)[+-]?\d[\d,.:/%\-]*")
URL_PATTERN = re.compile(r"https?://[^\s<>\]\[\"']+", re.IGNORECASE)
FORMAT_PATTERN = re.compile(r"(?m)^\s*(?:#{1,6}\s|[-*+]\s+|-\d+-\s*$)")
META_PHRASES = (
    "as an ai",
    "i cannot rewrite",
    "i can't rewrite",
    "here is the rewritten",
    "here's the rewritten",
    "rewritten version:",
)
NEGATIVE_TYPES = (
    "semantic_drift",
    "over_rewrite",
    "structure_damage",
    "fluency_contamination",
)


@dataclass(frozen=True)
class CandidateOption:
    """Compact metrics and eligible negative types for one generated candidate."""

    chain_id: int
    metrics: dict[str, object]
    eligible_types: tuple[str, ...]
    severity: float


@dataclass(frozen=True)
class InputAnalysis:
    """Identity, stratum, and compact candidate options for one KTO seed."""

    pair_sha256: str
    input_id: str
    split: str
    source: str
    length_bucket: str
    options: tuple[CandidateOption, ...]


@dataclass(frozen=True)
class SelectedNegative:
    """Final negative source and evidence assigned to one input."""

    negative_type: str
    chain_id: int | None
    metrics: dict[str, object]


def parse_args() -> argparse.Namespace:
    """Parse parameters supplied by the version Makefile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--train-seed", required=True, type=Path)
    parser.add_argument("--validation-seed", required=True, type=Path)
    parser.add_argument("--train-candidates", required=True, type=Path)
    parser.add_argument("--validation-candidates", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--inspect-only", action="store_true")
    return parser.parse_args()


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


def parse_selector_config(
    config: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, float]]:
    """Validate selection thresholds and exact top-level type ratios."""
    if config.get("schema_version") != 1:
        raise ValueError("selector schema_version must equal 1")
    selection = config.get("selection")
    gates = config.get("candidate_gates")
    rules = config.get("type_rules")
    targets = config.get("negative_type_targets")
    if not all(isinstance(value, dict) for value in (selection, gates, rules, targets)):
        raise ValueError("selector sections must be mappings")
    merged = {**cast(dict[str, object], selection), **cast(dict[str, object], gates), **cast(dict[str, object], rules)}
    required_numeric = (
        "source_copy_fraction",
        "minimum_length_ratio",
        "maximum_length_ratio",
        "minimum_source_token_recall",
        "maximum_repeated_fourgram_fraction",
        "semantic_max_source_token_recall",
        "over_rewrite_minimum_length_ratio",
        "over_rewrite_minimum_added_words",
        "over_rewrite_minimum_repeated_fourgram_fraction",
        "structure_minimum_paragraph_delta",
    )
    for name in required_numeric:
        if not isinstance(merged.get(name), (int, float)):
            raise ValueError(f"selector {name} must be numeric")
    if not isinstance(merged.get("seed"), int):
        raise ValueError("selector seed must be an integer")
    if not isinstance(merged.get("review_count_per_negative_type"), int):
        raise ValueError("review_count_per_negative_type must be an integer")
    type_targets: dict[str, float] = {}
    if set(cast(dict[str, object], targets)) != set(NEGATIVE_TYPES):
        raise ValueError("negative_type_targets must name the four candidate types")
    for name in NEGATIVE_TYPES:
        value = cast(dict[str, object], targets)[name]
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"invalid negative type target: {name}")
        type_targets[name] = float(value)
    if not math.isclose(
        float(merged["source_copy_fraction"]) + sum(type_targets.values()), 1.0
    ):
        raise ValueError("source-copy and candidate-type fractions must sum to one")
    return merged, type_targets


def word_tokens(text: str) -> list[str]:
    """Return normalized word-like tokens for lightweight fidelity proxies."""
    return [match.group(0).casefold() for match in WORD_PATTERN.finditer(text)]


def token_overlap(source_tokens: list[str], candidate_tokens: list[str]) -> tuple[float, float, float]:
    """Return multiset recall, precision, and F1 without quadratic alignment."""
    source_counts = Counter(source_tokens)
    candidate_counts = Counter(candidate_tokens)
    overlap = sum(
        min(count, candidate_counts.get(token, 0))
        for token, count in source_counts.items()
    )
    recall = overlap / len(source_tokens) if source_tokens else 0.0
    precision = overlap / len(candidate_tokens) if candidate_tokens else 0.0
    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    return recall, precision, f1


def paragraph_count(text: str) -> int:
    """Count non-empty paragraphs separated by blank lines."""
    return len([part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()])


def repeated_fourgram_fraction(tokens: list[str]) -> float:
    """Measure repeated four-gram mass as a lightweight repetition proxy."""
    if len(tokens) < 4:
        return 0.0
    grams = [tuple(tokens[index : index + 4]) for index in range(len(tokens) - 3)]
    counts = Counter(grams)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return repeated / len(grams)


def script_counts(text: str) -> Counter[str]:
    """Count major letter scripts used to detect introduced-language contamination."""
    counts: Counter[str] = Counter()
    for character in text:
        codepoint = ord(character)
        if character.isascii() and character.isalpha():
            counts["latin"] += 1
        elif 0x00C0 <= codepoint <= 0x024F:
            counts["latin"] += 1
        elif 0x0400 <= codepoint <= 0x052F:
            counts["cyrillic"] += 1
        elif 0x0370 <= codepoint <= 0x03FF:
            counts["greek"] += 1
        elif 0x0600 <= codepoint <= 0x06FF:
            counts["arabic"] += 1
        elif 0x0900 <= codepoint <= 0x097F:
            counts["devanagari"] += 1
        elif 0x3040 <= codepoint <= 0x30FF or 0x3400 <= codepoint <= 0x9FFF:
            counts["cjk"] += 1
    return counts


def anchor_set(pattern: re.Pattern[str], text: str) -> set[str]:
    """Return normalized literal anchors matched by one pattern."""
    return {match.group(0).casefold().rstrip(".,;:)") for match in pattern.finditer(text)}


def candidate_metrics(
    source_text: str,
    target_text: str,
    candidate_text: str,
) -> dict[str, object]:
    """Calculate cheap, deterministic fidelity and structural proxies."""
    source_words = word_tokens(source_text)
    target_words = word_tokens(target_text)
    candidate_words = word_tokens(candidate_text)
    recall, precision, f1 = token_overlap(source_words, candidate_words)
    _target_recall, _target_precision, target_f1 = token_overlap(target_words, candidate_words)
    source_paragraphs = paragraph_count(source_text)
    candidate_paragraphs = paragraph_count(candidate_text)
    source_scripts = script_counts(source_text)
    candidate_scripts = script_counts(candidate_text)
    introduced_scripts = sorted(
        script
        for script, count in candidate_scripts.items()
        if count >= 2 and source_scripts.get(script, 0) == 0
    )
    source_numbers = anchor_set(NUMBER_PATTERN, source_text)
    candidate_numbers = anchor_set(NUMBER_PATTERN, candidate_text)
    source_urls = anchor_set(URL_PATTERN, source_text)
    candidate_urls = anchor_set(URL_PATTERN, candidate_text)
    length_ratio = len(candidate_words) / len(source_words) if source_words else 0.0
    source_format_count = len(FORMAT_PATTERN.findall(source_text))
    candidate_format_count = len(FORMAT_PATTERN.findall(candidate_text))
    source_complete = source_text.rstrip().endswith(tuple(".!?。！？\"'”’)]}"))
    candidate_complete = candidate_text.rstrip().endswith(tuple(".!?。！？\"'”’)]}"))
    return {
        "source_word_count": len(source_words),
        "candidate_word_count": len(candidate_words),
        "added_word_count": len(candidate_words) - len(source_words),
        "length_ratio": round(length_ratio, 6),
        "source_token_recall": round(recall, 6),
        "source_token_precision": round(precision, 6),
        "source_token_f1": round(f1, 6),
        "target_token_f1": round(target_f1, 6),
        "source_paragraph_count": source_paragraphs,
        "candidate_paragraph_count": candidate_paragraphs,
        "paragraph_delta": candidate_paragraphs - source_paragraphs,
        "number_mismatch": source_numbers != candidate_numbers,
        "url_mismatch": source_urls != candidate_urls,
        "introduced_scripts": introduced_scripts,
        "introduced_format_artifact": candidate_format_count > source_format_count,
        "incomplete_ending": source_complete and not candidate_complete,
        "repeated_fourgram_fraction": round(repeated_fourgram_fraction(candidate_words), 6),
        "meta_or_refusal": any(phrase in candidate_text.casefold() for phrase in META_PHRASES),
        "exact_source": " ".join(source_words) == " ".join(candidate_words),
        "exact_target": " ".join(target_words) == " ".join(candidate_words),
    }


def classify_candidate(
    metrics: Mapping[str, object],
    policy: Mapping[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...], float]:
    """Return eligible negative types, failed gates, and a lower-is-harder severity."""
    failures: list[str] = []
    ratio = float(metrics["length_ratio"])
    recall = float(metrics["source_token_recall"])
    repetition = float(metrics["repeated_fourgram_fraction"])
    if ratio < float(policy["minimum_length_ratio"]):
        failures.append("candidate_too_short")
    if ratio > float(policy["maximum_length_ratio"]):
        failures.append("candidate_too_long")
    if recall < float(policy["minimum_source_token_recall"]):
        failures.append("candidate_overlap_too_low")
    if repetition > float(policy["maximum_repeated_fourgram_fraction"]):
        failures.append("candidate_repetition_too_high")
    if metrics["exact_source"]:
        failures.append("candidate_exact_source")
    if metrics["exact_target"]:
        failures.append("candidate_exact_target")
    if policy.get("reject_meta_or_refusal") is True and metrics["meta_or_refusal"]:
        failures.append("candidate_meta_or_refusal")
    if failures:
        return (), tuple(failures), 100.0

    eligible: list[str] = []
    if (
        metrics["number_mismatch"]
        or metrics["url_mismatch"]
        or recall <= float(policy["semantic_max_source_token_recall"])
    ):
        eligible.append("semantic_drift")
    if (
        ratio >= float(policy["over_rewrite_minimum_length_ratio"])
        or int(metrics["added_word_count"]) >= int(policy["over_rewrite_minimum_added_words"])
        or repetition >= float(policy["over_rewrite_minimum_repeated_fourgram_fraction"])
    ):
        eligible.append("over_rewrite")
    if (
        abs(int(metrics["paragraph_delta"]))
        >= int(policy["structure_minimum_paragraph_delta"])
        or metrics["introduced_format_artifact"]
    ):
        eligible.append("structure_damage")
    if (
        bool(metrics["introduced_scripts"])
        or metrics["introduced_format_artifact"]
        or metrics["incomplete_ending"]
    ):
        eligible.append("fluency_contamination")
    severity = (
        abs(math.log(max(ratio, 1e-6))) * 1.5
        + (1.0 - recall) * 2.0
        + repetition * 2.0
        + abs(int(metrics["paragraph_delta"])) * 0.1
        + (0.25 if metrics["number_mismatch"] else 0.0)
        + (0.25 if metrics["url_mismatch"] else 0.0)
        + (0.3 if metrics["introduced_scripts"] else 0.0)
    )
    return tuple(eligible), (), round(severity, 6)


def validate_candidate_record(
    record: Mapping[str, object],
    seed_record: Mapping[str, object],
    split: str,
    line_number: int,
) -> list[dict[str, object]]:
    """Validate candidate identity, generation shape, and non-empty results."""
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
    for name in (
        "input_id",
        "source",
        "split",
        "length_bucket",
        "source_sha256",
        "target_sha256",
        "pair_sha256",
    ):
        if record[name] != seed_record[name]:
            raise ValueError(f"candidate {name} mismatch at {split}:{line_number}")
    num_results = record["num_results"]
    if record["rounds"] != 2 or num_results not in {3, 5, 6}:
        raise ValueError(f"candidate generation shape mismatch at {split}:{line_number}")
    results = record["results"]
    if not isinstance(results, list) or len(results) != num_results:
        raise ValueError(
            f"candidate results must contain {num_results} rows at {split}:{line_number}"
        )
    typed_results: list[dict[str, object]] = []
    for chain_id, result in enumerate(results):
        if not isinstance(result, dict) or result.get("chain_id") != chain_id:
            raise ValueError(f"candidate chain order mismatch at {split}:{line_number}")
        if not isinstance(result.get("rewrite"), str) or not str(result["rewrite"]).strip():
            raise ValueError(f"empty candidate rewrite at {split}:{line_number}")
        typed_results.append(result)
    return typed_results


def iter_aligned(
    seed_path: Path,
    candidate_path: Path,
    split: str,
) -> Iterator[tuple[int, dict[str, object], list[dict[str, object]]]]:
    """Stream exact seed/candidate pairs and reject count or identity drift."""
    seed_iterator = iter_jsonl(seed_path, f"{split} seed")
    candidate_iterator = iter_jsonl(candidate_path, f"{split} candidates")
    for pair in zip_longest(seed_iterator, candidate_iterator):
        if pair[0] is None or pair[1] is None:
            raise ValueError(f"{split} seed and candidate counts differ")
        (seed_line, seed), (candidate_line, candidate) = cast(tuple, pair)
        if seed_line != candidate_line:
            raise ValueError(f"{split} line numbers are not aligned")
        validate_seed_record(seed, split, seed_line)
        results = validate_candidate_record(candidate, seed, split, candidate_line)
        yield seed_line, seed, results


def analyze_split(
    seed_path: Path,
    candidate_path: Path,
    split: str,
    policy: Mapping[str, object],
    expected_count: int,
) -> tuple[list[InputAnalysis], Counter[str]]:
    """Analyze all candidates while retaining only compact metrics and identities."""
    analyses: list[InputAnalysis] = []
    funnel: Counter[str] = Counter()
    for line_number, seed, results in tqdm(
        iter_aligned(seed_path, candidate_path, split),
        total=expected_count,
        desc=f"Analyzing KTO {split} candidates",
    ):
        messages = cast(list[dict[str, object]], seed["messages"])
        source_text = str(messages[1]["content"])
        target_text = str(seed["desirable_response"])
        options: list[CandidateOption] = []
        for result in results:
            metrics = candidate_metrics(source_text, target_text, str(result["rewrite"]))
            eligible, failures, severity = classify_candidate(metrics, policy)
            if failures:
                for failure in failures:
                    funnel[f"dropped:{failure}"] += 1
            if not eligible:
                funnel["candidate:no_supported_negative_type"] += 1
            for negative_type in eligible:
                funnel[f"eligible:{negative_type}"] += 1
            options.append(
                CandidateOption(
                    chain_id=int(result["chain_id"]),
                    metrics=metrics,
                    eligible_types=eligible,
                    severity=severity,
                )
            )
            funnel["candidate:scanned"] += 1
        if not any(option.eligible_types for option in options):
            funnel["input:no_eligible_candidate"] += 1
        funnel["input:scanned"] += 1
        analyses.append(
            InputAnalysis(
                pair_sha256=str(seed["pair_sha256"]),
                input_id=str(seed["input_id"]),
                split=split,
                source=str(seed["source"]),
                length_bucket=str(seed["length_bucket"]),
                options=tuple(options),
            )
        )
    if len(analyses) != expected_count:
        raise ValueError(f"{split} input count is {len(analyses)}; expected {expected_count}")
    if len({analysis.pair_sha256 for analysis in analyses}) != len(analyses):
        raise ValueError(f"duplicate pair hashes in {split}")
    return analyses, funnel


def stable_score(seed: int, identity: str) -> int:
    """Return a deterministic pseudo-random rank."""
    return int.from_bytes(hashlib.sha256(f"{seed}:{identity}".encode()).digest(), "big")


def exact_target(total: int, fraction: float, description: str) -> int:
    """Convert one configured fraction to an exact integral count."""
    value = total * fraction
    if not value.is_integer():
        raise ValueError(f"{description} does not produce an integer count")
    return int(value)


def choose_source_copy_inputs(
    analyses: list[InputAnalysis],
    fraction: float,
    seed: int,
) -> set[str]:
    """Select an exact per-split quota while keeping strata as balanced as possible."""
    selected: set[str] = set()
    for split in ("train", "validation"):
        split_values = [item for item in analyses if item.split == split]
        target = exact_target(
            len(split_values), fraction, f"source-copy quota for {split}"
        )
        strata: dict[tuple[str, str], list[InputAnalysis]] = {}
        for analysis in split_values:
            strata.setdefault((analysis.source, analysis.length_bucket), []).append(
                analysis
            )
        queues: dict[tuple[str, str], list[InputAnalysis]] = {}
        selected_by_stratum: Counter[tuple[str, str]] = Counter()
        for key, values in strata.items():
            unusable = [
                item
                for item in values
                if not any(option.eligible_types for option in item.options)
            ]
            usable = [item for item in values if item not in unusable]
            unusable.sort(
                key=lambda item: (stable_score(seed, item.pair_sha256), item.pair_sha256)
            )
            usable.sort(
                key=lambda item: (stable_score(seed, item.pair_sha256), item.pair_sha256)
            )
            selected.update(item.pair_sha256 for item in unusable)
            selected_by_stratum[key] = len(unusable)
            queues[key] = usable
        split_selected_count = sum(selected_by_stratum.values())
        if split_selected_count > target:
            raise ValueError(
                f"source-copy quota for {split} cannot cover {split_selected_count} "
                f"inputs without eligible candidates; quota is {target}"
            )
        while split_selected_count < target:
            available_strata = [key for key, queue in queues.items() if queue]
            if not available_strata:
                raise ValueError(f"source-copy allocation exhausted inputs for {split}")
            # Pick the most underrepresented stratum at each step. Strata with many
            # unusable candidates naturally stay above their nominal 20% share.
            key = min(
                available_strata,
                key=lambda item: (
                    selected_by_stratum[item] / (len(strata[item]) * fraction),
                    stable_score(seed + 7, f"{split}:{item[0]}:{item[1]}"),
                    item,
                ),
            )
            chosen = queues[key].pop(0)
            selected.add(chosen.pair_sha256)
            selected_by_stratum[key] += 1
            split_selected_count += 1
    return selected


def best_option_for_type(
    analysis: InputAnalysis,
    negative_type: str,
) -> CandidateOption | None:
    """Return the least damaged candidate that still proves one negative type."""
    eligible = [
        option for option in analysis.options if negative_type in option.eligible_types
    ]
    return min(eligible, key=lambda option: (option.severity, option.chain_id), default=None)


def select_negatives(
    analyses: list[InputAnalysis],
    policy: Mapping[str, object],
    type_targets: Mapping[str, float],
) -> tuple[dict[str, SelectedNegative], dict[str, dict[str, int]]]:
    """Assign exact label/type counts separately in train and validation."""
    seed = int(policy["seed"])
    source_copy_pairs = choose_source_copy_inputs(
        analyses, float(policy["source_copy_fraction"]), seed
    )
    selections: dict[str, SelectedNegative] = {
        pair_digest: SelectedNegative(
            negative_type="source_copy",
            chain_id=None,
            metrics={
                "selection_reason": "original_ai_input_as_under_edit_negative",
                "length_ratio": 1.0,
                "source_token_recall": 1.0,
            },
        )
        for pair_digest in source_copy_pairs
    }
    diagnostics: dict[str, dict[str, int]] = {}
    for split in ("train", "validation"):
        split_analyses = [analysis for analysis in analyses if analysis.split == split]
        candidate_pool = [
            analysis
            for analysis in split_analyses
            if analysis.pair_sha256 not in source_copy_pairs
        ]
        targets = {
            negative_type: exact_target(
                len(split_analyses), fraction, f"{split}/{negative_type} target"
            )
            for negative_type, fraction in type_targets.items()
        }
        supply = {
            negative_type: sum(
                best_option_for_type(analysis, negative_type) is not None
                for analysis in candidate_pool
            )
            for negative_type in NEGATIVE_TYPES
        }
        # These signals overlap heavily. Reserve scarce/specific classes first and
        # let broad semantic-drift evidence absorb the remaining candidate pool.
        order = (
            "fluency_contamination",
            "structure_damage",
            "over_rewrite",
            "semantic_drift",
        )
        assigned: set[str] = set()
        selected_counts: Counter[str] = Counter()
        for negative_type in order:
            ranked: list[tuple[float, int, str, CandidateOption]] = []
            for analysis in candidate_pool:
                if analysis.pair_sha256 in assigned:
                    continue
                option = best_option_for_type(analysis, negative_type)
                if option is None:
                    continue
                ranked.append(
                    (
                        option.severity,
                        stable_score(seed + 1, f"{analysis.pair_sha256}:{negative_type}"),
                        analysis.pair_sha256,
                        option,
                    )
                )
            ranked.sort()
            take_count = min(len(ranked), targets[negative_type])
            for _severity, _rank, pair_digest, option in ranked[:take_count]:
                selections[pair_digest] = SelectedNegative(
                    negative_type=negative_type,
                    chain_id=option.chain_id,
                    metrics=option.metrics,
                )
                assigned.add(pair_digest)
                selected_counts[negative_type] += 1

        remaining = [
            analysis
            for analysis in candidate_pool
            if analysis.pair_sha256 not in assigned
        ]
        remaining.sort(
            key=lambda item: (stable_score(seed + 3, item.pair_sha256), item.pair_sha256)
        )
        for analysis in remaining:
            available: list[tuple[float, float, str, int, CandidateOption]] = []
            for option in analysis.options:
                for negative_type in option.eligible_types:
                    target = max(targets[negative_type], 1)
                    available.append(
                        (
                            selected_counts[negative_type] / target,
                            option.severity,
                            negative_type,
                            option.chain_id,
                            option,
                        )
                    )
            if not available:
                raise ValueError(
                    f"{split} input {analysis.input_id} has no usable candidate "
                    "after source-copy allocation"
                )
            _ratio, _severity, negative_type, _chain_id, option = min(available)
            selections[analysis.pair_sha256] = SelectedNegative(
                negative_type=negative_type,
                chain_id=option.chain_id,
                metrics=option.metrics,
            )
            assigned.add(analysis.pair_sha256)
            selected_counts[negative_type] += 1
        if len(assigned) != len(candidate_pool):
            raise ValueError(f"{split} soft assignments do not cover every non-source input")
        diagnostics[split] = {
            **{f"supply:{name}": supply[name] for name in NEGATIVE_TYPES},
            **{f"target:{name}": targets[name] for name in NEGATIVE_TYPES},
            **{f"selected:{name}": selected_counts[name] for name in NEGATIVE_TYPES},
            "selected:source_copy": sum(
                pair in source_copy_pairs for pair in (item.pair_sha256 for item in split_analyses)
            ),
        }
        for analysis in split_analyses:
            stratum = f"{analysis.source}:{analysis.length_bucket}"
            diagnostics[split][f"input:{stratum}"] = (
                diagnostics[split].get(f"input:{stratum}", 0) + 1
            )
            if analysis.pair_sha256 in source_copy_pairs:
                diagnostics[split][f"selected:source_copy:{stratum}"] = (
                    diagnostics[split].get(f"selected:source_copy:{stratum}", 0) + 1
                )
    if len(selections) != len(analyses):
        raise ValueError("negative selection count differs from input count")
    return selections, diagnostics


def print_diagnostics(
    funnel: Mapping[str, int],
    diagnostics: Mapping[str, Mapping[str, int]],
) -> None:
    """Print compact supply, target, and funnel summaries."""
    print("candidate_funnel:")
    for name, count in sorted(funnel.items()):
        print(f"  {name:<48} {count:>7}")
    print("selection_supply:")
    for split, values in diagnostics.items():
        print(f"  split={split}")
        for negative_type in ("source_copy", *NEGATIVE_TYPES):
            supply = values.get(f"supply:{negative_type}", "-")
            target = values.get(f"target:{negative_type}", values.get(f"selected:{negative_type}", 0))
            selected = values.get(f"selected:{negative_type}", 0)
            print(
                f"    {negative_type:<24} supply={str(supply):>5} "
                f"target={target:>5} selected={selected:>5}"
            )


def build_training_record(
    messages: list[dict[str, object]],
    response: str,
    label: bool,
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


def review_pair_ids(
    analyses: list[InputAnalysis],
    selections: Mapping[str, SelectedNegative],
    count_per_type: int,
    seed: int,
) -> set[str]:
    """Choose an exact deterministic review sample from every selected negative type."""
    selected: set[str] = set()
    for negative_type in ("source_copy", *NEGATIVE_TYPES):
        candidates = [
            analysis
            for analysis in analyses
            if selections[analysis.pair_sha256].negative_type == negative_type
        ]
        if len(candidates) < count_per_type:
            raise ValueError(f"insufficient {negative_type} rows for review sample")
        ordered = sorted(
            candidates,
            key=lambda item: (
                stable_score(seed + 2, f"{negative_type}:{item.pair_sha256}"),
                item.pair_sha256,
            ),
        )
        selected.update(item.pair_sha256 for item in ordered[:count_per_type])
    return selected


def write_outputs(
    split_paths: Mapping[str, tuple[Path, Path]],
    output_paths: Mapping[str, Path],
    selections: Mapping[str, SelectedNegative],
    review_ids: set[str],
) -> dict[str, object]:
    """Stream aligned inputs again and write KTO rows, indexes, and review records."""
    counts: Counter[str] = Counter()
    selected_types: Counter[str] = Counter()
    seen_pairs: set[str] = set()
    with (
        output_paths["train"].open("x", encoding="utf-8") as train_file,
        output_paths["validation"].open("x", encoding="utf-8") as validation_file,
        output_paths["sample_index"].open("x", encoding="utf-8") as index_file,
        output_paths["review_sample"].open("x", encoding="utf-8") as review_file,
    ):
        for split in ("train", "validation"):
            seed_path, candidate_path = split_paths[split]
            expected_count = 4500 if split == "train" else 500
            for _line, seed, results in tqdm(
                iter_aligned(seed_path, candidate_path, split),
                total=expected_count,
                desc=f"Writing KTO {split}",
            ):
                pair_digest = str(seed["pair_sha256"])
                if pair_digest in seen_pairs:
                    raise ValueError("one pair appears in multiple KTO splits")
                seen_pairs.add(pair_digest)
                selection = selections[pair_digest]
                messages = cast(list[dict[str, object]], seed["messages"])
                source_text = str(messages[1]["content"])
                positive_text = str(seed["desirable_response"])
                if selection.chain_id is None:
                    negative_text = source_text
                else:
                    result = results[selection.chain_id]
                    if result["chain_id"] != selection.chain_id:
                        raise ValueError("selected chain no longer aligns with candidates")
                    negative_text = str(result["rewrite"])
                output_file = train_file if split == "train" else validation_file
                for label, role, response in (
                    (True, "held_out_human_positive", positive_text),
                    (False, selection.negative_type, negative_text),
                ):
                    output_file.write(
                        json.dumps(
                            build_training_record(messages, response, label),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
                    index_record = {
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
                        "selected_chain_id": selection.chain_id,
                        "selection_metrics": selection.metrics if not label else None,
                    }
                    index_file.write(
                        json.dumps(index_record, ensure_ascii=False, separators=(",", ":"))
                        + "\n"
                    )
                    counts[f"{split}:{'positive' if label else 'negative'}"] += 1
                selected_types[f"{split}:{selection.negative_type}"] += 1
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
                                "selected_negative": negative_text,
                                "negative_type": selection.negative_type,
                                "selected_chain_id": selection.chain_id,
                                "selection_metrics": selection.metrics,
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
        "selected_type_counts": dict(sorted(selected_types.items())),
        "unique_input_count": len(seen_pairs),
    }


def count_jsonl(path: Path) -> int:
    """Count non-empty JSONL rows while validating JSON syntax."""
    return sum(1 for _line, _record in iter_jsonl(path, path.name))


def file_metadata(path: Path) -> dict[str, object]:
    """Return validated file count, size, and SHA-256."""
    return {
        "path": str(path.resolve()),
        "record_count": count_jsonl(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def input_metadata(path: Path) -> dict[str, object]:
    """Return immutable metadata for one source file."""
    return {
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def register_artifact(
    manifest_path: Path,
    bundle: Path,
    statistics_path: Path,
    statistics_sha256: str,
    outputs: Mapping[str, Mapping[str, object]],
    config_path: Path,
) -> None:
    """Register one mechanically selected, review-blocked KTO artifact."""
    manifest = load_yaml_mapping(manifest_path, "manifest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("processed_data"), list):
        raise ValueError("manifest artifacts.processed_data must be a list")
    version_dir = manifest_path.resolve().parent

    def relative(path_value: object) -> str:
        return str(Path(str(path_value)).resolve().relative_to(version_dir))

    artifact = {
        "id": bundle.name.replace("_", "-"),
        "status": "mechanically-selected-pending-human-review",
        "purpose": "balanced-held-out-sft-derived-kto-training-and-validation-data",
        "source_id": "crawl-private-sft-snapshot",
        "path": relative(outputs["train"]["path"]),
        "statistics_path": relative(statistics_path),
        "format": "ms-swift-kto-jsonl",
        "created_at": datetime.now().astimezone().isoformat(),
        "record_count": outputs["train"]["record_count"],
        "size_bytes": outputs["train"]["size_bytes"],
        "sha256": outputs["train"]["sha256"],
        "statistics_sha256": statistics_sha256,
        "parameters": {
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
            "bundle_path": relative(bundle),
        },
    }
    artifacts["processed_data"].append(artifact)
    planned = manifest.get("planned_training")
    if isinstance(planned, dict) and isinstance(planned.get("stages"), list):
        for stage in planned["stages"]:
            if isinstance(stage, dict) and stage.get("name") == "kto-negative-selection-and-review":
                stage["status"] = "completed"
    with manifest_path.open("w", encoding="utf-8") as output_file:
        yaml.safe_dump(manifest, output_file, allow_unicode=True, sort_keys=False)


def main() -> int:
    """Inspect candidates or build the balanced review-blocked KTO artifact."""
    args = parse_args()
    target = "kto-negative-inspect" if args.inspect_only else "kto-negative-build"
    started_at = datetime.now().astimezone().isoformat()
    print(f"target: {target}")
    print(f"manifest: {args.manifest.resolve()}")
    print(f"started_at: {started_at}")
    temporary_dir: Path | None = None
    try:
        manifest = load_yaml_mapping(args.manifest, "manifest")
        version = manifest.get("version")
        if not isinstance(version, dict) or version.get("status") == "released":
            raise ValueError("released or invalid version cannot build data")
        config = load_yaml_mapping(args.config, "selector config")
        policy, type_targets = parse_selector_config(config)
        split_paths = {
            "train": (args.train_seed.resolve(), args.train_candidates.resolve()),
            "validation": (
                args.validation_seed.resolve(),
                args.validation_candidates.resolve(),
            ),
        }
        analyses: list[InputAnalysis] = []
        funnel: Counter[str] = Counter()
        for split, expected in (("train", 4500), ("validation", 500)):
            split_analyses, split_funnel = analyze_split(
                *split_paths[split], split, policy, expected
            )
            analyses.extend(split_analyses)
            funnel.update(split_funnel)
        if len({analysis.pair_sha256 for analysis in analyses}) != 5000:
            raise ValueError("train and validation pair hashes are not disjoint")
        selections, diagnostics = select_negatives(analyses, policy, type_targets)
        print_diagnostics(funnel, diagnostics)
        if args.inspect_only:
            print("status: success")
            print(f"finished_at: {datetime.now().astimezone().isoformat()}")
            return 0

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"sft_heldout_kto_{timestamp}"
        output_root = args.output_dir.resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        bundle = output_root / bundle_name
        temporary_dir = output_root / f".{bundle_name}.tmp"
        temporary_dir.mkdir(exist_ok=False)
        temporary_paths = {
            "train": temporary_dir / "train.jsonl",
            "validation": temporary_dir / "validation.jsonl",
            "sample_index": temporary_dir / "sample_index.jsonl",
            "review_sample": temporary_dir / "review_sample.jsonl",
        }
        review_ids = review_pair_ids(
            analyses,
            selections,
            int(policy["review_count_per_negative_type"]),
            int(policy["seed"]),
        )
        summary = write_outputs(split_paths, temporary_paths, selections, review_ids)
        outputs = {name: file_metadata(path) for name, path in temporary_paths.items()}
        expected_output_counts = {
            "train": 9000,
            "validation": 1000,
            "sample_index": 10000,
            "review_sample": 150,
        }
        for name, expected in expected_output_counts.items():
            if outputs[name]["record_count"] != expected:
                raise ValueError(f"{name} count differs from expected {expected}")
        final_paths = {name: bundle / path.name for name, path in temporary_paths.items()}
        for name, metadata in outputs.items():
            metadata["path"] = str(final_paths[name])
        finished_at = datetime.now().astimezone().isoformat()
        statistics = {
            "version_id": args.manifest.resolve().parent.name,
            "target": "kto-negative-build",
            "manifest": str(args.manifest.resolve()),
            "started_at": started_at,
            "finished_at": finished_at,
            "status": "success",
            "inputs": {
                "train_seed": input_metadata(args.train_seed),
                "validation_seed": input_metadata(args.validation_seed),
                "train_candidates": input_metadata(args.train_candidates),
                "validation_candidates": input_metadata(args.validation_candidates),
                "selector_config": input_metadata(args.config),
            },
            "config": config,
            "candidate_funnel": dict(sorted(funnel.items())),
            "selection": diagnostics,
            "output_summary": summary,
            "outputs": outputs,
            "code_sha256": {
                "code/data_process/d_select_kto_negatives.py": sha256_file(Path(__file__))
            },
            "limitations": [
                "Literal anchors and token overlap are proxies and do not prove semantic correctness.",
                "The 150-input negative-type-stratified sample requires human review before training.",
                "No model inference, detector request, training, or GPU task was run.",
            ],
        }
        statistics_temp = temporary_dir / "statistics.yaml"
        with statistics_temp.open("x", encoding="utf-8") as output_file:
            yaml.safe_dump(statistics, output_file, allow_unicode=True, sort_keys=False)
        temporary_dir.rename(bundle)
        temporary_dir = None
        statistics_path = bundle / "statistics.yaml"
        statistics_sha256 = sha256_file(statistics_path)
        register_artifact(
            args.manifest,
            bundle,
            statistics_path,
            statistics_sha256,
            outputs,
            args.config,
        )
        print(f"output_bundle: {bundle}")
        print("train_record_count: 9000")
        print("validation_record_count: 1000")
        print("review_sample_record_count: 150")
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

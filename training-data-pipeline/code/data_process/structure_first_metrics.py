"""Measure sentence restructuring and classify structure-first KTO candidates."""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
import re
import unicodedata


TOKEN_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]|[^\W_]+", re.UNICODE)
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[。！？])|(?<=[.!?])\s+")
META_PHRASES = (
    "as an ai",
    "i cannot rewrite",
    "i can't rewrite",
    "here is the rewritten",
    "here's the rewritten",
    "rewritten version:",
)


@dataclass(frozen=True)
class StructureMetrics:
    """Sentence, lexical, and output-shape metrics for one rewrite."""

    source_sentence_count: int
    rewrite_sentence_count: int
    sentence_delta_abs: int
    relative_sentence_delta: float
    source_cv: float
    rewrite_cv: float
    cv_change: float
    source_token_count: int
    rewrite_token_count: int
    length_ratio: float
    edit_distance: float
    rouge_l: float
    content_recall: float
    repeated_fourgram_fraction: float
    meta_or_refusal: bool
    introduced_scripts: tuple[str, ...]
    incomplete_ending: bool


def metric_tokens(text: str) -> list[str]:
    """Tokenize words and CJK characters for multilingual overlap metrics."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return TOKEN_PATTERN.findall(normalized)


def split_sentences(text: str) -> list[str]:
    """Split punctuation-delimited sentences and drop empty fragments."""
    return [
        fragment.strip()
        for fragment in SENTENCE_BOUNDARY_PATTERN.split(text)
        if metric_tokens(fragment)
    ]


def coefficient_of_variation(lengths: Sequence[int]) -> float:
    """Return sentence-length standard deviation divided by its mean."""
    if len(lengths) < 2:
        return 0.0
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.0
    variance = sum((value - mean) ** 2 for value in lengths) / len(lengths)
    return variance**0.5 / mean


def levenshtein_distance(source_text: str, target_text: str) -> int:
    """Return exact character-level Levenshtein distance using a bit vector."""
    if len(source_text) > len(target_text):
        source_text, target_text = target_text, source_text
    pattern_length = len(source_text)
    if pattern_length == 0:
        return len(target_text)
    masks: dict[str, int] = {}
    for index, character in enumerate(source_text):
        masks[character] = masks.get(character, 0) | (1 << index)
    active_mask = (1 << pattern_length) - 1
    last_bit = 1 << (pattern_length - 1)
    positive = active_mask
    negative = 0
    distance = pattern_length
    for character in target_text:
        matches = masks.get(character, 0)
        vertical = matches | negative
        horizontal = (((matches & positive) + positive) ^ positive) | matches
        positive_horizontal = negative | ~(horizontal | positive)
        negative_horizontal = positive & horizontal
        if positive_horizontal & last_bit:
            distance += 1
        elif negative_horizontal & last_bit:
            distance -= 1
        positive_horizontal = ((positive_horizontal << 1) | 1) & active_mask
        negative_horizontal = (negative_horizontal << 1) & active_mask
        positive = (negative_horizontal | ~(vertical | positive_horizontal)) & active_mask
        negative = positive_horizontal & vertical
    return distance


def longest_common_subsequence_length(source: list[str], target: list[str]) -> int:
    """Return exact token LCS length with a bit-parallel dynamic program."""
    if len(source) > len(target):
        source, target = target, source
    masks: dict[str, int] = {}
    for index, token in enumerate(target):
        masks[token] = masks.get(token, 0) | (1 << index)
    row = 0
    for token in source:
        matches = masks.get(token, 0)
        union = row | matches
        row = union & ~(union - ((row << 1) | 1))
    return row.bit_count()


def repeated_fourgram_fraction(tokens: list[str]) -> float:
    """Return the fraction of four-grams beyond their first occurrence."""
    if len(tokens) < 4:
        return 0.0
    grams = [tuple(tokens[index : index + 4]) for index in range(len(tokens) - 3)]
    counts = Counter(grams)
    return sum(count - 1 for count in counts.values() if count > 1) / len(grams)


def script_counts(text: str) -> Counter[str]:
    """Count broad scripts used by letters in one text."""
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


def calculate_metrics(source_text: str, rewrite_text: str) -> StructureMetrics:
    """Calculate all structure-first selector metrics for one text pair."""
    source_tokens = metric_tokens(source_text)
    rewrite_tokens = metric_tokens(rewrite_text)
    source_sentences = split_sentences(source_text)
    rewrite_sentences = split_sentences(rewrite_text)
    source_lengths = [len(metric_tokens(sentence)) for sentence in source_sentences]
    rewrite_lengths = [len(metric_tokens(sentence)) for sentence in rewrite_sentences]
    delta = abs(len(rewrite_sentences) - len(source_sentences))
    maximum_characters = max(len(source_text.strip()), len(rewrite_text.strip()))
    edit_distance = (
        levenshtein_distance(source_text.strip(), rewrite_text.strip()) / maximum_characters
        if maximum_characters
        else 0.0
    )
    lcs = longest_common_subsequence_length(source_tokens, rewrite_tokens)
    rouge_l = 2 * lcs / (len(source_tokens) + len(rewrite_tokens)) if source_tokens or rewrite_tokens else 0.0
    source_counts = Counter(source_tokens)
    rewrite_counts = Counter(rewrite_tokens)
    overlap = sum(min(count, rewrite_counts[token]) for token, count in source_counts.items())
    recall = overlap / len(source_tokens) if source_tokens else 0.0
    source_scripts = script_counts(source_text)
    rewrite_scripts = script_counts(rewrite_text)
    introduced = tuple(
        sorted(
            script
            for script, count in rewrite_scripts.items()
            if count >= 2 and source_scripts.get(script, 0) == 0
        )
    )
    source_complete = source_text.rstrip().endswith(tuple(".!?。！？\"'”’)]}"))
    rewrite_complete = rewrite_text.rstrip().endswith(tuple(".!?。！？\"'”’)]}"))
    return StructureMetrics(
        source_sentence_count=len(source_sentences),
        rewrite_sentence_count=len(rewrite_sentences),
        sentence_delta_abs=delta,
        relative_sentence_delta=delta / max(len(source_sentences), 1),
        source_cv=coefficient_of_variation(source_lengths),
        rewrite_cv=coefficient_of_variation(rewrite_lengths),
        cv_change=abs(
            coefficient_of_variation(rewrite_lengths)
            - coefficient_of_variation(source_lengths)
        ),
        source_token_count=len(source_tokens),
        rewrite_token_count=len(rewrite_tokens),
        length_ratio=len(rewrite_tokens) / len(source_tokens) if source_tokens else 0.0,
        edit_distance=edit_distance,
        rouge_l=rouge_l,
        content_recall=recall,
        repeated_fourgram_fraction=repeated_fourgram_fraction(rewrite_tokens),
        meta_or_refusal=any(phrase in rewrite_text.casefold() for phrase in META_PHRASES),
        introduced_scripts=introduced,
        incomplete_ending=source_complete and not rewrite_complete,
    )


def positive_is_eligible(metrics: StructureMetrics, policy: Mapping[str, object]) -> bool:
    """Return whether a held-out Human target provides a material structure signal."""
    if not (
        float(policy["minimum_length_ratio"])
        <= metrics.length_ratio
        <= float(policy["maximum_length_ratio"])
    ) or metrics.edit_distance < float(policy["minimum_edit_distance"]):
        return False
    short = metrics.source_sentence_count <= int(policy["short_source_sentence_maximum"])
    required_delta = int(
        policy["short_minimum_sentence_delta"]
        if short
        else policy["general_minimum_sentence_delta"]
    )
    sentence_signal = (
        metrics.sentence_delta_abs >= required_delta
        or metrics.relative_sentence_delta >= float(policy["minimum_relative_sentence_delta"])
    )
    return sentence_signal or metrics.cv_change >= float(policy["minimum_cv_change"])


def severe_failure_type(
    metrics: StructureMetrics,
    policy: Mapping[str, object],
) -> str | None:
    """Return one severe output-failure category, if present."""
    if metrics.length_ratio <= float(policy["maximum_short_length_ratio"]):
        return "severe_short"
    if metrics.length_ratio >= float(policy["minimum_long_length_ratio"]):
        return "severe_long"
    if metrics.repeated_fourgram_fraction >= float(policy["minimum_repeated_fourgram_fraction"]):
        return "severe_repetition"
    if policy.get("reject_meta_or_refusal") is True and metrics.meta_or_refusal:
        return "severe_meta_or_refusal"
    if policy.get("reject_introduced_script") is True and metrics.introduced_scripts:
        return "severe_introduced_script"
    if policy.get("reject_incomplete_ending") is True and metrics.incomplete_ending:
        return "severe_incomplete_ending"
    return None


def under_edit_is_eligible(
    metrics: StructureMetrics,
    policy: Mapping[str, object],
) -> bool:
    """Return whether a fluent rewrite changes wording but barely changes structure."""
    maximum_delta = min(
        int(policy["maximum_sentence_delta"]),
        0 if metrics.source_sentence_count <= 3 else int(policy["maximum_sentence_delta"]),
    )
    return (
        float(policy["minimum_length_ratio"])
        <= metrics.length_ratio
        <= float(policy["maximum_length_ratio"])
        and metrics.sentence_delta_abs <= maximum_delta
        and metrics.relative_sentence_delta <= float(policy["maximum_relative_sentence_delta"])
        and metrics.cv_change <= float(policy["maximum_cv_change"])
        and metrics.edit_distance <= float(policy["maximum_edit_distance"])
        and metrics.rouge_l >= float(policy["minimum_rouge_l"])
        and metrics.content_recall >= float(policy["minimum_content_recall"])
        and metrics.edit_distance > 0.0
    )


def finite_policy_number(policy: Mapping[str, object], name: str) -> float:
    """Return one finite numeric policy value."""
    value = policy.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"invalid policy number: {name}")
    return float(value)


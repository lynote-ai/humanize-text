"""Test deterministic source-and-length reservation for later KTO construction."""

import json
from pathlib import Path
import tempfile
import unittest

from data_process.a_reserve_sft_for_kto import (
    assign_kto_validation,
    bucket_for,
    parse_policy,
    select_reserved_inputs,
)


def policy(require_unique_targets: bool = True) -> dict[str, object]:
    """Return a small valid policy with two non-empty strata."""
    return {
        "schema_version": 1,
        "selection": {
            "target_input_count": 4,
            "selection_seed": 10,
            "kto_validation_ratio": 0.5,
            "kto_validation_seed": 11,
            "require_unique_target_hashes": require_unique_targets,
        },
        "length_buckets": [
            {"name": "short", "min_words": 0, "max_words": 199},
            {"name": "long", "min_words": 200, "max_words": None},
        ],
        "quotas": {
            "crawl": {"short": 2, "long": 0},
            "private": {"short": 0, "long": 2},
        },
    }


def index_record(
    sample_id: str,
    source: str,
    word_count: int,
    target_hash: str,
) -> dict[str, object]:
    """Build the smallest valid upstream sample-index record."""
    return {
        "sample_id": sample_id,
        "source": source,
        "split": "train",
        "source_sha256": f"source-{sample_id}",
        "target_sha256": target_hash,
        "pair_sha256": f"pair-{sample_id}",
        "system_prompt_id": 0,
        "ai_word_count": word_count,
        "human_word_count": word_count,
    }


class ReserveSftForKtoTest(unittest.TestCase):
    """Cover policy boundaries, exact quotas, and leakage protection."""

    def test_bucket_boundaries_are_inclusive_and_exhaustive(self) -> None:
        buckets, _quotas, _selection = parse_policy(policy())

        self.assertEqual(bucket_for(0, buckets), "short")
        self.assertEqual(bucket_for(199, buckets), "short")
        self.assertEqual(bucket_for(200, buckets), "long")

    def test_selection_and_validation_meet_each_stratum_quota(self) -> None:
        config = policy()
        buckets, quotas, selection = parse_policy(config)
        records = [
            index_record("crawl-a", "crawl", 100, "target-a"),
            index_record("crawl-b", "crawl", 110, "target-b"),
            index_record("crawl-c", "crawl", 120, "target-c"),
            index_record("private-a", "private", 300, "target-d"),
            index_record("private-b", "private", 310, "target-e"),
            index_record("private-c", "private", 320, "target-f"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "sample_index.jsonl"
            index_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )

            selected, supply, split_counts = select_reserved_inputs(
                index_path, buckets, quotas, selection
            )
            validation = assign_kto_validation(selected, quotas, selection)

        self.assertEqual(len(selected), 4)
        self.assertEqual(len(validation), 2)
        self.assertEqual(supply[("crawl", "short")], 3)
        self.assertEqual(supply[("private", "long")], 3)
        self.assertEqual(split_counts["train"], 6)

    def test_repeated_target_is_rejected_before_reservation(self) -> None:
        config = policy()
        buckets, quotas, selection = parse_policy(config)
        records = [
            index_record("crawl-a", "crawl", 100, "shared-target"),
            index_record("crawl-b", "crawl", 110, "shared-target"),
            index_record("private-a", "private", 300, "target-a"),
            index_record("private-b", "private", 310, "target-b"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "sample_index.jsonl"
            index_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "repeated target hash"):
                select_reserved_inputs(index_path, buckets, quotas, selection)


if __name__ == "__main__":
    unittest.main()

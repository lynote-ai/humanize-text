"""Test focused validation helpers for the selected KTO dataset."""

import unittest

from data_process.e_validate_kto_dataset import (
    expected_type_counts,
    message_texts,
    validate_index_pair,
)


class KtoDatasetValidatorTest(unittest.TestCase):
    """Cover ratio and pair invariants without loading production data."""

    def test_expected_type_counts_are_exact(self) -> None:
        config = {
            "selection": {"source_copy_fraction": 0.2},
            "negative_type_targets": {
                "semantic_drift": 0.3,
                "over_rewrite": 0.25,
                "structure_damage": 0.15,
                "fluency_contamination": 0.1,
            },
        }

        counts = expected_type_counts(config, 500)

        self.assertEqual(counts["source_copy"], 100)
        self.assertEqual(counts["semantic_drift"], 150)
        self.assertEqual(sum(counts.values()), 500)

    def test_message_texts_rejects_wrong_role_order(self) -> None:
        record = {
            "messages": [
                {"role": "user", "content": "system"},
                {"role": "system", "content": "input"},
                {"role": "assistant", "content": "output"},
            ],
            "label": True,
        }

        with self.assertRaisesRegex(ValueError, "roles"):
            message_texts(record, "test")

    def test_index_pair_rejects_source_copy_with_chain_id(self) -> None:
        base = {
            "input_id": "input-1",
            "source": "crawl",
            "split": "train",
            "length_bucket": "lt_200",
            "source_sha256": "source",
            "target_sha256": "target",
            "pair_sha256": "pair",
            "selected_chain_id": 1,
        }
        positive = {
            **base,
            "label": True,
            "response_role": "held_out_human_positive",
            "response_sha256": "target",
            "selection_metrics": None,
        }
        negative = {
            **base,
            "label": False,
            "response_role": "source_copy",
            "response_sha256": "source",
            "selection_metrics": {},
        }

        with self.assertRaisesRegex(ValueError, "chain must be null"):
            validate_index_pair(positive, negative, "train", 1)


if __name__ == "__main__":
    unittest.main()

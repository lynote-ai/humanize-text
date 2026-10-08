"""Test rule-based hard-negative analysis and deterministic quota helpers."""

import unittest

from data_process.d_select_kto_negatives import (
    CandidateOption,
    InputAnalysis,
    candidate_metrics,
    choose_source_copy_inputs,
    classify_candidate,
    parse_selector_config,
    validate_candidate_record,
)


def selector_config() -> dict[str, object]:
    """Return the production-shaped selector settings used by focused tests."""
    return {
        "schema_version": 1,
        "selection": {
            "seed": 1,
            "source_copy_fraction": 0.2,
            "review_count_per_negative_type": 1,
            "require_one_negative_per_input": True,
        },
        "candidate_gates": {
            "minimum_length_ratio": 0.55,
            "maximum_length_ratio": 1.75,
            "minimum_source_token_recall": 0.5,
            "maximum_repeated_fourgram_fraction": 0.25,
            "reject_meta_or_refusal": True,
        },
        "negative_type_targets": {
            "semantic_drift": 0.3,
            "over_rewrite": 0.25,
            "structure_damage": 0.15,
            "fluency_contamination": 0.1,
        },
        "type_rules": {
            "semantic_max_source_token_recall": 0.82,
            "over_rewrite_minimum_length_ratio": 1.2,
            "over_rewrite_minimum_added_words": 60,
            "over_rewrite_minimum_repeated_fourgram_fraction": 0.08,
            "structure_minimum_paragraph_delta": 1,
        },
    }


class SelectKtoNegativesTest(unittest.TestCase):
    """Cover fidelity signals, type evidence, and stratum-level source copies."""

    def test_metrics_detect_anchor_script_and_paragraph_damage(self) -> None:
        source = "There were 20 items.\n\nThe second paragraph is here."
        target = "There were 20 items.\n\nHere is the second paragraph."
        candidate = "There were 30 items 随心. The second paragraph is here."

        metrics = candidate_metrics(source, target, candidate)

        self.assertTrue(metrics["number_mismatch"])
        self.assertEqual(metrics["introduced_scripts"], ["cjk"])
        self.assertEqual(metrics["paragraph_delta"], -1)

    def test_clear_but_noncatastrophic_candidate_gets_supported_types(self) -> None:
        policy, _targets = parse_selector_config(selector_config())
        metrics = {
            "length_ratio": 1.1,
            "source_token_recall": 0.75,
            "repeated_fourgram_fraction": 0.0,
            "exact_source": False,
            "exact_target": False,
            "meta_or_refusal": False,
            "number_mismatch": True,
            "url_mismatch": False,
            "added_word_count": 10,
            "paragraph_delta": 0,
            "introduced_format_artifact": False,
            "introduced_scripts": [],
            "incomplete_ending": False,
        }

        eligible, failures, severity = classify_candidate(metrics, policy)

        self.assertEqual(failures, ())
        self.assertIn("semantic_drift", eligible)
        self.assertLess(severity, 2.0)

    def test_source_copy_quota_is_exact_per_split_and_balanced_by_stratum(self) -> None:
        usable_option = CandidateOption(
            chain_id=0,
            metrics={},
            eligible_types=("semantic_drift",),
            severity=1.0,
        )
        analyses = [
            InputAnalysis(
                pair_sha256=f"pair-{source}-{index}",
                input_id=f"input-{source}-{index}",
                split="train",
                source=source,
                length_bucket="short",
                options=(usable_option,),
            )
            for source in ("crawl", "private")
            for index in range(10)
        ]

        selected = choose_source_copy_inputs(analyses, 0.2, seed=3)

        self.assertEqual(len(selected), 4)
        self.assertEqual(sum("crawl" in pair for pair in selected), 2)
        self.assertEqual(sum("private" in pair for pair in selected), 2)

    def test_source_copy_allocation_prioritizes_inputs_without_candidates(self) -> None:
        usable_option = CandidateOption(
            chain_id=0,
            metrics={},
            eligible_types=("semantic_drift",),
            severity=1.0,
        )
        analyses = [
            InputAnalysis(
                pair_sha256=f"pair-{index}",
                input_id=f"input-{index}",
                split="train",
                source="crawl",
                length_bucket="short",
                options=() if index == 0 else (usable_option,),
            )
            for index in range(10)
        ]

        selected = choose_source_copy_inputs(analyses, 0.2, seed=3)

        self.assertEqual(len(selected), 2)
        self.assertIn("pair-0", selected)

    def test_candidate_validator_accepts_six_temperature_candidates(self) -> None:
        seed = {
            "input_id": "input-1",
            "source": "crawl",
            "split": "train",
            "length_bucket": "300_499",
            "source_sha256": "source-hash",
            "target_sha256": "target-hash",
            "pair_sha256": "pair-hash",
        }
        candidate = {
            **seed,
            "rounds": 2,
            "num_results": 6,
            "results": [
                {
                    "chain_id": chain_id,
                    "temperature": temperature,
                    "rewrite": f"candidate-{chain_id}",
                }
                for chain_id, temperature in enumerate(
                    (0.3, 0.5, 0.7, 0.9, 1.0, 1.0)
                )
            ],
        }

        results = validate_candidate_record(candidate, seed, "train", 1)

        self.assertEqual(len(results), 6)


if __name__ == "__main__":
    unittest.main()

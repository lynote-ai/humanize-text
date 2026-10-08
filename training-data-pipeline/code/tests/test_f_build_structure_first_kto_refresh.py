"""Test refreshed KTO assignment and deterministic severe transformations."""

import unittest

from data_process.f_build_structure_first_kto_refresh import (
    InputAnalysis,
    UnderEditOption,
    select_negative_types,
    severe_expansion,
    severe_shortening,
)
from data_process.structure_first_metrics import calculate_metrics


class StructureFirstKtoRefreshTest(unittest.TestCase):
    """Cover exact mixture counts and severe length failures."""

    def test_severe_transformations_cross_length_thresholds(self) -> None:
        source = "One sentence has enough words to test truncation. " * 20
        self.assertLessEqual(
            calculate_metrics(source, severe_shortening(source)).length_ratio, 0.55
        )
        self.assertGreaterEqual(
            calculate_metrics(source, severe_expansion(source)).length_ratio, 1.70
        )

    def test_exact_sixty_twenty_twenty_assignment(self) -> None:
        metrics = calculate_metrics(
            "The original sentence stays here. A second sentence follows.",
            "The initial sentence stays here. A second sentence comes next.",
        )
        analyses = [
            InputAnalysis(
                pair_sha256=f"train-{index}",
                input_id=f"train-{index}",
                split="train",
                source="crawl",
                length_bucket="lt_200",
                option=UnderEditOption(0, "Light edit.", metrics),
            )
            for index in range(10)
        ]
        selections, diagnostics = select_negative_types(
            analyses,
            {
                "seed": 260917,
                "generated_under_edit_fraction": 0.60,
                "source_copy_fraction": 0.20,
                "severe_failure_fraction": 0.20,
            },
        )

        self.assertEqual(len(selections), 10)
        self.assertEqual(diagnostics["train"]["selected_generated_under_edit"], 6)
        self.assertEqual(diagnostics["train"]["selected_source_copy"], 2)
        self.assertEqual(diagnostics["train"]["selected_severe_short"], 1)
        self.assertEqual(
            diagnostics["train"]["selected_severe_long_repetition"], 1
        )


if __name__ == "__main__":
    unittest.main()

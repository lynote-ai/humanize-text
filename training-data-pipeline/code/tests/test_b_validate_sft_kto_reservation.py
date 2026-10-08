"""Test focused validation helpers for the SFT/KTO reservation bundle."""

import unittest

from data_process.a_reserve_sft_for_kto import parse_policy


class ReservationValidatorPolicyTest(unittest.TestCase):
    """Ensure fractional validation quotas cannot silently drift."""

    def test_non_integer_validation_quota_is_rejected(self) -> None:
        config = {
            "schema_version": 1,
            "selection": {
                "target_input_count": 1,
                "selection_seed": 1,
                "kto_validation_ratio": 0.1,
                "kto_validation_seed": 2,
                "require_unique_target_hashes": True,
            },
            "length_buckets": [
                {"name": "all", "min_words": 0, "max_words": None}
            ],
            "quotas": {
                "crawl": {"all": 1},
                "private": {"all": 0},
            },
        }

        with self.assertRaisesRegex(ValueError, "does not produce an integer"):
            parse_policy(config)


if __name__ == "__main__":
    unittest.main()

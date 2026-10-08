"""Test enforcement of the public demo record limit."""

import json
from pathlib import Path
import tempfile
import unittest

from harness.validate_demo_data import validate_jsonl, validate_prompt_examples


class ValidateDemoDataTest(unittest.TestCase):
    """Cover exact and over-limit demo datasets."""

    def write_records(self, path: Path, count: int) -> None:
        """Write a small JSONL fixture."""
        with path.open("w", encoding="utf-8") as output_file:
            for index in range(count):
                output_file.write(json.dumps({"id": index}) + "\n")

    def test_exact_limit_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "demo.jsonl"
            self.write_records(path, 50)

            self.assertEqual(validate_jsonl(path, 50), 50)

    def test_more_than_limit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "demo.jsonl"
            self.write_records(path, 51)

            with self.assertRaisesRegex(ValueError, "exceeds"):
                validate_jsonl(path, 50)

    def test_non_public_source_label_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "demo.jsonl"
            path.write_text(
                json.dumps({"input_id": "internal:item", "source": "internal"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "non-public source label"):
                validate_jsonl(path, 50)

    def test_five_distinct_prompt_examples_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "prompts.json"
            path.write_text(
                json.dumps([f"prompt-{index}" for index in range(5)]),
                encoding="utf-8",
            )

            self.assertEqual(validate_prompt_examples(path), 5)

    def test_duplicate_prompt_example_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "prompts.json"
            path.write_text(json.dumps(["same"] * 5), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "distinct"):
                validate_prompt_examples(path)


if __name__ == "__main__":
    unittest.main()

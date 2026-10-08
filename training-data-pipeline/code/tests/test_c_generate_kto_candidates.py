"""Test the KTO train/validation remote candidate-generation adapter."""

import json
from pathlib import Path
import tempfile
import unittest

from data_process.c_generate_kto_candidates import (
    clean_rewrite,
    count_completed_prefix,
    parse_temperature_schedule,
    rewrite_chain,
    validate_seed_record,
)


def seed_record(split: str = "train") -> dict[str, object]:
    """Return one valid generation seed."""
    return {
        "input_id": "crawl:sample-1",
        "source": "crawl",
        "split": split,
        "length_bucket": "300_499",
        "ai_word_count": 320,
        "human_word_count": 330,
        "messages": [
            {"role": "system", "content": "Rewrite faithfully."},
            {"role": "user", "content": "Source paragraph."},
        ],
        "desirable_response": "Human response.",
        "source_sha256": "source-hash",
        "target_sha256": "target-hash",
        "pair_sha256": "pair-hash",
        "system_prompt_id": 1,
    }


class FakeCompletions:
    """Return deterministic texts while recording chained request messages."""

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []
        self.temperatures: list[float] = []

    def create(self, **kwargs: object) -> object:
        messages = kwargs["messages"]
        assert isinstance(messages, list)
        self.calls.append(messages)
        self.temperatures.append(float(kwargs["temperature"]))
        content = "first\n\nparagraph" if len(self.calls) == 1 else "second"
        message = type("Message", (), {"content": content})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


class FakeClient:
    """Expose the nested chat.completions interface used by the generator."""

    def __init__(self) -> None:
        completions = FakeCompletions()
        self.completions = completions
        self.chat = type("Chat", (), {"completions": completions})()


class GenerateKtoCandidatesTest(unittest.TestCase):
    """Cover schema adaptation, paragraph preservation, chaining, and resume."""

    def test_seed_uses_its_own_system_and_user_messages(self) -> None:
        system_prompt, input_text = validate_seed_record(seed_record(), "train", 1)

        self.assertEqual(system_prompt, "Rewrite faithfully.")
        self.assertEqual(input_text, "Source paragraph.")

    def test_clean_rewrite_preserves_paragraph_breaks(self) -> None:
        self.assertEqual(clean_rewrite("  First.\n\nSecond.  "), "First.\n\nSecond.")

    def test_rewrite_chain_feeds_previous_output_to_next_round(self) -> None:
        client = FakeClient()

        result = rewrite_chain(
            client,
            "followups",
            "Rewrite faithfully.",
            "Source paragraph.",
            rounds=2,
            temperature=1.0,
            max_tokens=4096,
            max_retries=0,
        )

        self.assertEqual(result, "second")
        self.assertEqual(
            client.completions.calls[1][1]["content"], "first\n\nparagraph"
        )
        self.assertEqual(client.completions.temperatures, [1.0, 1.0])

    def test_temperature_schedule_keeps_duplicate_entries_as_independent_chains(self) -> None:
        self.assertEqual(
            parse_temperature_schedule("0.3,0.5,0.7,0.9,1.0,1.0", 6),
            (0.3, 0.5, 0.7, 0.9, 1.0, 1.0),
        )
        with self.assertRaisesRegex(ValueError, "must equal num-results"):
            parse_temperature_schedule("0.3,0.5", 6)

    def test_resume_requires_exact_seed_prefix_and_generation_shape(self) -> None:
        seed = seed_record()
        candidate = {
            "input_id": seed["input_id"],
            "source": seed["source"],
            "split": "train",
            "length_bucket": seed["length_bucket"],
            "source_sha256": seed["source_sha256"],
            "target_sha256": seed["target_sha256"],
            "pair_sha256": seed["pair_sha256"],
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
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "seed.jsonl"
            output_path = Path(temp_dir) / "candidates.jsonl"
            input_path.write_text(json.dumps(seed) + "\n", encoding="utf-8")
            output_path.write_text(json.dumps(candidate) + "\n", encoding="utf-8")

            completed = count_completed_prefix(
                input_path,
                output_path,
                "train",
                num_results=6,
                rounds=2,
                temperatures=(0.3, 0.5, 0.7, 0.9, 1.0, 1.0),
            )

        self.assertEqual(completed, 1)


if __name__ == "__main__":
    unittest.main()

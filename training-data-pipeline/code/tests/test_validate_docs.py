"""Test bilingual documentation and Mermaid contract validation."""

from pathlib import Path
import tempfile
import unittest

from harness.validate_docs import (
    extract_mermaid_blocks,
    validate_english_text,
    validate_mermaid_blocks,
    validate_relative_links,
)


class ValidateDocsTest(unittest.TestCase):
    """Cover Mermaid declarations, language separation, and local links."""

    def test_flowchart_block_is_accepted(self) -> None:
        text = """# Diagram

```mermaid
flowchart LR
    source --> target
```
"""

        self.assertEqual(extract_mermaid_blocks(text), ["flowchart LR\n    source --> target"])
        self.assertEqual(validate_mermaid_blocks(Path("README.md"), text, 1), 1)

    def test_unknown_mermaid_declaration_is_rejected(self) -> None:
        text = """```mermaid
unknownDiagram
    source --> target
```"""

        with self.assertRaisesRegex(ValueError, "unsupported Mermaid declaration"):
            validate_mermaid_blocks(Path("README.md"), text, 1)

    def test_chinese_text_in_english_document_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Chinese text found"):
            validate_english_text(Path("README.md"), "English text and 中文。")

    def test_missing_relative_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "README.md"

            with self.assertRaisesRegex(ValueError, "broken relative link"):
                validate_relative_links(path, "See [missing](docs/missing.md).")


if __name__ == "__main__":
    unittest.main()

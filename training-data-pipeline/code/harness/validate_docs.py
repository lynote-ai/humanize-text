"""Validate bilingual documentation links and Mermaid diagram contracts."""

import argparse
from datetime import datetime
from pathlib import Path
import re


DOC_MIN_MERMAID_BLOCKS = {
    "README.md": 1,
    "README.zh-CN.md": 1,
    "data/README.md": 0,
    "data/README.zh-CN.md": 0,
    "docs/ARCHITECTURE.md": 2,
    "docs/ARCHITECTURE.zh-CN.md": 2,
    "docs/DATA_CONSTRUCTION.md": 3,
    "docs/DATA_CONSTRUCTION.zh-CN.md": 3,
    "docs/PROMPTS.md": 1,
    "docs/PROMPTS.zh-CN.md": 1,
}
ENGLISH_DOCS = {
    "README.md",
    "data/README.md",
    "docs/ARCHITECTURE.md",
    "docs/DATA_CONSTRUCTION.md",
    "docs/PROMPTS.md",
}
MERMAID_STARTS = (
    "flowchart ",
    "graph ",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "journey",
    "gantt",
    "pie",
    "mindmap",
    "timeline",
    "gitGraph",
)
MERMAID_BLOCK_PATTERN = re.compile(r"```mermaid[ \t]*\n(.*?)\n```", re.DOTALL)
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HAN_PATTERN = re.compile(r"[\u3400-\u9fff]")


def parse_args() -> argparse.Namespace:
    """Parse the project directory supplied by the Make target."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, type=Path)
    return parser.parse_args()


def extract_mermaid_blocks(text: str) -> list[str]:
    """Return all fenced Mermaid blocks in one Markdown document."""
    return [match.strip() for match in MERMAID_BLOCK_PATTERN.findall(text)]


def validate_mermaid_blocks(path: Path, text: str, minimum: int) -> int:
    """Validate the expected count and declaration of Mermaid blocks."""
    blocks = extract_mermaid_blocks(text)
    if len(blocks) < minimum:
        raise ValueError(
            f"{path} has {len(blocks)} Mermaid blocks; expected at least {minimum}"
        )
    for index, block in enumerate(blocks, start=1):
        first_line = next((line.strip() for line in block.splitlines() if line.strip()), "")
        if not first_line.startswith(MERMAID_STARTS):
            raise ValueError(
                f"unsupported Mermaid declaration in {path} block {index}: {first_line}"
            )
    return len(blocks)


def validate_english_text(path: Path, text: str) -> None:
    """Reject Chinese text accidentally mixed into an English document."""
    match = HAN_PATTERN.search(text)
    if match:
        line_number = text.count("\n", 0, match.start()) + 1
        raise ValueError(f"Chinese text found in English document at {path}:{line_number}")


def validate_relative_links(path: Path, text: str) -> None:
    """Require every relative Markdown link to resolve to a local file."""
    for raw_target in MARKDOWN_LINK_PATTERN.findall(text):
        target = raw_target.strip().split("#", maxsplit=1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            raise ValueError(f"broken relative link in {path}: {raw_target}")


def validate_documentation(project_dir: Path) -> dict[str, int]:
    """Validate the bilingual documentation set and return diagram counts."""
    counts: dict[str, int] = {}
    for relative_path, minimum in DOC_MIN_MERMAID_BLOCKS.items():
        path = project_dir / relative_path
        text = path.read_text(encoding="utf-8")
        if relative_path in ENGLISH_DOCS:
            validate_english_text(path, text)
        validate_relative_links(path, text)
        counts[relative_path] = validate_mermaid_blocks(path, text, minimum)
    return counts


def main() -> int:
    """Validate public documentation and return a reliable process exit code."""
    args = parse_args()
    project_dir = args.project_dir.resolve()
    print("target: docs-validate")
    print(f"project_dir: {project_dir}")
    print(f"started_at: {datetime.now().astimezone().isoformat()}")
    try:
        counts = validate_documentation(project_dir)
    except (OSError, ValueError) as error:
        print("status: failed")
        print(f"error: {error}")
        return 2
    print(f"document_count: {len(counts)}")
    print(f"mermaid_block_count: {sum(counts.values())}")
    print("status: success")
    print(f"finished_at: {datetime.now().astimezone().isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

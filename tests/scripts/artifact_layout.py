#!/usr/bin/env python3

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "tests" / "data"
INPUTS_ROOT = DATA_ROOT / "inputs"
RESULTS_ROOT = DATA_ROOT / "results"


def slugify(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def input_file(*parts: str) -> Path:
    return INPUTS_ROOT.joinpath(*parts)


def latest_result_artifact(filename: str) -> Path:
    matches = sorted(
        RESULTS_ROOT.rglob(filename),
        key=lambda path: (path.stat().st_mtime, str(path)),
    )
    if not matches:
        raise FileNotFoundError(f"Could not find result artifact named {filename} under {RESULTS_ROOT}")
    return matches[-1]


def timestamped_result_dir(
    *,
    content: str,
    artifact_type: str,
    purpose: str,
    timestamp: datetime | None = None,
) -> Path:
    if timestamp is None:
        timestamp = datetime.now()
    stamp = timestamp.strftime("%Y-%m-%d_%H%M%S")
    year_dir = RESULTS_ROOT / timestamp.strftime("%Y")
    year_dir.mkdir(parents=True, exist_ok=True)
    result_dir = year_dir / (
        f"{stamp}__{slugify(content)}__{slugify(artifact_type)}__{slugify(purpose)}"
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def write_readme(
    directory: Path,
    *,
    title: str,
    content: str,
    artifact_type: str,
    purpose: str,
    notes: list[str] | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title}",
        "",
        f"- Content: {content}",
        f"- Type: {artifact_type}",
        f"- Purpose: {purpose}",
    ]
    if notes:
        lines.extend(["", "## Notes", ""])
        lines.extend([f"- {note}" for note in notes])
    readme = directory / "README.md"
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return readme

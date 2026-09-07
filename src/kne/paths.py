"""Repo-root discovery and default file locations for the Kenya Name Engine."""

from __future__ import annotations

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` (or this file) to the directory holding pyproject.toml."""
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    # Fall back to two levels up from src/kne/paths.py
    return Path(__file__).resolve().parents[2]


ROOT = repo_root()

DATA_DIR = ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
DEFAULT_CORPUS_FILE = CORPUS_DIR / "reference_dataset_classified.xlsx"
DEFAULT_CORPUS_MANIFEST = CORPUS_DIR / "MANIFEST.json"
DEFAULT_DB = DATA_DIR / "corpus.db"

OUTPUT_DIR = ROOT / "output"
CORPUS_REPORT_DIR = OUTPUT_DIR / "corpus"

ARCHIVE_DIR = ROOT / "archive"

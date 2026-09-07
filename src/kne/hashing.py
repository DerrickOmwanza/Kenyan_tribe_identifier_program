"""Deterministic SHA-256 helpers for provenance and reproducibility.

The streaming file hasher mirrors ``sha256_file`` in the legacy
``src/profile_data.py`` so hashes reported by the new engine match earlier runs.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

_CHUNK = 1024 * 1024


def sha256_file(path: str | Path) -> str:
    """Return the lowercase hex SHA-256 of a file, read in 1 MiB chunks."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase hex SHA-256 of a bytes object."""
    return hashlib.sha256(data).hexdigest()


def sha256_strings(parts: Iterable[str]) -> str:
    """Return a stable hex SHA-256 over an ordered sequence of strings.

    Each part is newline-terminated before hashing so that ``["a", "bc"]`` and
    ``["ab", "c"]`` produce different digests.
    """
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

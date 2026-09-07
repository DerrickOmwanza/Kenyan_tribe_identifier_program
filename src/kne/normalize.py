"""Normalization helpers that keep source values separate from analysis values.

Copied verbatim from the legacy ``src/normalize.py`` so the new engine shares the
exact deterministic comparison form used by the existing reference data.
"""

from __future__ import annotations

import re
import unicodedata


def normalize_name(value: str) -> str:
    """Return a deterministic comparison form without changing the source value."""
    value = unicodedata.normalize("NFKC", value or "")
    value = value.strip().upper()
    value = re.sub(r"[\s\-]+", " ", value)
    return value


def name_tokens(value: str) -> list[str]:
    """Return normalized whitespace-delimited name tokens from one source field."""
    normalized = normalize_name(value)
    return [token for token in normalized.split(" ") if token]

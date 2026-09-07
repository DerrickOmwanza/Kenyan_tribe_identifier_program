"""Explicit unit tests for kne.normalize (the legacy suite only covers it indirectly)."""

from __future__ import annotations

import pytest

from kne.normalize import name_tokens, normalize_name


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("otieno", "OTIENO"),
        ("  Wanjiku  ", "WANJIKU"),
        ("john   paul", "JOHN PAUL"),
        ("Anne-Marie", "ANNE MARIE"),
        ("a - b  -  c", "A B C"),
        ("", ""),
        ("   ", ""),
        ("ﬁona", "FIONA"),          # NFKC decomposes the fi ligature
        ("ＭＵＴＵＡ", "MUTUA"),        # fullwidth latin -> ascii via NFKC
    ],
)
def test_normalize_name(raw: str, expected: str) -> None:
    assert normalize_name(raw) == expected


def test_normalize_name_accepts_none() -> None:
    assert normalize_name(None) == ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("JOHN MUTISYA", ["JOHN", "MUTISYA"]),
        ("  mary   ", ["MARY"]),
        ("anne-marie wangui", ["ANNE", "MARIE", "WANGUI"]),
        ("", []),
        (None, []),
        ("   ", []),
    ],
)
def test_name_tokens(raw, expected) -> None:
    assert name_tokens(raw) == expected


def test_normalize_is_idempotent() -> None:
    once = normalize_name("  José-Luis   di María ")
    assert normalize_name(once) == once

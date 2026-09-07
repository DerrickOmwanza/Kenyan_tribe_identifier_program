"""Unit tests for kne.hashing."""

from __future__ import annotations

import hashlib

from kne.hashing import sha256_bytes, sha256_file, sha256_strings

_EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_sha256_bytes_known_vector() -> None:
    assert sha256_bytes(b"") == _EMPTY_SHA
    assert sha256_bytes(b"abc") == hashlib.sha256(b"abc").hexdigest()


def test_sha256_file_matches_bytes(tmp_path) -> None:
    payload = b"MACHARIA\nODHIAMBO\n" * 100_000  # exceeds the 1 MiB chunk size
    path = tmp_path / "big.txt"
    path.write_bytes(payload)
    assert sha256_file(path) == sha256_bytes(payload)


def test_sha256_strings_is_order_and_boundary_sensitive() -> None:
    assert sha256_strings(["a", "bc"]) != sha256_strings(["ab", "c"])
    assert sha256_strings(["x", "y"]) != sha256_strings(["y", "x"])
    assert sha256_strings(["a", "b"]) == sha256_strings(["a", "b"])

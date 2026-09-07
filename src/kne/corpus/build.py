"""Recompute the derived tables and corpus version from the raw ``records`` table.

All observation aggregates are derived, so a rebuild is always safe to run and is
the single source of truth after any ingest.
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter
from datetime import datetime, timezone

from ..hashing import sha256_strings
from ..normalize import name_tokens
from .store import SCHEMA_VERSION, set_meta

POSITIONS = ("fname", "mname", "sname")

# combo_reference keeps only keys at or above this support; the classifier's
# own combo_min_support may be higher but never lower.
COMBO_REFERENCE_MIN_SUPPORT = 3


def _entropy(counts: list[int], total: int) -> float:
    """Shannon entropy in bits over a tribe distribution."""
    h = 0.0
    for c in counts:
        if c:
            p = c / total
            h -= p * math.log2(p)
    return h


def _reference_row(dist: dict[str, int]) -> tuple[int, int, str, float, float, str]:
    """Collapse a {tribe: count} distribution into a reference-table row tuple."""
    total = sum(dist.values())
    ordered = sorted(dist.items(), key=lambda kv: (-kv[1], kv[0]))
    top_tribe, top_count = ordered[0]
    probs = {tribe: round(count / total, 6) for tribe, count in ordered}
    return (
        total,
        len(dist),
        top_tribe,
        round(top_count / total, 6),
        round(_entropy(list(dist.values()), total), 6),
        json.dumps(probs, ensure_ascii=False, sort_keys=True),
    )


def rebuild_observations(conn: sqlite3.Connection) -> dict[str, int]:
    """Recompute name_observations and combo_observations from every record."""
    name_counts: Counter[tuple[str, str, str]] = Counter()
    combo_counts: Counter[tuple[str, str, str]] = Counter()

    for row in conn.execute(
        "SELECT fname_raw, mname_raw, sname_raw, tribe_raw FROM records"
    ):
        tribe = row["tribe_raw"]
        tokens = {
            "fname": name_tokens(row["fname_raw"] or ""),
            "mname": name_tokens(row["mname_raw"] or ""),
            "sname": name_tokens(row["sname_raw"] or ""),
        }
        for position in POSITIONS:
            for token in tokens[position]:
                name_counts[(token, position, tribe)] += 1
        for ft in tokens["fname"]:
            for st in tokens["sname"]:
                combo_counts[("fname_sname", f"{ft}|{st}", tribe)] += 1
        for mt in tokens["mname"]:
            for st in tokens["sname"]:
                combo_counts[("mname_sname", f"{mt}|{st}", tribe)] += 1
        for ft in tokens["fname"]:
            for mt in tokens["mname"]:
                for st in tokens["sname"]:
                    combo_counts[("fname_mname_sname", f"{ft}|{mt}|{st}", tribe)] += 1

    conn.execute("DELETE FROM name_observations")
    conn.execute("DELETE FROM combo_observations")
    conn.executemany(
        "INSERT INTO name_observations(token, position, tribe, count) VALUES (?, ?, ?, ?)",
        [(*key, n) for key, n in name_counts.items()],
    )
    conn.executemany(
        "INSERT INTO combo_observations(combo_type, token_key, tribe, count) VALUES (?, ?, ?, ?)",
        [(*key, n) for key, n in combo_counts.items()],
    )
    return {"name_observations": len(name_counts), "combo_observations": len(combo_counts)}


def rebuild_token_reference(conn: sqlite3.Connection) -> int:
    """Rebuild token_reference from name_observations. Returns the row count."""
    conn.execute("DELETE FROM token_reference")
    grouped: dict[tuple[str, str], dict[str, int]] = {}
    for row in conn.execute("SELECT token, position, tribe, count FROM name_observations"):
        grouped.setdefault((row["token"], row["position"]), {})[row["tribe"]] = row["count"]

    payload = [
        (token, position, *_reference_row(dist))
        for (token, position), dist in grouped.items()
    ]
    conn.executemany(
        "INSERT INTO token_reference"
        "(token, position, support, distinct_tribes, top_tribe, top_share, entropy, dist_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        payload,
    )
    return len(payload)


def rebuild_combo_reference(
    conn: sqlite3.Connection, min_support: int = COMBO_REFERENCE_MIN_SUPPORT
) -> int:
    """Rebuild combo_reference from combo_observations, keeping keys with support >= min_support."""
    conn.execute("DELETE FROM combo_reference")
    grouped: dict[tuple[str, str], dict[str, int]] = {}
    for row in conn.execute("SELECT combo_type, token_key, tribe, count FROM combo_observations"):
        grouped.setdefault((row["combo_type"], row["token_key"]), {})[row["tribe"]] = row["count"]

    payload = [
        (combo_type, token_key, *_reference_row(dist))
        for (combo_type, token_key), dist in grouped.items()
        if sum(dist.values()) >= min_support
    ]
    conn.executemany(
        "INSERT INTO combo_reference"
        "(combo_type, token_key, support, distinct_tribes, top_tribe, top_share, entropy, dist_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        payload,
    )
    return len(payload)


def compute_corpus_version(conn: sqlite3.Connection) -> str:
    parts = [f"schema:{SCHEMA_VERSION}"]
    for row in conn.execute("SELECT source_id, sha256 FROM sources ORDER BY sha256, source_id"):
        parts.append(f"{row['source_id']}:{row['sha256']}")
    return sha256_strings(parts)


def tribe_list(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        r["tribe_raw"]: r["n"]
        for r in conn.execute(
            "SELECT tribe_raw, COUNT(*) AS n FROM records "
            "GROUP BY tribe_raw ORDER BY n DESC, tribe_raw"
        )
    }


def build(conn: sqlite3.Connection) -> dict[str, object]:
    """Rebuild every derived table and refresh corpus_meta. Caller commits."""
    obs = rebuild_observations(conn)
    token_rows = rebuild_token_reference(conn)
    combo_rows = rebuild_combo_reference(conn)
    version = compute_corpus_version(conn)
    tribes = tribe_list(conn)
    set_meta(conn, "schema_version", SCHEMA_VERSION)
    set_meta(conn, "corpus_version", version)
    set_meta(conn, "built_at", datetime.now(timezone.utc).isoformat())
    set_meta(conn, "tribe_list_json", json.dumps(tribes, ensure_ascii=False, sort_keys=True))
    return {
        **obs,
        "token_reference_rows": token_rows,
        "combo_reference_rows": combo_rows,
        "corpus_version": version,
        "tribe_count": len(tribes),
    }

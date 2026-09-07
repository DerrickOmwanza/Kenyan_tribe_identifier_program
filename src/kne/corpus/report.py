"""Data-quality reports derived from the corpus store."""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..normalize import name_tokens
from .store import connect, get_meta

SUPPORT_BINS = ((1, 1), (2, 4), (5, 9), (10, 49), (50, None))
MIN_SUPPORT = 10          # surname support required to trust a consensus
SPARSE_SURNAME_LIMIT = 150  # tribes below this many "owned" surnames are flagged unlearnable


def _bin_label(lo: int, hi: int | None) -> str:
    return f"{lo}+" if hi is None else (str(lo) if lo == hi else f"{lo}-{hi}")


def _support_histogram(conn: sqlite3.Connection, position: str) -> dict[str, int]:
    supports = [
        r["support"]
        for r in conn.execute(
            "SELECT support FROM token_reference WHERE position = ?", (position,)
        )
    ]
    hist = {}
    for lo, hi in SUPPORT_BINS:
        hist[_bin_label(lo, hi)] = sum(1 for s in supports if s >= lo and (hi is None or s <= hi))
    return hist


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate(
    db_path: str | Path,
    out_dir: str | Path,
    *,
    min_support: int = MIN_SUPPORT,
    sparse_surname_limit: int = SPARSE_SURNAME_LIMIT,
) -> dict[str, object]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        return _generate(conn, out_dir, min_support, sparse_surname_limit)
    finally:
        conn.close()


def _generate(
    conn: sqlite3.Connection, out_dir: Path, min_support: int, sparse_surname_limit: int
) -> dict[str, object]:
    meta_source = conn.execute(
        "SELECT source_id, filename, sha256, row_count, hash_verified FROM sources ORDER BY source_id"
    ).fetchall()
    total_records = conn.execute("SELECT COUNT(*) AS n FROM records").fetchone()["n"]
    corpus_version = get_meta(conn, "corpus_version", "?")
    tribe_counts = json.loads(get_meta(conn, "tribe_list_json", "{}"))

    # --- surname_reference.csv ---
    surname_rows = [
        {
            "surname": r["token"],
            "support": r["support"],
            "top_tribe": r["top_tribe"],
            "top_share": r["top_share"],
            "distinct_tribes": r["distinct_tribes"],
            "entropy": r["entropy"],
        }
        for r in conn.execute(
            "SELECT token, support, top_tribe, top_share, distinct_tribes, entropy "
            "FROM token_reference WHERE position = 'sname' "
            "ORDER BY support DESC, token"
        )
    ]
    _write_csv(
        out_dir / "surname_reference.csv",
        ["surname", "support", "top_tribe", "top_share", "distinct_tribes", "entropy"],
        surname_rows,
    )
    surname_ref = {r["surname"]: r for r in surname_rows}

    # --- label_consensus_disagreement.csv ---
    disagreements = []
    for rec in conn.execute(
        "SELECT row_index, fname_raw, mname_raw, sname_raw, tribe_raw FROM records "
        "ORDER BY row_index"
    ):
        stoks = name_tokens(rec["sname_raw"] or "")
        if not stoks:
            continue
        ref = surname_ref.get(stoks[0])
        if not ref or ref["support"] < min_support:
            continue
        if rec["tribe_raw"] != ref["top_tribe"]:
            disagreements.append({
                "row_index": rec["row_index"],
                "fname_raw": rec["fname_raw"] or "",
                "mname_raw": rec["mname_raw"] or "",
                "sname_raw": rec["sname_raw"] or "",
                "tribe_raw": rec["tribe_raw"],
                "surname_top_tribe": ref["top_tribe"],
                "surname_top_share": ref["top_share"],
                "surname_support": ref["support"],
            })
    disagreements.sort(key=lambda d: (-d["surname_support"], d["row_index"]))
    _write_csv(
        out_dir / "label_consensus_disagreement.csv",
        ["row_index", "fname_raw", "mname_raw", "sname_raw", "tribe_raw",
         "surname_top_tribe", "surname_top_share", "surname_support"],
        disagreements,
    )

    # --- per-tribe surname ownership ---
    owned = {
        r["top_tribe"]: r["n"]
        for r in conn.execute(
            "SELECT top_tribe, COUNT(*) AS n FROM token_reference "
            "WHERE position = 'sname' GROUP BY top_tribe"
        )
    }
    sparse = sorted(t for t, c in tribe_counts.items() if owned.get(t, 0) < sparse_surname_limit)

    # --- distinct tokens / support headline ---
    distinct = {
        p: conn.execute(
            "SELECT COUNT(*) AS n FROM token_reference WHERE position = ?", (p,)
        ).fetchone()["n"]
        for p in ("fname", "mname", "sname")
    }
    sname_hist = _support_histogram(conn, "sname")
    sname_total = distinct["sname"] or 1
    sname_ge_min = conn.execute(
        "SELECT COUNT(*) AS n FROM token_reference WHERE position = 'sname' AND support >= ?",
        (min_support,),
    ).fetchone()["n"]

    # --- corpus_summary.md ---
    lines = [
        "# Corpus Summary",
        "",
        "Descriptive statistics over the labelled name corpus. Tribe labels are stored",
        "verbatim as supplied and are an LLM-derived reference, not ground truth. A",
        "name-based association is not proof of an individual's ethnicity, community",
        "identity, ancestry, or self-identification.",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Corpus version: `{corpus_version}`",
        f"- Total labelled records: **{total_records:,}**",
        "",
        "## Sources",
        "",
        "| source_id | file | rows | sha256 | hash verified |",
        "|---|---|---|---|---|",
    ]
    for s in meta_source:
        lines.append(
            f"| {s['source_id']} | {s['filename']} | {s['row_count']:,} | "
            f"`{s['sha256']}` | {'yes' if s['hash_verified'] else 'no'} |"
        )
    lines += [
        "",
        "## Records per tribe (verbatim labels)",
        "",
        "| tribe | records |",
        "|---|---|",
    ]
    for tribe, count in sorted(tribe_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {tribe} | {count:,} |")
    lines += [
        "",
        "## Distinct normalized tokens",
        "",
        f"- fname: **{distinct['fname']:,}**",
        f"- mname: **{distinct['mname']:,}**",
        f"- sname: **{distinct['sname']:,}**",
        "",
        "## Surname support histogram",
        "",
        "| observations | surname tokens |",
        "|---|---|",
    ]
    for label, value in sname_hist.items():
        lines.append(f"| {label} | {value:,} |")
    lines += [
        "",
        f"- Surname tokens with support ≥ {min_support}: "
        f"**{sname_ge_min:,}** ({sname_ge_min / sname_total:.1%})",
        f"- Records whose label disagrees with the surname consensus "
        f"(support ≥ {min_support}): **{len(disagreements):,}**",
        "",
        "## Tribes too sparse to predict",
        "",
        f"Fewer than {sparse_surname_limit} surname tokens where this tribe is the consensus. "
        "The engine should assign these only on strong lexical evidence, else abstain.",
        "",
    ]
    for tribe in sparse:
        lines.append(f"- {tribe} — records {tribe_counts.get(tribe, 0):,}, owned surnames {owned.get(tribe, 0):,}")
    (out_dir / "corpus_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # --- tribe_support.md ---
    tlines = [
        "# Tribe Support",
        "",
        "| tribe | records | consensus surnames | consensus fnames |",
        "|---|---|---|---|",
    ]
    owned_f = {
        r["top_tribe"]: r["n"]
        for r in conn.execute(
            "SELECT top_tribe, COUNT(*) AS n FROM token_reference "
            "WHERE position = 'fname' GROUP BY top_tribe"
        )
    }
    for tribe, count in sorted(tribe_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        tlines.append(f"| {tribe} | {count:,} | {owned.get(tribe, 0):,} | {owned_f.get(tribe, 0):,} |")
    (out_dir / "tribe_support.md").write_text("\n".join(tlines) + "\n", encoding="utf-8")

    return {
        "out_dir": str(out_dir),
        "surname_rows": len(surname_rows),
        "disagreements": len(disagreements),
        "sparse_tribes": sparse,
        "files": [
            "corpus_summary.md",
            "surname_reference.csv",
            "label_consensus_disagreement.csv",
            "tribe_support.md",
        ],
    }

"""Tests for the corpus ingest / build / report pipeline."""

from __future__ import annotations

import csv
import json

import pytest

openpyxl = pytest.importorskip("openpyxl")

from kne.corpus.build import build
from kne.corpus.ingest import IngestError, ingest
from kne.corpus.report import generate
from kne.corpus.store import connect, get_meta

KIKUYU = "Agikuyu (Kikuyu)"
LUO = "Luo"

ROWS = [
    ("OTIENO", "", "ODHIAMBO", LUO),
    ("PETER", "OCHIENG", "ODHIAMBO", LUO),
    ("MARY", "WANJIKU", "ODHIAMBO", KIKUYU),
    ("JOHN", "", "KAMAU", KIKUYU),
    ("JOHN", "", "KAMAU", LUO),
    ("JANE", "", "WANJIKU", KIKUYU),
]


def _make_xlsx(path, rows, header=("fname", "mname", "sname", "Tribe")):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(header))
    for row in rows:
        ws.append(list(row))
    wb.save(path)
    return path


@pytest.fixture()
def corpus_db(tmp_path):
    src = _make_xlsx(tmp_path / "corpus.xlsx", ROWS)
    db = tmp_path / "corpus.db"
    summary = ingest(src, db, source_id="ref_v1")
    return db, summary


def _fetch(db, sql, params=()):
    conn = connect(db)
    try:
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


def test_ingest_summary_counts(corpus_db):
    _, summary = corpus_db
    assert summary["records_ingested"] == 6
    assert summary["skipped_blank_tribe"] == 0
    assert summary["hash_verified"] is False
    assert summary["tribe_count"] == 2


def test_name_observations(corpus_db):
    db, _ = corpus_db
    obs = {
        (r["token"], r["position"], r["tribe"]): r["count"]
        for r in _fetch(db, "SELECT token, position, tribe, count FROM name_observations")
    }
    assert obs[("ODHIAMBO", "sname", LUO)] == 2
    assert obs[("ODHIAMBO", "sname", KIKUYU)] == 1
    assert obs[("KAMAU", "sname", KIKUYU)] == 1
    assert obs[("KAMAU", "sname", LUO)] == 1
    assert obs[("JOHN", "fname", KIKUYU)] == 1
    assert obs[("JOHN", "fname", LUO)] == 1
    assert obs[("OCHIENG", "mname", LUO)] == 1
    assert ("OTIENO", "mname", LUO) not in obs  # blank middle name contributes nothing


def test_combo_observations(corpus_db):
    db, _ = corpus_db
    combos = {
        (r["combo_type"], r["token_key"], r["tribe"]): r["count"]
        for r in _fetch(db, "SELECT combo_type, token_key, tribe, count FROM combo_observations")
    }
    assert combos[("fname_sname", "JOHN|KAMAU", KIKUYU)] == 1
    assert combos[("fname_sname", "JOHN|KAMAU", LUO)] == 1
    assert combos[("mname_sname", "OCHIENG|ODHIAMBO", LUO)] == 1
    assert combos[("fname_mname_sname", "PETER|OCHIENG|ODHIAMBO", LUO)] == 1


def test_token_reference_values(corpus_db):
    db, _ = corpus_db
    ref = {
        (r["token"], r["position"]): r
        for r in _fetch(db, "SELECT * FROM token_reference")
    }
    odh = ref[("ODHIAMBO", "sname")]
    assert odh["support"] == 3
    assert odh["distinct_tribes"] == 2
    assert odh["top_tribe"] == LUO
    assert odh["top_share"] == pytest.approx(2 / 3, abs=1e-6)
    assert odh["entropy"] == pytest.approx(0.9182958, abs=1e-6)
    assert json.loads(odh["dist_json"]) == pytest.approx({LUO: 0.666667, KIKUYU: 0.333333}, abs=1e-6)

    # Tie broken deterministically by tribe name (Agikuyu... sorts before Luo).
    kamau = ref[("KAMAU", "sname")]
    assert kamau["support"] == 2
    assert kamau["top_tribe"] == KIKUYU
    assert kamau["top_share"] == pytest.approx(0.5)
    assert kamau["entropy"] == pytest.approx(1.0)


def test_corpus_version_stable_and_data_sensitive(tmp_path):
    db = tmp_path / "c.db"
    src_a = _make_xlsx(tmp_path / "a.xlsx", ROWS)
    v1 = ingest(src_a, db, source_id="ref_v1")["corpus_version"]
    v2 = ingest(src_a, db, source_id="ref_v1")["corpus_version"]
    assert v1 == v2  # same bytes -> same version, and re-ingest is idempotent
    assert _fetch(db, "SELECT COUNT(*) AS n FROM records")[0]["n"] == 6

    changed = ROWS[:-1] + [("JANE", "", "WANJIKU", LUO)]
    src_b = _make_xlsx(tmp_path / "b.xlsx", changed)
    v3 = ingest(src_b, db, source_id="ref_v1")["corpus_version"]
    assert v3 != v1


def test_manifest_hash_mismatch_blocks_unless_forced(tmp_path):
    src = _make_xlsx(tmp_path / "corpus.xlsx", ROWS)
    manifest = tmp_path / "MANIFEST.json"
    manifest.write_text(json.dumps({"sha256": "DEADBEEF"}), encoding="utf-8")
    db = tmp_path / "c.db"
    with pytest.raises(IngestError, match="hash mismatch"):
        ingest(src, db, source_id="ref_v1", manifest_path=manifest)
    summary = ingest(src, db, source_id="ref_v1", manifest_path=manifest, force=True)
    assert summary["hash_verified"] is False
    assert summary["records_ingested"] == 6


def test_column_autodetection_and_missing_column(tmp_path):
    db = tmp_path / "c.db"
    src = _make_xlsx(
        tmp_path / "renamed.xlsx", ROWS, header=("First", "Middle", "Surname", "Community")
    )
    summary = ingest(
        src, db, source_id="ref_v1",
        fname_col="first", mname_col="Middle", sname_col="surname", tribe_col="Community",
    )
    assert summary["records_ingested"] == 6

    with pytest.raises(IngestError, match="missing required column"):
        ingest(src, tmp_path / "d.db", source_id="ref_v1")  # defaults don't match headers


def test_blank_tribe_rows_skipped(tmp_path):
    db = tmp_path / "c.db"
    rows = ROWS + [("NOBODY", "", "NOWHERE", "")]
    src = _make_xlsx(tmp_path / "corpus.xlsx", rows)
    summary = ingest(src, db, source_id="ref_v1")
    assert summary["records_ingested"] == 6
    assert summary["skipped_blank_tribe"] == 1


def test_report_outputs(corpus_db, tmp_path):
    db, _ = corpus_db
    out = tmp_path / "report"
    summary = generate(db, out, min_support=2, sparse_surname_limit=100)

    assert (out / "corpus_summary.md").is_file()
    assert (out / "tribe_support.md").is_file()

    surnames = list(csv.DictReader((out / "surname_reference.csv").open(encoding="utf-8")))
    by_name = {r["surname"]: r for r in surnames}
    assert by_name["ODHIAMBO"]["top_tribe"] == LUO
    assert by_name["ODHIAMBO"]["support"] == "3"

    disagreements = list(
        csv.DictReader((out / "label_consensus_disagreement.csv").open(encoding="utf-8"))
    )
    pairs = {(int(d["row_index"]), d["tribe_raw"], d["surname_top_tribe"]) for d in disagreements}
    assert (3, KIKUYU, LUO) in pairs      # MARY ... ODHIAMBO labelled Kikuyu vs Luo consensus
    assert (5, LUO, KIKUYU) in pairs      # JOHN KAMAU labelled Luo vs Kikuyu consensus
    assert summary["disagreements"] == 2


def test_build_is_callable_standalone(corpus_db):
    db, _ = corpus_db
    conn = connect(db)
    try:
        before = get_meta(conn, "corpus_version")
        result = build(conn)
        conn.commit()
    finally:
        conn.close()
    assert result["corpus_version"] == before
    assert result["token_reference_rows"] > 0

"""Tests for `kne evaluate`."""

from __future__ import annotations

import csv
import json

import pytest

from kne.evaluate import EvaluateError, evaluate


def _write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def _predictions(path, rows):
    # rows: (fname, mname, sname, tribe_predicted, tribe_status, tribe_confidence)
    return _write_csv(
        path,
        ["fname", "mname", "sname", "tribe_predicted", "tribe_status", "tribe_confidence"],
        rows,
    )


def _gold(path, rows):
    # rows: (fname, mname, sname, tribe_gold, tier)
    return _write_csv(path, ["fname", "mname", "sname", "tribe_gold", "tier"], rows)


def test_basic_coverage_precision_and_tiers(tmp_path):
    preds = _predictions(tmp_path / "p.csv", [
        ("A", "", "MWANGI", "Agikuyu (Kikuyu)", "assigned", "0.95"),
        ("B", "", "OTIENO", "Luo", "assigned", "0.90"),
        ("C", "", "ODHIAMBO", "Agikuyu (Kikuyu)", "assigned", "0.80"),  # wrong
        ("D", "", "JUMA", "", "review", "0.40"),
        ("E", "", "OMONDI", "", "generic", "0.30"),
    ])
    gold = _gold(tmp_path / "g.csv", [
        ("A", "", "MWANGI", "Agikuyu (Kikuyu)", "B"),
        ("B", "", "OTIENO", "Luo", "B"),
        ("C", "", "ODHIAMBO", "Luo", "A"),
        ("D", "", "JUMA", "Luo", "A"),
        ("E", "", "OMONDI", "Luo", "B"),
    ])
    s = evaluate(preds, gold, tmp_path / "out")
    assert s["matched_rows"] == 5
    o = s["overall"]
    assert o["decided"] == 3 and o["correct"] == 2
    assert o["precision"] == pytest.approx(2 / 3, abs=1e-4)
    assert o["coverage"] == pytest.approx(3 / 5, abs=1e-4)
    assert o["abstained"] == 2
    assert o["abstention_breakdown"] == {"generic": 1, "review": 1}
    # tiers split out
    assert s["by_tier"]["A"]["n"] == 2 and s["by_tier"]["A"]["correct"] == 0
    assert s["by_tier"]["B"]["n"] == 3 and s["by_tier"]["B"]["precision"] == pytest.approx(1.0)
    # per gold tribe (B, C, D, E are all gold Luo)
    assert s["by_gold_tribe"]["Luo"]["n"] == 4
    assert s["by_gold_tribe"]["Luo"]["decided"] == 2 and s["by_gold_tribe"]["Luo"]["correct"] == 1
    # files written
    assert (tmp_path / "out" / "evaluate_g.json").is_file()
    assert (tmp_path / "out" / "evaluate_g.md").is_file()


def test_untiered_gold_and_confusions(tmp_path):
    preds = _predictions(tmp_path / "p.csv", [
        ("X", "", "KAMAU", "Akamba (Kamba)", "assigned", "0.9"),
        ("Y", "", "WEKESA", "Luo", "assigned", "0.9"),
    ])
    gold = _write_csv(tmp_path / "g.csv", ["fname", "mname", "sname", "tribe_gold"], [
        ("X", "", "KAMAU", "Agikuyu (Kikuyu)"),
        ("Y", "", "WEKESA", "Abaluhya (Luhya)"),
    ])
    s = evaluate(preds, gold, tmp_path / "out")
    assert s["by_tier"]["untiered"]["n"] == 2
    assert {(c["gold"], c["predicted"]) for c in s["top_confusions"]} == {
        ("Agikuyu (Kikuyu)", "Akamba (Kamba)"), ("Abaluhya (Luhya)", "Luo")
    }


def test_no_match_is_an_error(tmp_path):
    preds = _predictions(tmp_path / "p.csv", [("A", "", "MWANGI", "Luo", "assigned", "0.9")])
    gold = _gold(tmp_path / "g.csv", [("Z", "", "ZZZ", "Luo", "B")])
    with pytest.raises(EvaluateError):
        evaluate(preds, gold, tmp_path / "out")


def test_coverage_at_precision_curve(tmp_path):
    rows = [(f"P{i}", "", "MWANGI", "Agikuyu (Kikuyu)", "assigned", f"{0.5 + i*0.05:.2f}") for i in range(10)]
    preds = _predictions(tmp_path / "p.csv", rows)
    gold = _gold(tmp_path / "g.csv", [(f"P{i}", "", "MWANGI", "Agikuyu (Kikuyu)", "B") for i in range(10)])
    s = evaluate(preds, gold, tmp_path / "out")
    curve = {r["min_confidence"]: r for r in s["coverage_at_precision"]}
    assert curve[0.50]["coverage"] == pytest.approx(1.0)
    assert curve[0.90]["coverage"] < curve[0.50]["coverage"]
    assert all(r["precision"] == pytest.approx(1.0) for r in s["coverage_at_precision"])

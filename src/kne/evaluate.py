"""`kne evaluate` -- score a classification output against a labelled gold set.

Joins a kne prediction file (.xlsx/.csv, as written by `kne classify`) to a gold
CSV on the normalised (fname, mname, sname) triple, then reports coverage,
precision and the abstention breakdown -- overall, per gold tier, and per tribe.

This is a standing regression check: re-run it against the same gold file after
any corpus or config change and compare. It never changes engine behaviour.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .normalize import normalize_name
from .pipeline import _load_input

# statuses that count as "the engine committed to a label"
DECIDED = frozenset({"assigned", "confirmed", "refined", "conflict"})
ABSTAINED = frozenset({"review", "generic", "unverified"})

_PRED_ALIASES = ("tribe_predicted", "tribe", "predicted", "prediction")
_STATUS_ALIASES = ("tribe_status", "status")
_CONF_ALIASES = ("tribe_confidence", "confidence", "conf")
_GOLD_ALIASES = ("tribe_gold", "gold", "tribe", "label")
_TIER_ALIASES = ("tier", "gold_tier", "stratum")


class EvaluateError(RuntimeError):
    pass


@dataclass(frozen=True)
class _Row:
    triple: tuple[str, str, str]
    gold: str
    tier: str
    pred: str
    status: str
    confidence: float


def _pick(header: list[str], aliases: tuple[str, ...]) -> int | None:
    lower = {h.strip().lower(): i for i, h in enumerate(header) if h}
    for a in aliases:
        if a in lower:
            return lower[a]
    return None


def _triple(fn: str, mn: str, sn: str) -> tuple[str, str, str]:
    return (normalize_name(fn), normalize_name(mn), normalize_name(sn))


def _load_gold(path: Path) -> dict[tuple[str, str, str], tuple[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.reader(text.splitlines())
    rows = list(reader)
    if not rows:
        raise EvaluateError(f"gold file is empty: {path}")
    header = [c.strip() for c in rows[0]]
    lower = {h.lower(): i for i, h in enumerate(header)}
    need = [c for c in ("fname", "mname", "sname") if c not in lower]
    if need:
        raise EvaluateError(f"gold file missing column(s): {', '.join(need)}; header: {', '.join(header)}")
    gi = _pick(header, _GOLD_ALIASES)
    if gi is None:
        raise EvaluateError(f"gold file has no tribe_gold column; header: {', '.join(header)}")
    ti = _pick(header, _TIER_ALIASES)
    fi, mi, si = lower["fname"], lower["mname"], lower["sname"]

    out: dict[tuple[str, str, str], tuple[str, str]] = {}
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        cell = lambda idx: r[idx].strip() if idx is not None and idx < len(r) else ""
        gold = cell(gi)
        if not gold:
            continue
        out[_triple(cell(fi), cell(mi), cell(si))] = (gold, cell(ti) or "untiered")
    if not out:
        raise EvaluateError(f"no usable gold rows in {path}")
    return out


def _load_predictions(path: Path) -> list[tuple[tuple[str, str, str], str, str, float]]:
    header, rows = _load_input(path, None)
    if not header:
        raise EvaluateError(f"prediction file has no header: {path}")
    lower = {h.strip().lower(): i for i, h in enumerate(header) if h}
    for c in ("fname", "mname", "sname"):
        if c not in lower:
            raise EvaluateError(f"prediction file missing '{c}'; header: {', '.join(header)}")
    pi = _pick(header, _PRED_ALIASES)
    if pi is None:
        raise EvaluateError(
            f"prediction file has no tribe_predicted column; header: {', '.join(header)}"
        )
    sti = _pick(header, _STATUS_ALIASES)
    ci = _pick(header, _CONF_ALIASES)
    fi, mi, si = lower["fname"], lower["mname"], lower["sname"]

    out = []
    for r in rows:
        cell = lambda idx: (r[idx].strip() if idx is not None and idx < len(r) and r[idx] is not None else "")
        pred = cell(pi)
        status = cell(sti) or ("assigned" if pred else "review")
        try:
            conf = float(cell(ci))
        except ValueError:
            conf = 0.0
        out.append((_triple(cell(fi), cell(mi), cell(si)), pred, status, conf))
    return out


def _rate(num: int, den: int) -> float:
    return num / den if den else 0.0


def _block(rows: list[_Row]) -> dict[str, object]:
    n = len(rows)
    decided = [r for r in rows if r.status in DECIDED]
    abstained = [r for r in rows if r.status in ABSTAINED]
    correct = sum(1 for r in decided if r.pred == r.gold)
    ab = Counter(r.status for r in abstained)
    return {
        "n": n,
        "decided": len(decided),
        "coverage": round(_rate(len(decided), n), 4),
        "correct": correct,
        "precision": round(_rate(correct, len(decided)), 4),
        "recall": round(_rate(correct, n), 4),
        "abstained": len(abstained),
        "abstention_rate": round(_rate(len(abstained), n), 4),
        "abstention_breakdown": {k: ab.get(k, 0) for k in sorted(ABSTAINED) if ab.get(k)},
    }


def _coverage_at_precision(rows: list[_Row]) -> list[dict[str, float]]:
    decided = [r for r in rows if r.status in DECIDED]
    n = len(rows)
    out = []
    for thr in (0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99):
        kept = [r for r in decided if r.confidence >= thr]
        if not kept:
            continue
        corr = sum(1 for r in kept if r.pred == r.gold)
        out.append({
            "min_confidence": thr,
            "coverage": round(_rate(len(kept), n), 4),
            "precision": round(_rate(corr, len(kept)), 4),
        })
    return out


def evaluate(pred_path: str | Path, gold_path: str | Path, out_dir: str | Path) -> dict[str, object]:
    pred_path, gold_path, out_dir = Path(pred_path), Path(gold_path), Path(out_dir)
    if not pred_path.is_file():
        raise EvaluateError(f"prediction file not found: {pred_path}")
    if not gold_path.is_file():
        raise EvaluateError(f"gold file not found: {gold_path}")

    gold = _load_gold(gold_path)
    preds = _load_predictions(pred_path)
    pred_by_triple = {t: (p, s, c) for t, p, s, c in preds}

    matched: list[_Row] = []
    unmatched_gold = 0
    for triple, (g, tier) in gold.items():
        hit = pred_by_triple.get(triple)
        if hit is None:
            unmatched_gold += 1
            continue
        p, s, c = hit
        matched.append(_Row(triple, g, tier, p, s, c))

    if not matched:
        raise EvaluateError(
            "no gold rows matched the prediction file on (fname, mname, sname). "
            "Did you run `kne classify` on the same input the gold set was drawn from?"
        )

    by_tier: dict[str, list[_Row]] = defaultdict(list)
    by_gold_tribe: dict[str, list[_Row]] = defaultdict(list)
    for r in matched:
        by_tier[r.tier].append(r)
        by_gold_tribe[r.gold].append(r)

    pred_prec: dict[str, dict[str, int]] = defaultdict(lambda: {"assigned": 0, "correct": 0})
    for r in matched:
        if r.status in DECIDED:
            pred_prec[r.pred]["assigned"] += 1
            pred_prec[r.pred]["correct"] += int(r.pred == r.gold)

    confusion = Counter(
        (r.gold, r.pred) for r in matched if r.status in DECIDED and r.pred != r.gold
    )

    summary = {
        "tool_version": __version__,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "prediction_file": pred_path.name,
        "gold_file": gold_path.name,
        "gold_rows": len(gold),
        "matched_rows": len(matched),
        "unmatched_gold_rows": unmatched_gold,
        "overall": _block(matched),
        "by_tier": {k: _block(v) for k, v in sorted(by_tier.items())},
        "by_gold_tribe": {
            k: _block(v) for k, v in sorted(by_gold_tribe.items(), key=lambda kv: -len(kv[1]))
        },
        "precision_by_predicted_tribe": {
            k: {"assigned": v["assigned"], "precision": round(_rate(v["correct"], v["assigned"]), 4)}
            for k, v in sorted(pred_prec.items(), key=lambda kv: -kv[1]["assigned"])
        },
        "coverage_at_precision": _coverage_at_precision(matched),
        "top_confusions": [
            {"gold": g, "predicted": p, "n": n}
            for (g, p), n in confusion.most_common(20)
        ],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = gold_path.stem
    (out_dir / f"evaluate_{stem}.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / f"evaluate_{stem}.md").write_text(_render_markdown(summary), encoding="utf-8")
    summary["outputs"] = {
        "json": str(out_dir / f"evaluate_{stem}.json"),
        "markdown": str(out_dir / f"evaluate_{stem}.md"),
    }
    return summary


def _render_markdown(s: dict) -> str:
    L: list[str] = []
    L.append(f"# Evaluation: `{s['prediction_file']}` vs `{s['gold_file']}`\n")
    L.append(f"- generated {s['generated_utc']} (kne {s['tool_version']})")
    L.append(f"- gold rows: {s['gold_rows']}  |  matched to predictions: {s['matched_rows']}"
             f"  |  unmatched: {s['unmatched_gold_rows']}\n")

    def table(title: str, blocks: dict[str, dict]) -> None:
        L.append(f"## {title}\n")
        L.append("| group | n | coverage | precision | recall | abstained | review/generic/unverified |")
        L.append("|---|--:|--:|--:|--:|--:|---|")
        for k, b in blocks.items():
            ab = b["abstention_breakdown"]
            abstr = ", ".join(f"{kk}={vv}" for kk, vv in ab.items()) or "-"
            L.append(f"| {k} | {b['n']} | {b['coverage']:.1%} | {b['precision']:.1%} | "
                     f"{b['recall']:.1%} | {b['abstained']} | {abstr} |")
        L.append("")

    o = s["overall"]
    L.append("## Overall\n")
    L.append(f"- coverage **{o['coverage']:.1%}** ({o['decided']}/{o['n']} assigned)")
    L.append(f"- precision **{o['precision']:.1%}** ({o['correct']}/{o['decided']} correct)")
    L.append(f"- abstained {o['abstained']} ({o['abstention_rate']:.1%}) - {o['abstention_breakdown']}\n")

    table("By tier", s["by_tier"])
    table("By gold tribe", s["by_gold_tribe"])

    L.append("## Coverage at precision\n")
    L.append("| min confidence | coverage | precision |")
    L.append("|--:|--:|--:|")
    for r in s["coverage_at_precision"]:
        L.append(f"| {r['min_confidence']:.2f} | {r['coverage']:.1%} | {r['precision']:.1%} |")
    L.append("")

    if s["top_confusions"]:
        L.append("## Top confusions (gold -> predicted, assigned rows)\n")
        L.append("| gold | predicted | n |")
        L.append("|---|---|--:|")
        for c in s["top_confusions"]:
            L.append(f"| {c['gold']} | {c['predicted']} | {c['n']} |")
        L.append("")

    L.append("---\n_A name-based association is not proof of an individual's ethnicity, "
             "community identity, ancestry, or self-identification._")
    return "\n".join(L) + "\n"

"""Formatted multi-sheet .xlsx writer for classification results."""

from __future__ import annotations

import json
from pathlib import Path

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from .pipeline import DECIDED_STATUSES, ClassifyResult

_WIDTH_SAMPLE = 4000
_STATUS_TINTS = {
    "assigned": "#E4F1E1",
    "confirmed": "#E4F1E1",
    "refined": "#E1EAF6",
    "review": "#FCF2E0",
    "unverified": "#FAF6EC",
    "conflict": "#FADBD8",
    "generic": "#ECECEC",
}


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _column_widths(fieldnames: list[str], rows: list[dict[str, str]]) -> list[int]:
    widths = []
    sample = rows[:_WIDTH_SAMPLE]
    for name in fieldnames:
        longest = max([len(name), *(len(str(r.get(name, ""))) for r in sample)] or [len(name)])
        widths.append(_clamp(longest + 2, 10, 60))
    return widths


def _write_data_sheet(
    workbook, title: str, result: ClassifyResult, rows: list[dict[str, str]],
    header_fmt, conf_fmt, status_fmts: dict[str, object],
) -> None:
    ws = workbook.add_worksheet(title)
    ws.freeze_panes(1, 0)
    fieldnames = result.fieldnames
    for c, width in enumerate(_column_widths(fieldnames, rows)):
        ws.set_column(c, c, width)
    ws.write_row(0, 0, fieldnames, header_fmt)

    conf_idx = (fieldnames.index(result.confidence_column)
                if result.confidence_column in fieldnames else -1)
    for r, row in enumerate(rows, start=1):
        for c, name in enumerate(fieldnames):
            value = row.get(name, "")
            if c == conf_idx and value not in ("", None):
                try:
                    ws.write_number(r, c, float(value), conf_fmt)
                    continue
                except (TypeError, ValueError):
                    pass
            ws.write(r, c, "" if value is None else str(value))

    last_col = len(fieldnames) - 1
    ws.autofilter(0, 0, max(len(rows), 1), last_col)

    if result.status_column in fieldnames and rows:
        letter = xl_col_to_name(fieldnames.index(result.status_column))
        cell_range = f"A2:{xl_col_to_name(last_col)}{len(rows) + 1}"
        for status, fmt in status_fmts.items():
            ws.conditional_format(cell_range, {
                "type": "formula",
                "criteria": f'=${letter}2="{status}"',
                "format": fmt,
            })


def _write_summary_sheet(workbook, result: ClassifyResult, title_fmt, key_fmt) -> None:
    ws = workbook.add_worksheet("Summary")
    ws.set_column(0, 0, 34)
    ws.set_column(1, 1, 60)
    m = result.manifest
    total = max(sum(result.status_counts.values()), 1)
    decided = sum(v for k, v in result.status_counts.items() if k in DECIDED_STATUSES)
    decided += result.status_counts.get("conflict", 0)
    reviewish = sum(v for k, v in result.status_counts.items()
                    if k in {"review", "generic", "unverified"})
    decided_conf = [
        float(r[result.confidence_column]) for r in result.rows
        if r.get(result.status_column) in DECIDED_STATUSES and r.get(result.confidence_column)
    ]
    mean_conf = sum(decided_conf) / len(decided_conf) if decided_conf else 0.0

    row = 0

    def put(label, value, fmt=None):
        nonlocal row
        ws.write(row, 0, label, key_fmt if fmt is None else fmt)
        ws.write(row, 1, value)
        row += 1

    ws.write(row, 0, "Run metadata", title_fmt); row += 1
    for label, key in (
        ("Input file", "input_file"), ("Input SHA-256", "input_sha256"),
        ("Mode", "mode"), ("Corpus version", "corpus_version"),
        ("Evidence dictionary SHA-256", "reference_dictionary_sha256"),
        ("Config digest", "config_digest"), ("Scorer", "scorer"),
        ("Tool version", "tool_version"), ("Generated (UTC)", "generated_utc"),
    ):
        put(label, str(m.get(key, "")))
    put("Detected columns", json.dumps(m.get("columns_detected", {}), ensure_ascii=False))
    row += 1

    ws.write(row, 0, "Headline metrics", title_fmt); row += 1
    put("Total rows", total)
    put("Decided (assigned/confirmed/refined/conflict)", f"{decided} ({decided / total:.1%})")
    put("Needs review (review/generic/unverified)", f"{reviewish} ({reviewish / total:.1%})")
    put("Conflicts", result.status_counts.get("conflict", 0))
    put("Mean confidence of decided rows", f"{mean_conf:.3f}")
    row += 1

    ws.write(row, 0, "Status", title_fmt)
    ws.write(row, 1, "Count"); row += 1
    for status, count in sorted(result.status_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        ws.write(row, 0, status)
        ws.write(row, 1, f"{count} ({count / total:.1%})")
        row += 1
    row += 1

    tribe_counts: dict[str, int] = {}
    for r in result.rows:
        if r.get(result.status_column) in DECIDED_STATUSES:
            t = r.get("tribe_predicted", "")
            if t:
                tribe_counts[t] = tribe_counts.get(t, 0) + 1
    ws.write(row, 0, "Decided tribe", title_fmt)
    ws.write(row, 1, "Count"); row += 1
    for tribe, count in sorted(tribe_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        ws.write(row, 0, tribe)
        ws.write(row, 1, count)
        row += 1
    row += 1

    ws.write(
        row, 0,
        "A name-based association is not proof of an individual's ethnicity, "
        "community identity, ancestry, or self-identification.",
    )


def _flatten(data: dict, prefix: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for key, value in data.items():
        full = f"{prefix}{key}"
        if isinstance(value, dict):
            out.extend(_flatten(value, f"{full}."))
        elif isinstance(value, (list, tuple)):
            out.append((full, json.dumps(list(value), ensure_ascii=False)))
        else:
            out.append((full, "" if value is None else str(value)))
    return out


def _write_manifest_sheet(workbook, result: ClassifyResult, key_fmt) -> None:
    ws = workbook.add_worksheet("Run Manifest")
    ws.set_column(0, 0, 34)
    ws.set_column(1, 1, 80)
    ws.write_row(0, 0, ["key", "value"], key_fmt)
    for r, (key, value) in enumerate(_flatten(result.manifest), start=1):
        ws.write(r, 0, key)
        ws.write(r, 1, value)


def write_workbook(path: str | Path, result: ClassifyResult) -> None:
    workbook = xlsxwriter.Workbook(str(path), {"constant_memory": True, "in_memory": False})
    header_fmt = workbook.add_format(
        {"bold": True, "font_color": "#FFFFFF", "bg_color": "#2F3B4C", "border": 1}
    )
    title_fmt = workbook.add_format({"bold": True, "font_size": 12})
    key_fmt = workbook.add_format({"bold": True})
    conf_fmt = workbook.add_format({"num_format": "0.000"})
    status_fmts = {s: workbook.add_format({"bg_color": tint}) for s, tint in _STATUS_TINTS.items()}

    _write_data_sheet(workbook, "Classified Data", result, result.rows,
                      header_fmt, conf_fmt, status_fmts)
    _write_summary_sheet(workbook, result, title_fmt, key_fmt)
    if result.review_rows:
        _write_data_sheet(workbook, "Review Queue", result, result.review_rows,
                          header_fmt, conf_fmt, status_fmts)
    _write_manifest_sheet(workbook, result, header_fmt)
    workbook.close()

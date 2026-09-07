"""End-to-end classification: read a table, classify each row, write CSV or XLSX + manifest."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .config import Config, load_config
from .corpus.ingest import _read_xlsx_rows
from .decide import decide
from .features import extract
from .hashing import sha256_file
from .model.loglinear import LogLinearScorer
from .reference import CorpusReference, EvidenceReference

POSITIONS = ("fname", "mname", "sname")
FRESH_COLUMNS = ("tribe_predicted", "tribe_confidence", "tribe_status",
                 "tribe_basis", "tribe_alt_candidates")
REFINE_EXTRA = ("tribe_original", "tribe_suggested")
REVIEW_STATUSES = frozenset({"review", "conflict", "generic", "unverified"})
DECIDED_STATUSES = frozenset({"assigned", "confirmed", "refined"})

_CANONICAL = {"fname": "fname", "mname": "mname", "sname": "sname", "tribe": "Tribe"}
_ALIASES = {
    "fname": ("fname", "first", "firstname", "firstnames", "givenname", "forename"),
    "mname": ("mname", "middle", "middlename", "middlenames", "othername", "othernames", "secondname"),
    "sname": ("sname", "surname", "surnames", "last", "lastname", "familyname"),
    "tribe": ("tribe", "tribegroup", "ethnicity", "ethnicgroup", "community", "clan"),
}


class ClassifyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ColumnMap:
    fname: int
    mname: int | None
    sname: int
    tribe: int | None
    matched: dict[str, str]


@dataclass
class ClassifyResult:
    fieldnames: list[str]
    rows: list[dict[str, str]]
    review_rows: list[dict[str, str]]
    status_counts: dict[str, int]
    mode: str
    manifest: dict[str, object]
    status_column: str = "tribe_status"
    confidence_column: str = "tribe_confidence"


def _squash(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _load_input(path: Path, sheet: str | None) -> tuple[list[str], list[list[str]]]:
    if path.suffix.lower() == ".xlsx":
        rows_iter = _read_xlsx_rows(path, sheet)
        try:
            header = ["" if c is None else str(c).strip() for c in next(rows_iter)]
        except StopIteration:
            return [], []
        data = [["" if c is None else str(c).strip() for c in row] for row in rows_iter]
        return header, data
    if sheet is not None:
        raise ClassifyError("--sheet only applies to .xlsx input")
    text = path.read_text(encoding="utf-8-sig")
    sample = text[:8192]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
    except csv.Error:
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        delimiter = "\t" if "\t" in first_line else ","
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    if not rows:
        return [], []
    return [c.strip() for c in rows[0]], [list(r) for r in rows[1:]]


def _resolve_columns(header: list[str], overrides: dict[str, str | None]) -> ColumnMap:
    exact = {h.strip().lower(): i for i, h in enumerate(header) if h}
    squashed: dict[str, int] = {}
    for i, h in enumerate(header):
        if h:
            squashed.setdefault(_squash(h), i)

    resolved: dict[str, int | None] = {}
    matched: dict[str, str] = {}
    for logical in ("fname", "mname", "sname", "tribe"):
        required = logical in ("fname", "sname")
        override = overrides.get(logical)
        if override:
            idx = exact.get(override.strip().lower())
            if idx is None:
                raise ClassifyError(
                    f"column '{override}' (for {logical}) not found; header: {', '.join(header)}"
                )
        else:
            idx = exact.get(_CANONICAL[logical].lower())
            if idx is None:
                for alias in _ALIASES[logical]:
                    if alias in squashed:
                        idx = squashed[alias]
                        break
        if idx is None:
            if required:
                raise ClassifyError(
                    f"could not find a '{logical}' column (tried {_CANONICAL[logical]!r} and "
                    f"aliases); pass --{logical}-col. Header: {', '.join(header)}"
                )
            resolved[logical] = None
            continue
        resolved[logical] = idx
        matched[logical] = header[idx]

    return ColumnMap(resolved["fname"], resolved["mname"], resolved["sname"],
                     resolved["tribe"], matched)


def _cell(row: list[str], idx: int | None) -> str:
    if idx is None or idx >= len(row):
        return ""
    value = row[idx]
    return "" if value is None else str(value).strip()


def _classify_rows(
    header: list[str], rows: list[list[str]], columns: ColumnMap, mode: str,
    corpus: CorpusReference, evidence: EvidenceReference, scorer: LogLinearScorer,
    config: Config,
) -> ClassifyResult:
    col = {"fname": columns.fname, "mname": columns.mname, "sname": columns.sname}
    out_columns = list(FRESH_COLUMNS) + (list(REFINE_EXTRA) if mode == "refine" else [])
    fieldnames = list(dict.fromkeys([*header, *out_columns]))

    status_counts: Counter[str] = Counter()
    out_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []

    for row in rows:
        record = {p: _cell(row, col[p]) for p in POSITIONS}
        existing = _cell(row, columns.tribe)
        features = extract(record, corpus, evidence)
        result = scorer.score(features)
        d = decide(result, features, existing, mode, config)
        status_counts[d.status] += 1

        base = {header[i] if i < len(header) else f"col{i}": (row[i] if i < len(row) else "")
                for i in range(max(len(header), len(row)))}
        extra = {
            "tribe_predicted": d.tribe,
            "tribe_confidence": f"{d.confidence:.4f}",
            "tribe_status": d.status,
            "tribe_basis": d.basis,
            "tribe_alt_candidates": d.alt_candidates,
        }
        if mode == "refine":
            extra["tribe_original"] = d.tribe_original or existing
            extra["tribe_suggested"] = d.tribe_suggested
        merged = {**base, **extra}
        out_rows.append(merged)
        if d.status in REVIEW_STATUSES:
            review_rows.append(merged)

    review_rows.sort(key=lambda r: float(r["tribe_confidence"]))
    manifest = {
        "mode": mode,
        "input_rows": len(rows),
        "columns_detected": columns.matched,
        "corpus_version": corpus.corpus_version,
        "reference_dictionary_sha256": evidence.dictionary_sha256,
        "config_source": config.source_path,
        "config_digest": config.digest(),
        "scorer": f"{scorer.name}:{scorer.version}",
        "target_tribe_count": len(corpus.target_tribes),
        "gate": asdict(config.gate),
        "status_counts": dict(sorted(status_counts.items())),
        "tool_version": __version__,
    }
    return ClassifyResult(fieldnames, out_rows, review_rows, dict(status_counts), mode, manifest)


def classify_file(
    input_path: str | Path,
    output_path: str | Path,
    *,
    db_path: str | Path,
    reference_dir: str | Path,
    config: Config | None = None,
    mode: str = "auto",
    sheet: str | None = None,
    fname_col: str | None = None,
    mname_col: str | None = None,
    sname_col: str | None = None,
    tribe_col: str | None = None,
) -> dict[str, object]:
    input_path, output_path = Path(input_path), Path(output_path)
    if not input_path.is_file():
        raise ClassifyError(f"input file not found: {input_path}")
    fmt = output_path.suffix.lower()
    if fmt not in (".xlsx", ".csv", ".tsv"):
        raise ClassifyError(f"unsupported output extension '{fmt}'; use .xlsx, .csv or .tsv")
    config = config or load_config()

    header, rows = _load_input(input_path, sheet)
    if not header or not rows:
        raise ClassifyError("input has no data rows")

    columns = _resolve_columns(
        header,
        {"fname": fname_col, "mname": mname_col, "sname": sname_col, "tribe": tribe_col},
    )

    if mode == "auto":
        has_labels = columns.tribe is not None and any(_cell(r, columns.tribe) for r in rows)
        mode = "refine" if has_labels else "fresh"
    elif mode == "refine" and columns.tribe is None:
        raise ClassifyError("--mode refine needs a tribe/ethnicity column; none found")
    if mode not in ("fresh", "refine"):
        raise ClassifyError(f"unknown mode: {mode}")

    corpus = CorpusReference.load(db_path, config)
    evidence = EvidenceReference.load(reference_dir, config)
    scorer = LogLinearScorer(corpus, evidence, config)

    result = _classify_rows(header, rows, columns, mode, corpus, evidence, scorer, config)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.manifest = {
        "input_file": input_path.name,
        "input_sha256": sha256_file(input_path).upper(),
        **result.manifest,
        "output_format": fmt.lstrip("."),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }

    if fmt == ".xlsx":
        from .report_xlsx import write_workbook

        write_workbook(output_path, result)
        outputs = {"workbook": output_path.name}
    else:
        outputs = _write_csv_outputs(result, output_path)
    result.manifest["outputs"] = outputs

    manifest_path = output_path.with_name(f"{output_path.stem}.manifest.json")
    manifest_path.write_text(
        json.dumps(result.manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    return {**result.manifest, "review_rows": len(result.review_rows)}


def _write_csv_outputs(result: ClassifyResult, output_path: Path) -> dict[str, str]:
    _write_csv(output_path, result.fieldnames, result.rows)
    review_path = output_path.with_name(f"{output_path.stem}.review.csv")
    _write_csv(review_path, result.fieldnames, result.review_rows)
    return {"classified": output_path.name, "review_queue": review_path.name}


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

"""Command-line entry point for the Kenya Name Engine."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from . import __version__, paths
from .corpus import build as corpus_build
from .corpus.ingest import IngestError, ingest
from .corpus.report import generate as corpus_report
from .corpus.store import connect, get_meta
from .pipeline import ClassifyError, classify_file


def _add_corpus_commands(sub: argparse._SubParsersAction) -> None:
    corpus = sub.add_parser("corpus", help="build and inspect the labelled name corpus")
    csub = corpus.add_subparsers(dest="corpus_cmd", required=True)

    p_ingest = csub.add_parser("ingest", help="load a labelled .xlsx dataset into the corpus store")
    p_ingest.add_argument("path", nargs="?", type=Path, default=paths.DEFAULT_CORPUS_FILE,
                          help=f"labelled .xlsx (default: {paths.DEFAULT_CORPUS_FILE})")
    p_ingest.add_argument("--db", type=Path, default=paths.DEFAULT_DB)
    p_ingest.add_argument("--source-id", default="ref_v1")
    p_ingest.add_argument("--manifest", type=Path, default=paths.DEFAULT_CORPUS_MANIFEST)
    p_ingest.add_argument("--fname-col", default="fname")
    p_ingest.add_argument("--mname-col", default="mname")
    p_ingest.add_argument("--sname-col", default="sname")
    p_ingest.add_argument("--tribe-col", default="Tribe")
    p_ingest.add_argument("--force", action="store_true", help="ingest even if the file hash does not match the manifest")

    p_build = csub.add_parser("build", help="recompute derived tables from stored records")
    p_build.add_argument("--db", type=Path, default=paths.DEFAULT_DB)

    p_report = csub.add_parser("report", help="write data-quality reports")
    p_report.add_argument("--db", type=Path, default=paths.DEFAULT_DB)
    p_report.add_argument("--out", type=Path, default=paths.CORPUS_REPORT_DIR)

    p_status = csub.add_parser("status", help="show corpus sources, counts and version")
    p_status.add_argument("--db", type=Path, default=paths.DEFAULT_DB)


def _add_classify_command(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("classify", help="add or refine a Tribe column on a CSV/TSV/XLSX file")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, required=True, help="output path (.xlsx, .csv or .tsv)")
    p.add_argument("--db", type=Path, default=paths.DEFAULT_DB)
    p.add_argument("--reference", type=Path, default=paths.ROOT / "reference")
    p.add_argument("--config", type=Path, default=None, help="TOML config (default: config/default.toml)")
    p.add_argument("--mode", choices=("auto", "fresh", "refine"), default="auto")
    p.add_argument("--sheet", default=None, help="worksheet name for .xlsx input (default: first)")
    p.add_argument("--fname-col", default=None, help="override first-name column")
    p.add_argument("--mname-col", default=None, help="override middle-name column")
    p.add_argument("--sname-col", default=None, help="override surname column")
    p.add_argument("--tribe-col", default=None, help="override tribe/ethnicity column")


def _cmd_classify(args: argparse.Namespace) -> int:
    if not Path(args.db).is_file():
        print(f"error: no corpus database at {args.db}; run `kne corpus ingest` first", file=sys.stderr)
        return 2
    from .config import load_config

    try:
        summary = classify_file(
            args.input, args.output,
            db_path=args.db, reference_dir=args.reference,
            config=load_config(args.config), mode=args.mode, sheet=args.sheet,
            fname_col=args.fname_col, mname_col=args.mname_col,
            sname_col=args.sname_col, tribe_col=args.tribe_col,
        )
    except ClassifyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    detected = summary.get("columns_detected", {})
    if detected:
        print("detected columns: "
              + ", ".join(f"{k}={v!r}" for k, v in detected.items()), file=sys.stderr)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _cmd_corpus_ingest(args: argparse.Namespace) -> int:
    try:
        summary = ingest(
            args.path, args.db,
            source_id=args.source_id,
            manifest_path=args.manifest,
            fname_col=args.fname_col, mname_col=args.mname_col,
            sname_col=args.sname_col, tribe_col=args.tribe_col,
            force=args.force,
        )
    except IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not summary["hash_verified"]:
        print("note: file hash was not verified against a manifest", file=sys.stderr)
    return 0


def _cmd_corpus_build(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    try:
        summary = corpus_build(conn)
        conn.commit()
    finally:
        conn.close()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _cmd_corpus_report(args: argparse.Namespace) -> int:
    if not Path(args.db).is_file():
        print(f"error: no corpus database at {args.db}; run `kne corpus ingest` first", file=sys.stderr)
        return 2
    summary = corpus_report(args.db, args.out)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _cmd_corpus_status(args: argparse.Namespace) -> int:
    if not Path(args.db).is_file():
        print(f"error: no corpus database at {args.db}; run `kne corpus ingest` first", file=sys.stderr)
        return 2
    conn = connect(args.db)
    try:
        sources = [dict(r) for r in conn.execute(
            "SELECT source_id, filename, sha256, row_count, ingested_at, hash_verified FROM sources ORDER BY source_id"
        )]
        records = conn.execute("SELECT COUNT(*) AS n FROM records").fetchone()["n"]
        tokens = conn.execute("SELECT COUNT(*) AS n FROM token_reference").fetchone()["n"]
        tribes = json.loads(get_meta(conn, "tribe_list_json", "{}"))
        status = {
            "db": str(args.db),
            "corpus_version": get_meta(conn, "corpus_version"),
            "schema_version": get_meta(conn, "schema_version"),
            "built_at": get_meta(conn, "built_at"),
            "sources": sources,
            "records": records,
            "token_reference_rows": tokens,
            "tribes": tribes,
        }
    finally:
        conn.close()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0


_DISPATCH = {
    ("corpus", "ingest"): _cmd_corpus_ingest,
    ("corpus", "build"): _cmd_corpus_build,
    ("corpus", "report"): _cmd_corpus_report,
    ("corpus", "status"): _cmd_corpus_status,
    ("classify", None): _cmd_classify,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kne", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_corpus_commands(sub)
    _add_classify_command(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = _DISPATCH.get((args.command, getattr(args, "corpus_cmd", None)))
    if handler is None:  # pragma: no cover - argparse enforces required subcommands
        print("error: unknown command", file=sys.stderr)
        return 2
    try:
        return handler(args)
    except sqlite3.DatabaseError as exc:
        print(f"error: database error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

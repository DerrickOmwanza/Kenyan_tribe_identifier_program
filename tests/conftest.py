"""Shared fixtures for the kne test suite."""

from __future__ import annotations

import csv
from dataclasses import replace

import openpyxl
import pytest

from kne.config import Config, GenericFname
from kne.corpus.ingest import ingest

KIKUYU = "Agikuyu (Kikuyu)"
LUO = "Luo"
KAMBA = "Akamba (Kamba)"
GENERIC = "Generic / borrowed (Christian, Swahili, or pan-Kenyan)"
UNCERTAIN = "Uncertain / could not confidently place"

# A small but structured corpus:
#  - MWANGI/WANJIKU strongly Kikuyu, OTIENO/ODHIAMBO strongly Luo, MUTUA Kamba
#  - JUMA shared Luo/Kikuyu (ambiguous surname)
#  - OMULA only ever "Generic / borrowed" and "Uncertain" (meta labels)
#  - JOHN spread across everything (non-informative first name)
_CORPUS_ROWS: list[tuple[str, str, str, str]] = []
for _ in range(20):
    _CORPUS_ROWS += [
        ("JOHN", "KAMANDE", "MWANGI", KIKUYU),
        ("MARY", "WANJIRU", "WANJIKU", KIKUYU),
        ("JOHN", "OCHIENG", "OTIENO", LUO),
        ("PETER", "ODHIAMBO", "OCHIENG", LUO),
        ("MARY", "MUMBUA", "MUTUA", KAMBA),
    ]
for _ in range(10):
    _CORPUS_ROWS += [
        ("PETER", "JUMA", "JUMA", LUO),
        ("JOHN", "JUMA", "JUMA", KIKUYU),
    ]
for _ in range(6):
    _CORPUS_ROWS += [
        ("JOHN", "", "OMULA", GENERIC),
        ("MARY", "", "OMULA", UNCERTAIN),
    ]
# SAM is a deliberately non-informative first name: it mirrors the whole-corpus
# tribe distribution, so KL(SAM || prior) is ~0 and it is flagged generic.
_CORPUS_ROWS += [("SAM", mname, sname, tribe) for (_f, mname, sname, tribe) in list(_CORPUS_ROWS)]


def make_xlsx(path, rows, header=("fname", "mname", "sname", "Tribe")):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(header))
    for row in rows:
        ws.append(list(row))
    wb.save(path)
    return path


def write_evidence_dir(path, rows: list[dict[str, str]]):
    path.mkdir(parents=True, exist_ok=True)
    fieldnames = ["name_token", "normalized_token", "primary_association", "alternative_associations",
                  "category", "strength", "evidence_score", "evidence_type", "position_scope",
                  "source_type", "source_reference", "source_url", "evidence_note",
                  "review_status", "reviewer", "date_added", "notes"]
    with (path / "name_dictionary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return path


@pytest.fixture()
def test_config() -> Config:
    """Defaults, but with a low generic-fname support floor for tiny corpora."""
    return replace(Config(), generic_fname=GenericFname(min_support=20, max_kl_from_prior=0.25))


@pytest.fixture()
def corpus_db(tmp_path):
    src = make_xlsx(tmp_path / "corpus.xlsx", _CORPUS_ROWS)
    db = tmp_path / "corpus.db"
    ingest(src, db, source_id="ref_v1")
    return db


@pytest.fixture()
def evidence_dir(tmp_path):
    return write_evidence_dir(
        tmp_path / "reference",
        [{"name_token": "MUTUA", "normalized_token": "MUTUA", "primary_association": "Kamba",
          "strength": "strong", "position_scope": "any_position",
          "source_reference": "SRC-TEST", "review_status": "approved"},
         {"name_token": "DRAFTONLY", "normalized_token": "DRAFTONLY", "primary_association": "Luo",
          "strength": "strong", "position_scope": "any_position",
          "source_reference": "SRC-TEST", "review_status": "draft"}],
    )

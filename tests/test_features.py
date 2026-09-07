"""Tests for kne.features.extract."""

from __future__ import annotations

from kne.features import extract
from kne.reference import CorpusReference, EvidenceReference

from conftest import KIKUYU, LUO


def _refs(corpus_db, evidence_dir, test_config):
    corpus = CorpusReference.load(corpus_db, test_config)
    evidence = EvidenceReference.load(evidence_dir, test_config)
    return corpus, evidence


def test_token_and_combo_hits(corpus_db, evidence_dir, test_config):
    corpus, evidence = _refs(corpus_db, evidence_dir, test_config)
    f = extract({"fname": "JOHN", "mname": "KAMANDE", "sname": "MWANGI"}, corpus, evidence)

    sname_hit = next(h for h in f.token_hits if h.position == "sname")
    assert sname_hit.token == "MWANGI"
    assert sname_hit.ref is not None and sname_hit.ref.dist.get(KIKUYU, 0) == 1.0

    assert any(c.combo_type == "fname_sname" and c.token_key == "JOHN|MWANGI" for c in f.combo_hits)
    assert f.has_signal


def test_generic_first_name_flagged(corpus_db, evidence_dir, test_config):
    corpus, evidence = _refs(corpus_db, evidence_dir, test_config)
    assert "SAM" in corpus.generic_fnames
    f = extract({"fname": "SAM", "mname": "", "sname": "ZZZUNKNOWN"}, corpus, evidence)
    sam = next(h for h in f.token_hits if h.token == "SAM")
    assert sam.generic is True
    # SAM suppressed, surname unknown, no combo -> no usable signal
    assert f.has_signal is False


def test_evidence_hits_respect_review_status_and_scope(corpus_db, evidence_dir, test_config):
    corpus, evidence = _refs(corpus_db, evidence_dir, test_config)
    f = extract({"fname": "MUTUA", "mname": "", "sname": "ZZZ"}, corpus, evidence)
    assert [h.tribe for h in f.evidence_hits] == ["Akamba (Kamba)"]

    g = extract({"fname": "DRAFTONLY", "mname": "", "sname": "ZZZ"}, corpus, evidence)
    assert g.evidence_hits == []


def test_no_signal_for_all_unknown(corpus_db, evidence_dir, test_config):
    corpus, evidence = _refs(corpus_db, evidence_dir, test_config)
    f = extract({"fname": "QWER", "mname": "TYUI", "sname": "OPAS"}, corpus, evidence)
    assert f.has_signal is False
    assert f.combo_hits == [] and f.evidence_hits == []

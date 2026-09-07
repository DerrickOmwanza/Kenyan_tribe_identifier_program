"""Tests for the log-linear scorer."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from kne.features import extract
from kne.model.loglinear import LogLinearScorer
from kne.reference import CorpusReference, DistRef, EvidenceReference

from conftest import KAMBA, KIKUYU, LUO


def _scorer(corpus_db, evidence_dir, config):
    corpus = CorpusReference.load(corpus_db, config)
    evidence = EvidenceReference.load(evidence_dir, config)
    return LogLinearScorer(corpus, evidence, config), corpus, evidence


def test_posterior_is_a_distribution(corpus_db, evidence_dir, test_config):
    scorer, corpus, evidence = _scorer(corpus_db, evidence_dir, test_config)
    f = extract({"fname": "JOHN", "mname": "KAMANDE", "sname": "MWANGI"}, corpus, evidence)
    result = scorer.score(f)
    assert set(result.posterior) == set(corpus.target_tribes)
    assert sum(result.posterior.values()) == pytest.approx(1.0)
    assert result.ranked()[0][0] == KIKUYU


def test_p_smoothed_matches_formula(corpus_db, evidence_dir, test_config):
    scorer, *_ = _scorer(corpus_db, evidence_dir, test_config)
    ref = DistRef(support=10, dist={LUO: 0.8, KIKUYU: 0.2})
    a = scorer.alpha
    prior = scorer.prior
    expected = (10 * 0.8 + a * prior[LUO]) / (10 + a)
    assert scorer._p_smoothed(ref, LUO) == pytest.approx(expected)


def test_low_support_shrinks_to_prior(corpus_db, evidence_dir, test_config):
    scorer, *_ = _scorer(corpus_db, evidence_dir, test_config)
    weak = DistRef(support=1, dist={LUO: 1.0})
    strong = DistRef(support=500, dist={LUO: 1.0})
    assert scorer._p_smoothed(weak, LUO) < scorer._p_smoothed(strong, LUO)
    assert scorer._p_smoothed(weak, LUO) == pytest.approx(
        (1 + scorer.alpha * scorer.prior[LUO]) / (1 + scorer.alpha)
    )


def test_evidence_weight_lifts_the_mapped_tribe(corpus_db, evidence_dir, test_config):
    # MUTUA surname is Kamba in the corpus AND an approved evidence hit -> very confident.
    scorer, corpus, evidence = _scorer(corpus_db, evidence_dir, test_config)
    f = extract({"fname": "MARY", "mname": "MUMBUA", "sname": "MUTUA"}, corpus, evidence)
    result = scorer.score(f)
    assert result.ranked()[0][0] == KAMBA
    assert any("evidence:" in b for b in result.basis)

    no_ev = replace(test_config, weights=replace(test_config.weights, evidence=0.0))
    s2, c2, e2 = _scorer(corpus_db, evidence_dir, no_ev)
    r2 = s2.score(extract({"fname": "MARY", "mname": "MUMBUA", "sname": "MUTUA"}, c2, e2))
    assert result.posterior[KAMBA] > r2.posterior[KAMBA]


def test_ambiguous_surname_is_not_confident(corpus_db, evidence_dir, test_config):
    scorer, corpus, evidence = _scorer(corpus_db, evidence_dir, test_config)
    result = scorer.score(extract({"fname": "", "mname": "", "sname": "JUMA"}, corpus, evidence))
    top, p = result.ranked()[0]
    assert p < 0.9  # JUMA is split Luo/Kikuyu in the corpus


def test_p_meta_from_meta_only_surname(corpus_db, evidence_dir, test_config):
    scorer, corpus, evidence = _scorer(corpus_db, evidence_dir, test_config)
    result = scorer.score(extract({"fname": "", "mname": "", "sname": "OMULA"}, corpus, evidence))
    assert result.p_meta == pytest.approx(1.0)


def test_deterministic(corpus_db, evidence_dir, test_config):
    scorer, corpus, evidence = _scorer(corpus_db, evidence_dir, test_config)
    rec = {"fname": "JOHN", "mname": "OCHIENG", "sname": "OTIENO"}
    a = scorer.score(extract(rec, corpus, evidence)).posterior
    b = scorer.score(extract(rec, corpus, evidence)).posterior
    assert a == b

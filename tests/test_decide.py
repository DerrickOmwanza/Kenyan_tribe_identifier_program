"""Tests for the confidence gate (kne.decide)."""

from __future__ import annotations

from kne.decide import decide
from kne.model.base import ScoreResult

from conftest import KIKUYU, LUO, UNCERTAIN

SPARSE = "Maasai"


def _features(signal=True):
    # has_signal is a property; fake it with one combo-less token hit via a stub.
    class F:
        has_signal = signal
    return F()


def _score(posterior, p_meta=0.0):
    return ScoreResult(posterior=posterior, p_meta=p_meta, basis=["sname:X"])


def test_pass_assigns_in_fresh_mode(test_config):
    d = decide(_score({KIKUYU: 0.9, LUO: 0.1}), _features(), "", "fresh", test_config)
    assert (d.status, d.tribe) == ("assigned", KIKUYU)


def test_margin_failure_is_review(test_config):
    d = decide(_score({KIKUYU: 0.55, LUO: 0.45}), _features(), "", "fresh", test_config)
    assert d.status == "review" and d.tribe == ""


def test_no_signal_is_review(test_config):
    d = decide(_score({KIKUYU: 0.99, LUO: 0.01}), _features(signal=False), "", "fresh", test_config)
    assert d.status == "review"


def test_sparse_tribe_needs_higher_bar(test_config):
    # 0.80 clears tau (0.75) but not sparse_tribe_tau (0.90)
    d = decide(_score({SPARSE: 0.80, LUO: 0.05}), _features(), "", "fresh", test_config)
    assert d.status == "review"
    d2 = decide(_score({SPARSE: 0.93, LUO: 0.02}), _features(), "", "fresh", test_config)
    assert (d2.status, d2.tribe) == ("assigned", SPARSE)


def test_generic_status_when_meta_dominates(test_config):
    d = decide(_score({KIKUYU: 0.5, LUO: 0.4}, p_meta=0.8), _features(), "", "fresh", test_config)
    assert d.status == "generic"


def test_refine_confirmed_and_alias(test_config):
    d = decide(_score({KIKUYU: 0.95}), _features(), "Kikuyu", "refine", test_config)
    assert d.status == "confirmed" and d.tribe_original == "Kikuyu"


def test_refine_conflict_preserves_original(test_config):
    d = decide(_score({KIKUYU: 0.97, LUO: 0.01}), _features(), "Luo", "refine", test_config)
    assert d.status == "conflict"
    assert d.tribe == "Luo" and d.tribe_suggested == KIKUYU


def test_refine_weak_disagreement_is_review(test_config):
    d = decide(_score({KIKUYU: 0.80, LUO: 0.05}), _features(), "Luo", "refine", test_config)
    assert d.status == "review" and d.tribe == "Luo"


def test_refine_unverified_when_gate_fails(test_config):
    d = decide(_score({KIKUYU: 0.5, LUO: 0.45}), _features(), "Luo", "refine", test_config)
    assert d.status == "unverified" and d.tribe == "Luo"


def test_refine_uncertain_label_gets_refined(test_config):
    d = decide(_score({KIKUYU: 0.96, LUO: 0.01}), _features(), UNCERTAIN, "refine", test_config)
    assert d.status == "refined" and d.tribe == KIKUYU and d.tribe_original == UNCERTAIN

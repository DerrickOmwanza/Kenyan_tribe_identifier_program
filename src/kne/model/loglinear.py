"""Interpretable log-linear hybrid scorer.

logit(t) = w_evidence * evidence_score(t)
         + Sigma_position  w_position * ln P_smoothed(t | token, position)
         + w_combo         * ln P_smoothed(t | best name-combination)
         + w_morph         * morph_score(t)          # disabled while w_morph == 0

posterior = softmax(logit / temperature) over the target tribes.
Pure arithmetic over a sorted tribe list — deterministic, no RNG.
"""

from __future__ import annotations

import math

from ..config import Config
from ..features import RecordFeatures
from ..reference import CorpusReference, DistRef, EvidenceReference
from .base import ScoreResult

_COMBO_SPECIFICITY = {"fname_mname_sname": 2, "mname_sname": 1, "fname_sname": 0}


class LogLinearScorer:
    name = "loglinear"
    version = "1"

    def __init__(self, corpus: CorpusReference, evidence: EvidenceReference, config: Config):
        self.corpus = corpus
        self.evidence = evidence
        self.config = config
        self.targets = corpus.target_tribes
        self.prior = corpus.tribe_prior
        self.alpha = float(config.smoothing_alpha)
        self.temperature = max(float(config.softmax_temperature), 1e-6)
        self.w = config.weights
        self.non_target = tuple(config.non_target_labels)

    def _p_smoothed(self, ref: DistRef, tribe: str) -> float:
        """Dirichlet-smoothed P(tribe | token); shrinks to the global prior at low support."""
        raw = ref.dist.get(tribe, 0.0)
        return (ref.support * raw + self.alpha * self.prior.get(tribe, 0.0)) / (
            ref.support + self.alpha
        )

    def _apply_dist(self, logits: dict[str, float], ref: DistRef, weight: float) -> None:
        if weight == 0.0:
            return
        for tribe in self.targets:
            logits[tribe] += weight * math.log(self._p_smoothed(ref, tribe))

    def score(self, features: RecordFeatures) -> ScoreResult:
        logits = {tribe: 0.0 for tribe in self.targets}
        basis: list[str] = []

        position_weight = {"fname": self.w.fname, "mname": self.w.mname, "sname": self.w.sname}
        for hit in features.token_hits:
            if hit.ref is None or hit.generic:
                if hit.generic:
                    basis.append(f"{hit.position}:{hit.token}(generic, suppressed)")
                continue
            self._apply_dist(logits, hit.ref, position_weight[hit.position])
            top = max(hit.ref.dist, key=hit.ref.dist.get)
            basis.append(f"{hit.position}:{hit.token}(top={top} s={hit.ref.support})")

        if features.combo_hits:
            best = max(
                features.combo_hits,
                key=lambda c: (c.ref.support, _COMBO_SPECIFICITY[c.combo_type]),
            )
            self._apply_dist(logits, best.ref, self.w.combo)
            top = max(best.ref.dist, key=best.ref.dist.get)
            basis.append(f"combo:{best.token_key}(top={top} s={best.ref.support})")

        for hit in features.evidence_hits:
            if hit.tribe in logits and self.w.evidence != 0.0:
                logits[hit.tribe] += self.w.evidence * hit.score
                basis.append(f"evidence:{hit.tribe}({hit.strength})")

        posterior = self._softmax(logits)
        p_meta = self._p_meta(features)
        return ScoreResult(posterior=posterior, p_meta=p_meta, basis=basis)

    def _softmax(self, logits: dict[str, float]) -> dict[str, float]:
        if not logits:
            return {}
        hi = max(logits.values())
        exps = {t: math.exp((v - hi) / self.temperature) for t, v in logits.items()}
        z = sum(exps.values()) or 1.0
        return {t: e / z for t, e in exps.items()}

    def _p_meta(self, features: RecordFeatures) -> float:
        """Share of the surname's corpus mass sitting on non-target (meta) labels."""
        for hit in features.token_hits:
            if hit.position == "sname" and hit.ref is not None:
                return sum(hit.ref.dist.get(label, 0.0) for label in self.non_target)
        return 0.0

"""Confidence gate: turn a posterior into an assignment, or abstain."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .features import RecordFeatures
from .model.base import ScoreResult

# fresh mode:  assigned | review | generic
# refine mode: confirmed | refined | conflict | unverified | review | generic
FRESH_STATUSES = ("assigned", "review", "generic")
REFINE_STATUSES = ("confirmed", "refined", "conflict", "unverified", "review", "generic")


@dataclass(frozen=True)
class Decision:
    tribe: str
    confidence: float
    status: str
    basis: str
    alt_candidates: str
    tribe_original: str = ""
    tribe_suggested: str = ""


def _alt(ranked: list[tuple[str, float]]) -> str:
    return "|".join(f"{t}:{p:.3f}" for t, p in ranked[:3] if p > 0.0)


def decide(
    score: ScoreResult,
    features: RecordFeatures,
    existing_label: str,
    mode: str,
    config: Config,
) -> Decision:
    ranked = score.ranked()
    basis = "; ".join(score.basis)
    existing = (existing_label or "").strip()
    existing_norm = config.tribe_aliases.get(existing, existing)
    non_target = set(config.non_target_labels)

    if not features.has_signal or not ranked:
        if mode == "refine" and existing:
            return Decision(existing, 0.0, "unverified", basis or "no name signal", "",
                            tribe_original=existing)
        return Decision("", 0.0, "review", basis or "no name signal", "")

    top_tribe, p_top = ranked[0]
    p_2nd = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = p_top - p_2nd
    conf = round(p_top, 4)
    alt = _alt(ranked)

    bar = config.gate.sparse_tribe_tau if top_tribe in set(config.sparse_tribes) else config.gate.tau
    passed = p_top >= bar and margin >= config.gate.delta

    if score.p_meta >= config.gate.generic_dominance and not passed:
        return Decision("", conf, "generic", basis, alt)

    if mode == "refine" and existing:
        if not passed:
            return Decision(existing, conf, "unverified", basis, alt, tribe_original=existing)
        if existing_norm == top_tribe or existing == top_tribe:
            return Decision(top_tribe, conf, "confirmed", basis, alt, tribe_original=existing)
        if existing in non_target or existing_norm in non_target:
            return Decision(top_tribe, conf, "refined", basis, alt,
                            tribe_original=existing, tribe_suggested=top_tribe)
        if p_top >= config.gate.tau_conflict:
            return Decision(existing, conf, "conflict", basis, alt,
                            tribe_original=existing, tribe_suggested=top_tribe)
        return Decision(existing, conf, "review", basis, alt, tribe_original=existing)

    # fresh mode, or refine mode with a blank existing label
    if passed:
        return Decision(top_tribe, conf, "assigned", basis, alt)
    return Decision("", conf, "review", basis, alt)

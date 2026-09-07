"""Shared scorer interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..features import RecordFeatures


@dataclass(frozen=True)
class ScoreResult:
    posterior: dict[str, float]        # over target tribes, sums to ~1
    p_meta: float = 0.0               # P(non-target labels | surname), for the "generic" status
    basis: list[str] = field(default_factory=list)

    def ranked(self) -> list[tuple[str, float]]:
        return sorted(self.posterior.items(), key=lambda kv: (-kv[1], kv[0]))


class Scorer(Protocol):
    name: str
    version: str

    def score(self, features: RecordFeatures) -> ScoreResult: ...

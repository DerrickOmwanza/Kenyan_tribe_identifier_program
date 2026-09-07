"""Per-record signal extraction for the classifier."""

from __future__ import annotations

from dataclasses import dataclass, field

from .normalize import name_tokens
from .reference import CorpusReference, DistRef, EvidenceHit, EvidenceReference

POSITIONS = ("fname", "mname", "sname")
COMBO_TYPES = ("fname_sname", "mname_sname", "fname_mname_sname")


@dataclass(frozen=True)
class TokenHit:
    position: str
    token: str
    ref: DistRef | None      # corpus token_reference entry, if any
    generic: bool            # a suppressed non-informative first name


@dataclass(frozen=True)
class ComboHit:
    combo_type: str
    token_key: str
    ref: DistRef


@dataclass(frozen=True)
class RecordFeatures:
    tokens: dict[str, list[str]]
    token_hits: list[TokenHit] = field(default_factory=list)
    combo_hits: list[ComboHit] = field(default_factory=list)
    evidence_hits: list[EvidenceHit] = field(default_factory=list)

    @property
    def has_signal(self) -> bool:
        return (
            any(h.ref is not None and not h.generic for h in self.token_hits)
            or bool(self.combo_hits)
            or bool(self.evidence_hits)
        )


def _combo_keys(tokens: dict[str, list[str]]) -> list[tuple[str, str]]:
    f = tokens["fname"][0] if tokens["fname"] else None
    m = tokens["mname"][0] if tokens["mname"] else None
    s = tokens["sname"][0] if tokens["sname"] else None
    keys: list[tuple[str, str]] = []
    if f and s:
        keys.append(("fname_sname", f"{f}|{s}"))
    if m and s:
        keys.append(("mname_sname", f"{m}|{s}"))
    if f and m and s:
        keys.append(("fname_mname_sname", f"{f}|{m}|{s}"))
    return keys


def extract(
    record: dict[str, str], corpus: CorpusReference, evidence: EvidenceReference
) -> RecordFeatures:
    tokens = {p: name_tokens(record.get(p, "")) for p in POSITIONS}

    token_hits: list[TokenHit] = []
    for position in POSITIONS:
        for token in tokens[position]:
            ref = corpus.tokens.get((token, position))
            generic = position == "fname" and token in corpus.generic_fnames
            token_hits.append(TokenHit(position, token, ref, generic))

    combo_hits = [
        ComboHit(combo_type, key, corpus.combos[(combo_type, key)])
        for combo_type, key in _combo_keys(tokens)
        if (combo_type, key) in corpus.combos
    ]

    seen: set[tuple[str, str, str]] = set()
    evidence_hits: list[EvidenceHit] = []
    for position in POSITIONS:
        for token in tokens[position]:
            for hit in evidence.by_token.get(token, ()):
                if hit.position_scope not in ("any_position", position):
                    continue
                dedup = (token, hit.tribe, hit.source)
                if dedup in seen:
                    continue
                seen.add(dedup)
                evidence_hits.append(hit)

    return RecordFeatures(tokens, token_hits, combo_hits, evidence_hits)

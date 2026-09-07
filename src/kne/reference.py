"""In-memory reference layers the scorer consults: the corpus and the evidence dictionary."""

from __future__ import annotations

import csv
import json
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .corpus.store import connect, get_meta
from .normalize import normalize_name

# Documentary-evidence strength -> multiplier applied to the evidence weight.
STRENGTH_SCORE = {
    "non_informative": 0.0,
    "weak": 0.4,
    "moderate": 0.7,
    "strong": 1.0,
    "very_strong": 1.3,
}


def _kl_divergence(dist: dict[str, float], prior: dict[str, float]) -> float:
    """KL(dist || prior) in bits. Small => the token distribution barely departs from base rate."""
    kl = 0.0
    for label, p in dist.items():
        q = prior.get(label, 0.0)
        if p > 0.0 and q > 0.0:
            kl += p * math.log2(p / q)
    return kl


@dataclass(frozen=True)
class DistRef:
    """A tribe distribution with its total support."""

    support: int
    dist: dict[str, float]  # tribe -> probability (raw, sums to ~1 over observed labels)


@dataclass(frozen=True)
class EvidenceHit:
    tribe: str
    strength: str
    score: float
    position_scope: str
    source: str


@dataclass(frozen=True)
class CorpusReference:
    tokens: dict[tuple[str, str], DistRef]
    combos: dict[tuple[str, str], DistRef]
    tribe_prior: dict[str, float]
    generic_fnames: frozenset[str]
    target_tribes: tuple[str, ...]
    all_labels: tuple[str, ...]
    corpus_version: str

    @classmethod
    def load(cls, db_path: str | Path, config: Config) -> "CorpusReference":
        conn = connect(db_path)
        try:
            return cls._load(conn, config)
        finally:
            conn.close()

    @classmethod
    def _load(cls, conn: sqlite3.Connection, config: Config) -> "CorpusReference":
        tribe_counts = json.loads(get_meta(conn, "tribe_list_json", "{}"))
        total = sum(tribe_counts.values()) or 1
        tribe_prior = {t: n / total for t, n in tribe_counts.items()}
        all_labels = tuple(sorted(tribe_counts))
        non_target = set(config.non_target_labels)
        target_tribes = tuple(t for t in all_labels if t not in non_target)

        tokens: dict[tuple[str, str], DistRef] = {}
        for r in conn.execute(
            "SELECT token, position, support, dist_json FROM token_reference"
        ):
            tokens[(r["token"], r["position"])] = DistRef(r["support"], json.loads(r["dist_json"]))

        combos: dict[tuple[str, str], DistRef] = {}
        for r in conn.execute(
            "SELECT combo_type, token_key, support, dist_json FROM combo_reference "
            "WHERE support >= ?",
            (config.combo_min_support,),
        ):
            combos[(r["combo_type"], r["token_key"])] = DistRef(
                r["support"], json.loads(r["dist_json"])
            )

        gf = config.generic_fname
        generic_fnames = frozenset(
            r["token"]
            for r in conn.execute(
                "SELECT token, support, dist_json FROM token_reference WHERE position = 'fname'"
            )
            if r["support"] >= gf.min_support
            and _kl_divergence(json.loads(r["dist_json"]), tribe_prior) <= gf.max_kl_from_prior
        )

        return cls(
            tokens=tokens,
            combos=combos,
            tribe_prior=tribe_prior,
            generic_fnames=generic_fnames,
            target_tribes=target_tribes,
            all_labels=all_labels,
            corpus_version=get_meta(conn, "corpus_version", "?"),
        )


@dataclass(frozen=True)
class EvidenceReference:
    by_token: dict[str, list[EvidenceHit]] = field(default_factory=dict)
    dictionary_sha256: str = ""

    @classmethod
    def load(cls, reference_dir: str | Path, config: Config) -> "EvidenceReference":
        reference_dir = Path(reference_dir)
        path = reference_dir / "name_dictionary.csv"
        if not path.is_file():
            return cls()
        from .hashing import sha256_file

        by_token: dict[str, list[EvidenceHit]] = {}
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("review_status") != "approved":
                    continue
                token = normalize_name(row.get("normalized_token") or row.get("name_token", ""))
                assoc = (row.get("primary_association") or "").strip()
                tribe = config.tribe_aliases.get(assoc, assoc)
                if not token or not tribe:
                    continue
                strength = (row.get("strength") or "moderate").strip()
                by_token.setdefault(token, []).append(
                    EvidenceHit(
                        tribe=tribe,
                        strength=strength,
                        score=STRENGTH_SCORE.get(strength, 0.7),
                        position_scope=(row.get("position_scope") or "any_position").strip(),
                        source=(row.get("source_reference") or "").strip(),
                    )
                )
        return cls(by_token=by_token, dictionary_sha256=sha256_file(path).upper())

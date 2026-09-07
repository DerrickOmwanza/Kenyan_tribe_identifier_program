"""Classifier configuration: dataclasses with baked-in defaults, optional TOML overlay."""

from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from .hashing import sha256_bytes
from .paths import ROOT

DEFAULT_CONFIG_PATH = ROOT / "config" / "default.toml"

_DEFAULT_TRIBE_ALIASES = {
    "Kikuyu": "Agikuyu (Kikuyu)",
    "Luo": "Luo",
    "Kamba": "Akamba (Kamba)",
    "Luhya": "Abaluhya (Luhya)",
    "Kisii": "Abagusii (Kisii)",
    "Meru": "Ameru (Meru)",
    "Embu": "Aembu / Mbeere (Embu)",
    "Kuria": "Abakuria (Kuria)",
}
_DEFAULT_SPARSE_TRIBES = (
    "Abakuria (Kuria)", "Aembu / Mbeere (Embu)", "Maasai", "Samburu",
    "Taita / Taveta", "Teso", "Turkana",
)
_DEFAULT_NON_TARGET_LABELS = (
    "Uncertain / could not confidently place",
    "Generic / borrowed (Christian, Swahili, or pan-Kenyan)",
)


@dataclass(frozen=True)
class Weights:
    evidence: float = 3.0
    fname: float = 0.4
    mname: float = 0.6
    sname: float = 1.0
    combo: float = 1.2
    morph: float = 0.0


@dataclass(frozen=True)
class Gate:
    tau: float = 0.75
    delta: float = 0.15
    tau_conflict: float = 0.85
    sparse_tribe_tau: float = 0.90
    generic_dominance: float = 0.60


@dataclass(frozen=True)
class GenericFname:
    min_support: int = 50
    # A first name is "non-informative" when its tribe distribution is close to the
    # global base rate: KL(token || prior) below this (bits). Tuned in Phase 4.
    max_kl_from_prior: float = 0.25


@dataclass(frozen=True)
class Config:
    smoothing_alpha: float = 8.0
    softmax_temperature: float = 1.0
    combo_min_support: int = 3
    weights: Weights = Weights()
    gate: Gate = Gate()
    generic_fname: GenericFname = GenericFname()
    tribe_aliases: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_TRIBE_ALIASES))
    sparse_tribes: tuple[str, ...] = _DEFAULT_SPARSE_TRIBES
    non_target_labels: tuple[str, ...] = _DEFAULT_NON_TARGET_LABELS
    source_path: str | None = None

    def digest(self) -> str:
        payload = asdict(self)
        payload.pop("source_path", None)
        return sha256_bytes(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def _merge_section(current, data: dict, key: str):
    section = data.get(key)
    if not isinstance(section, dict):
        return current
    return replace(current, **{k: v for k, v in section.items() if hasattr(current, k)})


def load_config(path: str | Path | None = None) -> Config:
    """Load a Config, overlaying a TOML file over the baked-in defaults.

    ``None`` uses ``config/default.toml`` if present, else pure defaults.
    """
    cfg = Config()
    if path is None:
        path = DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.is_file() else None
    if path is None:
        return cfg

    path = Path(path)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    scalars = {
        k: data[k]
        for k in ("smoothing_alpha", "softmax_temperature", "combo_min_support")
        if k in data
    }
    cfg = replace(cfg, **scalars)
    cfg = replace(
        cfg,
        weights=_merge_section(cfg.weights, data, "weights"),
        gate=_merge_section(cfg.gate, data, "gate"),
        generic_fname=_merge_section(cfg.generic_fname, data, "generic_fname"),
    )
    if isinstance(data.get("tribe_aliases"), dict):
        cfg = replace(cfg, tribe_aliases=dict(data["tribe_aliases"]))
    if isinstance(data.get("sparse_tribes"), list):
        cfg = replace(cfg, sparse_tribes=tuple(data["sparse_tribes"]))
    if isinstance(data.get("non_target_labels"), list):
        cfg = replace(cfg, non_target_labels=tuple(data["non_target_labels"]))
    return replace(cfg, source_path=str(path))

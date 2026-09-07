"""Corpus store: ingest labelled name datasets and derive tribe-association statistics."""

from __future__ import annotations

from .build import build
from .ingest import IngestError, ingest
from .report import generate as generate_report
from .store import connect

__all__ = ["build", "ingest", "IngestError", "generate_report", "connect"]

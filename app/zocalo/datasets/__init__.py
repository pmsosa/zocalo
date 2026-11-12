"""Datasets: the source registry, downloads, manual-download checks and population builders.

Filled in by registry.py (what each source is, its licence, how to get it) and loaders.py (how to read it).
"""
from __future__ import annotations

from .registry import SOURCES, datasets_dir, population_sources, source_status  # noqa: F401
from .loaders import build_population  # noqa: F401

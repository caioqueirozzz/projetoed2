"""Lightweight catalog reader for Music Explorer.

Reads ``data/processed/tracks_processed.csv`` (the output of
``preprocessing/build_dataset.py``) and exposes track metadata for dropdowns,
labels, and result display.  Feature columns are NOT loaded here — they are
handled entirely by the C++ core.

Usage:
    from services.dataset import load_catalog, get_track

    catalog = load_catalog()    # DataFrame indexed by track_id
    info = get_track(2)         # {"title": ..., "artist": ..., ...}
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Optional

import pandas as pd

_REPO_ROOT   = Path(__file__).resolve().parent.parent.parent
PROCESSED_CSV = Path(os.environ.get(
    "AME_DATASET_CSV", _REPO_ROOT / "data" / "processed" / "tracks_processed.csv"
)).expanduser().resolve()

# Columns to load from the CSV (skip the 44 feature columns).
_META_COLS = ["track_id", "title", "artist", "genre", "audio_path"]


def load_catalog() -> pd.DataFrame:
    """Return track metadata as a DataFrame indexed by track_id.

    Returns an empty DataFrame (with correct columns) when the CSV is missing.
    Decorated with @st.cache_data so subsequent calls within a session are free.
    """
    # Lazy import so the module can be used outside Streamlit (e.g., tests).
    try:
        import streamlit as st
        _cached = st.cache_data(_load_catalog_uncached)
        return _cached(_csv_signature())
    except ImportError:
        return _load_catalog_uncached(_csv_signature())


def _csv_signature() -> tuple[int, int] | None:
    if not PROCESSED_CSV.is_file():
        return None
    stat = PROCESSED_CSV.stat()
    return stat.st_mtime_ns, stat.st_size


def _load_catalog_uncached(signature=None) -> pd.DataFrame:
    if not PROCESSED_CSV.is_file():
        return pd.DataFrame(columns=["title", "artist", "genre", "audio_path"])
    df = pd.read_csv(PROCESSED_CSV, usecols=_META_COLS, index_col="track_id", keep_default_na=False)
    if df.index.has_duplicates:
        raise ValueError("IDs duplicados no catálogo; gere novamente o dataset.")
    return df


def get_track(track_id: int, catalog: Optional[pd.DataFrame] = None) -> dict:
    """Return metadata dict for a track, or a placeholder if not found."""
    if catalog is None:
        catalog = load_catalog()

    if track_id in catalog.index:
        row = catalog.loc[track_id]
        return {
            "track_id":  track_id,
            "title":     row.get("title", ""),
            "artist":    row.get("artist", ""),
            "genre":     row.get("genre", ""),
            "audio_path": row.get("audio_path", ""),
        }
    return {
        "track_id":  track_id,
        "title":     f"Track {track_id}",
        "artist":    "Unknown",
        "genre":     "Unknown",
        "audio_path": "",
    }


def audio_path(track_id: int, catalog: Optional[pd.DataFrame] = None) -> Optional[Path]:
    """Return the absolute path to the track's audio file, or None if missing."""
    info = get_track(track_id, catalog)
    audio_root = os.environ.get("FMA_AUDIO_DIR")
    tid = f"{track_id:06d}"
    if audio_root:
        full = Path(audio_root).expanduser() / tid[:3] / f"{tid}.mp3"
    else:
        stored = info.get("audio_path", "")
        if not stored:
            return None
        full = Path(stored)
        if not full.is_absolute():
            full = _REPO_ROOT / "data" / "raw" / full
    return full if full.is_file() and full.stat().st_size > 0 else None

"""Lightweight catalog reader for the Streamlit UI (plan §5, §23).

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

from pathlib import Path
from typing import Optional

import pandas as pd

_REPO_ROOT   = Path(__file__).resolve().parent.parent.parent
PROCESSED_CSV = _REPO_ROOT / "data" / "processed" / "tracks_processed.csv"

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
        return _cached()
    except ImportError:
        return _load_catalog_uncached()


def _load_catalog_uncached() -> pd.DataFrame:
    if not PROCESSED_CSV.exists():
        return pd.DataFrame(columns=["title", "artist", "genre", "audio_path"])

    # Read only metadata columns — avoids loading all 44 feature columns.
    try:
        df = pd.read_csv(
            PROCESSED_CSV,
            usecols=_META_COLS,
            index_col="track_id",
        )
        return df
    except Exception:
        # Corrupted CSV or schema mismatch — return empty rather than crash.
        return pd.DataFrame(columns=["title", "artist", "genre", "audio_path"])


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


def format_label(track_id: int, catalog: Optional[pd.DataFrame] = None) -> str:
    """Return a human-readable label: 'Title — Artist (#id)'."""
    info = get_track(track_id, catalog)
    return f"{info['title']} — {info['artist']} (#{track_id})"


def audio_path(track_id: int, catalog: Optional[pd.DataFrame] = None) -> Optional[Path]:
    """Return the absolute path to the track's audio file, or None if missing."""
    info = get_track(track_id, catalog)
    rel  = info.get("audio_path", "")
    if not rel:
        return None
    full = _REPO_ROOT / "data" / "raw" / rel
    return full if full.exists() else None

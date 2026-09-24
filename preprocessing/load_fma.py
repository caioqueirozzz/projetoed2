"""Load the raw FMA Medium metadata and feature tables (plan §3, §40).

Reads ``tracks.csv`` and ``features.csv`` from ``data/raw/`` and returns the
subset restricted to the FMA *medium* split.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def load_tracks(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Return track metadata for the FMA Medium subset.

    Parses the 2-level multi-index header of ``tracks.csv`` (row 0 = category,
    row 1 = field), filters to ``('set', 'subset') == 'medium'``, and returns a
    DataFrame indexed by ``track_id`` with flat columns:
    title, artist, genre, audio_path.
    """
    path = raw_dir / "tracks.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"FMA tracks file not found: {path}\n"
            "Download from https://github.com/mdeff/fma and extract to data/raw/"
        )

    tracks = pd.read_csv(path, index_col=0, header=[0, 1])
    tracks.index.name = "track_id"

    medium = tracks[tracks[("set", "subset")] == "medium"].copy()

    result = pd.DataFrame(index=medium.index)
    result["title"] = medium[("track", "title")].fillna("")
    result["artist"] = medium[("artist", "name")].fillna("Unknown")
    result["genre"] = medium[("track", "genre_top")].fillna("Unknown")
    result["audio_path"] = pd.Index(result.index).map(_fma_audio_path)

    print(f"[load_tracks] {len(result):,} medium tracks loaded from {path.name}")
    return result


def load_features(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Return the acoustic feature matrix indexed by track_id.

    Parses the 3-level multi-index header of ``features.csv``:
      Level 0 = feature group (mfcc, chroma_cqt, …)
      Level 1 = statistic (mean, std, …)
      Level 2 = coefficient index (01, 02, …)
    """
    path = raw_dir / "features.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"FMA features file not found: {path}\n"
            "Download from https://github.com/mdeff/fma and extract to data/raw/"
        )

    features = pd.read_csv(path, index_col=0, header=[0, 1, 2])
    features.index.name = "track_id"
    features.index = features.index.astype(int)

    print(
        f"[load_features] {len(features):,} tracks, "
        f"{features.shape[1]} feature columns loaded from {path.name}"
    )
    return features


def _fma_audio_path(track_id: int) -> str:
    """FMA Medium organises audio as fma_medium/{tid[:3]}/{tid}.mp3."""
    tid = f"{track_id:06d}"
    return f"fma_medium/{tid[:3]}/{tid}.mp3"


if __name__ == "__main__":
    t = load_tracks()
    f = load_features()
    print(t.head())
    print(f.iloc[:2, :6])

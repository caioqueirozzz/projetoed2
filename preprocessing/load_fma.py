"""Read official FMA multi-index tables and select the complete Medium subset."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def _validate_ids(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    ids = pd.to_numeric(frame.index, errors="raise")
    if (ids.isna().any() or (ids <= 0).any() or (ids % 1 != 0).any()
            or (ids > 2**31 - 1).any() or ids.has_duplicates):
        raise ValueError(f"{name}: track IDs must be unique positive 32-bit integers")
    frame.index = ids.astype(int)
    frame.index.name = "track_id"
    return frame


def load_tracks(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    tracks = _validate_ids(pd.read_csv(raw_dir / "tracks.csv", index_col=0, header=[0, 1]), "tracks.csv")
    required = [("set", "subset"), ("track", "title"),
                ("artist", "name"), ("track", "genre_top")]
    missing = [col for col in required if col not in tracks.columns]
    if missing:
        raise ValueError(f"tracks.csv: missing columns {missing}")

    # FMA subsets are nested: small ⊂ medium ⊂ large. Equality with 'medium'
    # would omit the 8,000 Small tracks that also belong to Medium.
    medium = tracks.loc[tracks[("set", "subset")].isin(["small", "medium"])]
    if medium.empty:
        raise ValueError("tracks.csv contains no Small/Medium tracks")
    result = pd.DataFrame(index=medium.index)
    result["title"] = medium[("track", "title")].fillna("")
    result["artist"] = medium[("artist", "name")].fillna("Unknown")
    result["genre"] = medium[("track", "genre_top")].fillna("Unknown")
    result["audio_path"] = [_fma_audio_path(tid) for tid in result.index]
    print(f"[load_tracks] {len(result):,} Small + Medium tracks")
    return result


def load_features(raw_dir: Path = RAW_DIR, track_ids=None) -> pd.DataFrame:
    """Read in chunks so unrelated Large tracks do not occupy memory."""
    chunks = []
    for chunk in pd.read_csv(raw_dir / "features.csv", index_col=0, header=[0, 1, 2], chunksize=5000):
        if track_ids is not None:
            chunk = chunk.loc[chunk.index.isin(track_ids)]
        if not chunk.empty:
            chunks.append(chunk)
    if not chunks:
        raise ValueError("features.csv has no matching tracks")
    result = _validate_ids(pd.concat(chunks), "features.csv")
    print(f"[load_features] {len(result):,} tracks")
    return result


def load_genres(raw_dir: Path = RAW_DIR) -> pd.DataFrame | None:
    path = raw_dir / "genres.csv"
    if not path.is_file():
        return None  # track.genre_top already contains the display genre.
    genres = pd.read_csv(path, index_col=0)
    if "title" not in genres or "parent" not in genres or genres.index.has_duplicates:
        raise ValueError("genres.csv: expected unique IDs and title/parent columns")
    genres.index.name = "genre_id"
    return genres


def _fma_audio_path(track_id: int) -> str:
    tid = f"{track_id:06d}"
    return f"fma_medium/{tid[:3]}/{tid}.mp3"

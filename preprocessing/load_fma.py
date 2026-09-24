"""Load the raw FMA Medium metadata and feature tables (plan §3, §40).

Reads ``tracks.csv`` and ``features.csv`` from ``data/raw/`` and returns the
subset restricted to the FMA *medium* split.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def load_tracks(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Load track metadata (id, title, artist, genre, split, subset).

    TODO: parse the multi-index header of the FMA ``tracks.csv`` and filter to
    ``subset == 'medium'``.
    """
    raise NotImplementedError("load_tracks: implement FMA tracks.csv parsing")


def load_features(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Load the pre-computed acoustic features indexed by track_id.

    TODO: parse the multi-index header of the FMA ``features.csv``.
    """
    raise NotImplementedError("load_features: implement FMA features.csv parsing")


if __name__ == "__main__":
    print("load_fma: scaffold — implement load_tracks / load_features")

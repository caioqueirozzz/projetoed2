"""End-to-end preprocessing pipeline (plan §8, §40 — Fase 1).

    raw FMA -> select medium subset -> handle missing -> select features
            -> normalize -> (Acoustic Key computed in C++) -> processed CSV

Entregável: ``data/processed/tracks_processed.csv``.
"""

from __future__ import annotations

from pathlib import Path

from clean_features import handle_missing, select_features
from load_fma import load_features, load_tracks
from normalize import min_max

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUT_CSV = PROCESSED_DIR / "tracks_processed.csv"


def build() -> None:
    """Run the full pipeline and write the processed dataset.

    TODO: join metadata + features on track_id, apply the cleaning and
    normalization steps, and write id/title/artist/genre + feature columns.
    The Acoustic Key is generated later by the C++ core (plan §43).
    """
    tracks = load_tracks()
    features = load_features()
    features = select_features(features)
    features = handle_missing(features)
    features = min_max(features)

    _ = (tracks, features)  # TODO: join + write OUTPUT_CSV
    raise NotImplementedError("build: join, assemble, and write tracks_processed.csv")


if __name__ == "__main__":
    build()

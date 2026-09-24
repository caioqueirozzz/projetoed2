"""End-to-end preprocessing pipeline (plan §8, §40 — Fase 1).

    raw FMA → filter medium → select 44 features → drop missing
            → min-max normalize → join metadata → write processed CSV

Entregáveis:
  data/processed/tracks_processed.csv    — metadata + 44 normalized features
  data/processed/normalization_params.json — min/max per column for query scaling

Usage (from project root):
    python preprocessing/build_dataset.py

Usage (from preprocessing/ directory):
    python build_dataset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from either the project root or preprocessing/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from clean_features import handle_missing, select_features
from load_fma import load_features, load_tracks
from normalize import min_max, save_params

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUT_CSV = PROCESSED_DIR / "tracks_processed.csv"
NORM_PARAMS = PROCESSED_DIR / "normalization_params.json"


def build() -> None:
    """Run the full pipeline and write the processed dataset.

    Pipeline steps:
      1. load_tracks  — parse tracks.csv, filter to medium subset (~25k tracks)
      2. load_features — parse features.csv (3-level multi-index, all groups)
      3. restrict features to medium-subset track IDs
      4. select_features — slice 44 columns, flatten names (clean_features.py)
      5. handle_missing — drop broken columns, then drop corrupt-audio rows
      6. min_max — scale every column to [0, 1] (required by AcousticKey)
      7. join — inner join metadata + features on track_id
      8. write OUTPUT_CSV and NORM_PARAMS
    """
    print("── Adaptive Music Explorer — Preprocessing Pipeline ──")

    # Step 1–2: load raw tables
    tracks_meta = load_tracks()
    features_raw = load_features()

    # Step 3: restrict the feature matrix to medium-subset tracks before any
    # selection or normalization (avoids computing stats over large/small tracks).
    medium_ids = tracks_meta.index
    features_raw = features_raw.loc[features_raw.index.isin(medium_ids)]
    print(f"[build] features restricted to medium subset: {len(features_raw):,} tracks")

    # Steps 4–6: clean and normalize
    features_sel = select_features(features_raw)
    features_clean = handle_missing(features_sel)
    features_norm, norm_params = min_max(features_clean)

    # Step 7: inner join — only tracks present in both metadata and clean features
    result = tracks_meta.join(features_norm, how="inner")
    n_tracks = len(result)
    n_feature_cols = features_norm.shape[1]

    print(
        f"[build] final dataset: {n_tracks:,} tracks × "
        f"{result.shape[1]} columns ({n_feature_cols} feature dims)"
    )

    # Step 8: write outputs
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV)
    save_params(norm_params, NORM_PARAMS)

    print(f"[build] wrote {OUTPUT_CSV}")
    print(f"[build] wrote {NORM_PARAMS}")
    print("── done ──")


if __name__ == "__main__":
    build()

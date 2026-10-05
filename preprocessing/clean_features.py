"""Select the acoustic feature subset and handle missing values.

Selected features (44 dims total):
  Indices 0-4:  RMS mean, ZCR mean, Spectral Centroid mean,
                Spectral Bandwidth mean, Spectral Rolloff mean
  Index   5:    MFCC mean 01  ← AcousticKey(6,10) uses indices 0-5
  Indices 6-24: MFCC mean 02-20
  Indices 25-36: Chroma CQT mean 01-12
  Indices 37-43: Spectral Contrast mean 01-07
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# (feature_group, statistic, expected_number_of_columns)
# Ordering is intentional: indices 0-5 are the six AcousticKey dimensions
# consumed by AcousticKey(6, 10).encode(features) in the C++ core.
SELECTED_FEATURES: list[tuple[str, str, int]] = [
    ("rmse", "mean", 1),               # index 0  — RMS energy
    ("zcr", "mean", 1),                # index 1  — Zero-crossing rate
    ("spectral_centroid", "mean", 1),  # index 2  — Spectral centroid
    ("spectral_bandwidth", "mean", 1), # index 3  — Spectral bandwidth
    ("spectral_rolloff", "mean", 1),   # index 4  — Spectral rolloff
    ("mfcc", "mean", 20),              # index 5-24 (MFCC-1 = index 5)
    ("chroma_cqt", "mean", 12),        # index 25-36
    ("spectral_contrast", "mean", 7),  # index 37-43
]

# Librosa ≥ 0.9 renamed 'rmse' → 'rms'. Both FMA dataset variants are handled.
_ALIASES: dict[str, str] = {"rmse": "rms", "rms": "rmse"}


def select_features(features: pd.DataFrame) -> pd.DataFrame:
    """Keep only the columns listed in ``SELECTED_FEATURES``.

    Returns a DataFrame with flat column names (``mfcc_mean_01``, ``rmse_mean``,
    etc.) where the column order mirrors SELECTED_FEATURES, ensuring that
    ``features[0:6]`` are the six AcousticKey dimensions.
    """
    available = set(features.columns.get_level_values(0))
    parts: list[pd.DataFrame] = []

    for group, stat, expected_n in SELECTED_FEATURES:
        resolved = _resolve_group(group, available)
        sub = features[resolved][stat].copy()

        if sub.shape[1] != expected_n:
            raise ValueError(
                f"Expected {expected_n} columns for ({group}, {stat}), "
                f"got {sub.shape[1]}: {list(sub.columns)}"
            )

        # Canonical flat names: "rmse_mean" (single), "mfcc_mean_01" (multi).
        # The canonical group name from SELECTED_FEATURES is always used so the
        # output CSV is consistent even if the FMA file used 'rms' vs 'rmse'.
        if expected_n == 1:
            sub.columns = [f"{group}_{stat}"]
        else:
            indices = [int(c) for c in sub.columns]
            if sorted(indices) != list(range(1, expected_n + 1)):
                raise ValueError(f"Invalid coefficient indices for {group}: {indices}")
            sub.columns = indices
            sub = sub.reindex(columns=range(1, expected_n + 1))
            sub.columns = [f"{group}_{stat}_{c:02d}" for c in sub.columns]

        parts.append(sub)

    result = pd.concat(parts, axis=1)
    print(f"[select_features] {result.shape[1]} feature columns selected")
    return result


def handle_missing(features: pd.DataFrame, col_threshold: float = 0.5) -> pd.DataFrame:
    """Drop invalid rows while preserving the fixed 44-feature C++ contract.

    A mostly missing column is an input error; dropping it would silently shift
    AcousticKey dimensions. Non-numeric values and infinities count as missing.
    """
    if features.empty or features.shape[1] != 44:
        raise ValueError("Expected a non-empty matrix with exactly 44 features")
    features = features.apply(pd.to_numeric, errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    col_missing = features.isnull().mean()
    bad_cols = col_missing[col_missing > col_threshold].index.tolist()
    if bad_cols:
        raise ValueError(f"Features with >{col_threshold:.0%} invalid values: {bad_cols}")

    n_before = len(features)
    features = features.dropna()
    if features.empty:
        raise ValueError("No tracks with 44 valid features remain")
    n_dropped = n_before - len(features)
    if n_dropped:
        print(f"[handle_missing] dropped {n_dropped} track(s) with any NaN "
              f"({n_dropped / n_before:.1%} of total)")

    print(f"[handle_missing] {len(features):,} tracks × {features.shape[1]} columns remain")
    return features


def _resolve_group(name: str, available: set[str]) -> str:
    """Return the actual group name in the DataFrame, handling rmse/rms aliases."""
    if name in available:
        return name
    alt = _ALIASES.get(name)
    if alt and alt in available:
        return alt
    raise KeyError(
        f"Feature group '{name}' not found. "
        f"Available groups: {sorted(available)}"
    )

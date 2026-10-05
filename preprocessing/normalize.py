"""Normalize acoustic features to a common scale.

Acoustic descriptors live on very different scales, so they must be normalized
before computing Euclidean distances or encoding with AcousticKey.

Both functions return a (normalized_df, params) tuple. The params dict should
be saved alongside the processed CSV so that new query vectors can be scaled
with the same statistics (no data leakage between index and query).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def min_max(features: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Min-Max scale each column to [0, 1]: (x − min) / (max − min).

    Constant columns (max == min) are left at 0.0 — they carry no information
    and would produce NaN or inf without the guard.

    This is the default normalization for the pipeline because AcousticKey
    requires features in [0, 1].
    """
    col_min = features.min()
    col_max = features.max()
    col_range = (col_max - col_min).replace(0.0, 1.0)  # constant col → stays 0

    normalized = (features - col_min) / col_range

    params: dict = {
        "method": "min_max",
        "columns": list(features.columns),
        "min": col_min.tolist(),
        "max": col_max.tolist(),
    }
    print(f"[min_max] {features.shape[1]} columns normalized to [0, 1]")
    return normalized, params


def z_score(features: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Standardize each column to zero mean / unit variance.

    Constant columns (std == 0) are left at 0.0.
    Alternative to min_max; provided for visualization and ML experiments but
    not used in the default pipeline (AcousticKey requires [0, 1] inputs).
    """
    mean = features.mean()
    std = features.std().replace(0.0, 1.0)  # constant col → stays 0

    normalized = (features - mean) / std

    params: dict = {
        "method": "z_score",
        "columns": list(features.columns),
        "mean": mean.tolist(),
        "std": std.tolist(),
    }
    print(f"[z_score] {features.shape[1]} columns standardized (μ=0, σ=1)")
    return normalized, params


def save_params(params: dict, path: Path) -> None:
    """Persist normalization statistics for consistent query scaling."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=2)


def load_params(path: Path) -> dict:
    """Load previously saved normalization statistics."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

"""Translate distribution-aware UI controls into exact acoustic intervals.

Percentiles affect only filter controls. The feature vectors, Acoustic Key and
Euclidean ranking retain the dataset's original min-max normalized values.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = {
    "rmse_mean": "rms",
    "spectral_centroid_mean": "spectral_centroid",
    "zcr_mean": "zcr",
    "spectral_bandwidth_mean": "bandwidth",
    "spectral_rolloff_mean": "rolloff",
}
FEATURE_LABELS = {
    "rms": "RMS (energia)",
    "spectral_centroid": "Centroide espectral",
    "zcr": "ZCR (taxa de cruzamento)",
    "bandwidth": "Largura de banda",
    "rolloff": "Roll-off espectral",
}


def percentile_bounds(values: pd.Series, interval: tuple[int, int]) -> tuple[float, float]:
    """Map catalog percentiles to observed values, preserving ties and endpoints.

    Nearest interpolation means a zero-width percentile interval still refers
    to an observed value instead of an interpolated value matching no track.
    """
    low, high = interval
    if not (0 <= low <= high <= 100):
        raise ValueError("Percentiles must satisfy 0 <= lower <= upper <= 100")
    finite = values.loc[np.isfinite(values)]
    if finite.empty:
        raise ValueError("No finite feature values available")
    bounds = finite.quantile([low / 100.0, high / 100.0], interpolation="nearest")
    return float(bounds.iloc[0]), float(bounds.iloc[1])


def matching_ids(features: pd.DataFrame, bounds: dict[str, tuple[float, float]]) -> pd.Index:
    """Select IDs satisfying every inclusive interval; missing values never pass."""
    mask = pd.Series(True, index=features.index)
    for name, (low, high) in bounds.items():
        if not (np.isfinite(low) and np.isfinite(high) and low <= high):
            raise ValueError("Filter bounds must be finite and ordered")
        values = features[name]
        mask &= np.isfinite(values) & values.between(low, high, inclusive="both")
    return features.index[mask]

"""Normalize acoustic features to a common scale (plan §8).

Acoustic descriptors live on very different scales, so they must be normalized
before computing Euclidean distances or building the Acoustic Key.
"""

from __future__ import annotations

import pandas as pd


def min_max(features: pd.DataFrame) -> pd.DataFrame:
    """Min-Max scale each column to [0, 1]: (x - min) / (max - min).

    TODO: implement and guard against zero-range (constant) columns.
    """
    raise NotImplementedError("min_max: implement min-max normalization")


def z_score(features: pd.DataFrame) -> pd.DataFrame:
    """Standardize each column to zero mean / unit variance.

    TODO: implement as an alternative to min_max (plan §8).
    """
    raise NotImplementedError("z_score: implement z-score standardization")

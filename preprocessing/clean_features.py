"""Select the acoustic feature subset and handle missing values (plan §7, §8).

Selected features (~44 dims):
  MFCC mean (20), Chroma CQT mean (12), Spectral Contrast mean (7),
  RMS mean (1), ZCR mean (1), Spectral Centroid mean (1),
  Spectral Bandwidth mean (1), Spectral Rolloff mean (1).
"""

from __future__ import annotations

import pandas as pd

# (feature_group, statistic, expected_number_of_columns)
SELECTED_FEATURES = [
    ("mfcc", "mean", 20),
    ("chroma_cqt", "mean", 12),
    ("spectral_contrast", "mean", 7),
    ("rmse", "mean", 1),
    ("zcr", "mean", 1),
    ("spectral_centroid", "mean", 1),
    ("spectral_bandwidth", "mean", 1),
    ("spectral_rolloff", "mean", 1),
]


def select_features(features: pd.DataFrame) -> pd.DataFrame:
    """Keep only the columns listed in ``SELECTED_FEATURES``.

    TODO: slice the FMA feature multi-index down to the selected groups/stats.
    """
    raise NotImplementedError("select_features: implement column selection")


def handle_missing(features: pd.DataFrame) -> pd.DataFrame:
    """Drop or impute rows/columns with missing values (plan §8).

    TODO: decide on drop vs impute and document the choice for the report.
    """
    raise NotImplementedError("handle_missing: implement missing-value policy")

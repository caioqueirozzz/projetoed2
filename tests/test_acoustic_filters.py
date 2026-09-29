"""Regression tests for acoustic filters on unevenly distributed features."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from services.acoustic_filters import matching_ids, percentile_bounds


class AcousticFilterTests(unittest.TestCase):
    def test_percentiles_remain_useful_when_one_extreme_compresses_the_catalog(self):
        values = pd.Series([i / 1000 for i in range(100)] + [1.0])
        frame = pd.DataFrame({"energy": values})

        # A linear lower limit of 0.10 would keep just the extreme track.
        self.assertEqual(len(matching_ids(frame, {"energy": (0.10, 1.0)})), 1)

        bounds = percentile_bounds(values, (10, 90))
        selected = matching_ids(frame, {"energy": bounds})
        self.assertGreaterEqual(len(selected), 79)
        self.assertLessEqual(len(selected), 83)
        self.assertLess(bounds[1], 0.10)
        self.assertNotIn(100, selected)

    def test_full_percentile_interval_preserves_minimum_and_maximum(self):
        values = pd.Series([0.0, 0.03, 0.2, 1.0], index=[9, 2, 7, 4])
        bounds = percentile_bounds(values, (0, 100))
        self.assertEqual(bounds, (0.0, 1.0))
        selected = matching_ids(values.to_frame("energy"), {"energy": bounds})
        self.assertEqual(selected.tolist(), values.index.tolist())
        self.assertEqual(percentile_bounds(values, (0, 0)), (0.0, 0.0))
        self.assertEqual(percentile_bounds(values, (100, 100)), (1.0, 1.0))

    def test_ties_at_percentile_boundaries_are_kept_together(self):
        values = pd.Series([0.0] * 40 + [0.1] * 40 + [1.0] * 20)
        bounds = percentile_bounds(values, (50, 60))
        self.assertEqual(bounds, (0.1, 0.1))
        selected = matching_ids(values.to_frame("energy"), {"energy": bounds})
        self.assertEqual(selected.tolist(), list(range(40, 80)))

    def test_constant_feature_does_not_discard_tracks(self):
        values = pd.Series([0.25] * 12)
        for interval in [(0, 100), (20, 80), (50, 50)]:
            with self.subTest(interval=interval):
                bounds = percentile_bounds(values, interval)
                self.assertEqual(bounds, (0.25, 0.25))
                selected = matching_ids(values.to_frame("energy"), {"energy": bounds})
                self.assertEqual(len(selected), len(values))

    def test_matching_uses_inclusive_limits_and_intersection(self):
        features = pd.DataFrame(
            {"energy": [0.1, 0.2, 0.3, 0.2], "brightness": [0.4, 0.5, 0.5, 0.7]},
            index=pd.Index([40, 10, 30, 20], name="track_id"),
        )
        selected = matching_ids(features, {"energy": (0.1, 0.2), "brightness": (0.4, 0.5)})
        self.assertEqual(selected.tolist(), [40, 10])
        self.assertEqual(selected.name, "track_id")

    def test_nonfinite_values_are_ignored_for_percentiles_and_rejected_by_filters(self):
        values = pd.Series([np.nan, np.inf, -np.inf, 0.1, 0.2, 1.0])
        bounds = percentile_bounds(values, (0, 100))
        self.assertEqual(bounds, (0.1, 1.0))
        selected = matching_ids(values.to_frame("energy"), {"energy": bounds})
        self.assertEqual(selected.tolist(), [3, 4, 5])

    def test_only_filtered_attributes_determine_missing_value_rejection(self):
        features = pd.DataFrame(
            {"energy": [0.1, 0.2, 0.3], "brightness": [np.nan, 0.5, np.inf]},
            index=[10, 20, 30],
        )
        self.assertEqual(matching_ids(features, {"energy": (0.0, 1.0)}).tolist(), [10, 20, 30])
        self.assertEqual(matching_ids(features, {"energy": (0.0, 1.0), "brightness": (0.0, 1.0)}).tolist(), [20])
        self.assertEqual(matching_ids(features, {}).tolist(), [10, 20, 30])

    def test_percentiles_reject_empty_or_nonfinite_only_series(self):
        for values in [pd.Series(dtype=float), pd.Series([np.nan, np.inf, -np.inf])]:
            with self.subTest(values=values.tolist()):
                with self.assertRaises(ValueError):
                    percentile_bounds(values, (0, 100))

    def test_percentiles_reject_invalid_intervals(self):
        values = pd.Series([0.0, 0.5, 1.0])
        for interval in [(-1, 100), (0, 101), (80, 20), (np.nan, 100), (0, np.inf)]:
            with self.subTest(interval=interval):
                with self.assertRaises(ValueError):
                    percentile_bounds(values, interval)

    def test_matching_rejects_reversed_and_nonfinite_bounds(self):
        features = pd.DataFrame({"energy": [0.1, 0.2]})
        for bounds in [(0.3, 0.1), (np.nan, 1.0), (0.0, np.nan), (-np.inf, 1.0), (0.0, np.inf)]:
            with self.subTest(bounds=bounds):
                with self.assertRaises(ValueError):
                    matching_ids(features, {"energy": bounds})


if __name__ == "__main__":
    unittest.main()

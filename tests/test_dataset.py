"""FMA import regressions and the Python → CSV → C++ integration contract."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "preprocessing"))
sys.path.insert(0, str(ROOT / "app"))
from build_dataset import build
from clean_features import handle_missing, select_features
from import_fma import import_zip
from load_fma import load_features, load_tracks
from services.core_bridge import CoreBridge
from services.dataset import audio_path
from fma_fixture import make_fma

CORE = Path(os.environ.get("AME_CORE_BINARY", ROOT / "build" / "ame_core_app"))


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fma test with spaces ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "raw"
        self.metadata, self.audio = make_fma(self.source)
        self.output = self.root / "processed data"
        self.log = contextlib.redirect_stdout(io.StringIO())
        self.log.__enter__()
        self.addCleanup(self.log.__exit__, None, None, None)

    def prepare(self, **kwargs):
        return build(self.source, self.output, **kwargs)

    def test_medium_includes_small_and_preserves_schema(self):
        report = self.prepare(require_audio=True)
        data = pd.read_csv(self.output / "tracks_processed.csv", index_col="track_id")
        self.assertEqual(list(data.index), [2, 3, 4])
        self.assertEqual(data.columns[4:10].tolist(), ["rmse_mean", "zcr_mean", "spectral_centroid_mean",
                         "spectral_bandwidth_mean", "spectral_rolloff_mean", "mfcc_mean_01"])
        self.assertEqual(data.shape[1], 48)
        self.assertTrue(np.isfinite(data.iloc[:, 4:].to_numpy()).all())
        self.assertTrue(((data.iloc[:, 4:] >= 0) & (data.iloc[:, 4:] <= 1)).all().all())
        self.assertEqual(report["missing_feature_ids"], [7])
        self.assertEqual(report["invalid_feature_ids"], [6])
        self.assertEqual(report["audio_available"], 3)
        self.assertEqual(data.loc[2, "title"], 'Canção, "A"\nsegunda linha')
        self.assertEqual(audio_path(2, data), self.audio / "000" / "000002.mp3")
        self.assertTrue((self.output / "genres.csv").is_file())
        params = json.loads((self.output / "normalization_params.json").read_text())
        self.assertEqual(len(params["columns"]), 44)

    def test_import_zip_supports_nested_kaggle_and_ignores_small(self):
        archive = self.root / "kaggle.zip"
        with ZipFile(archive, "w") as zip_file:
            for path in self.source.rglob("*"):
                if path.is_file():
                    zip_file.write(path, path.relative_to(self.source))
            zip_file.writestr("fma_small/000/000002.mp3", b"small")
            zip_file.writestr("../../outside.csv", b"invalid")
        destination = self.root / "imported"
        self.assertEqual(import_zip(archive, destination), 8)
        self.assertEqual(import_zip(archive, destination), 8)  # safe rerun
        self.assertFalse((destination / "fma_small").exists())
        self.assertEqual(build(destination, self.output, require_audio=True)["processed_tracks"], 3)

    def test_incomplete_zip_reports_actionable_error(self):
        archive = self.root / "incomplete.zip"
        archive.write_bytes(b"PK\x03\x04incomplete download")
        result = subprocess.run([sys.executable, str(ROOT / "preprocessing" / "build_dataset.py"),
                                 "--import-zip", str(archive), "--source", str(self.root / "imported")],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Wait for the download to finish", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_audio_reports_and_strict_failure_preserves_csv(self):
        self.prepare()
        csv = self.output / "tracks_processed.csv"
        before = csv.read_bytes()
        (self.audio / "000" / "000002.mp3").unlink()
        with self.assertRaisesRegex(ValueError, "Audio missing"):
            self.prepare(require_audio=True)
        self.assertEqual(csv.read_bytes(), before)
        report = self.prepare()
        self.assertEqual(report["missing_audio_ids"], [2])

    def test_missing_feature_column_fails_instead_of_shifting_dimensions(self):
        features = select_features(load_features(self.metadata))
        features["zcr_mean"] = np.nan
        with self.assertRaisesRegex(ValueError, "invalid values"):
            handle_missing(features)
        with self.assertRaisesRegex(ValueError, "44 features"):
            handle_missing(features.drop(columns="zcr_mean"))

    def test_feature_coefficients_are_sorted_numerically(self):
        raw = load_features(self.metadata)
        selected = select_features(raw)
        self.assertEqual(selected.loc[2, "mfcc_mean_01"], raw.loc[2, ("mfcc", "mean", "01")])
        self.assertLess(list(selected.columns).index("mfcc_mean_02"), list(selected.columns).index("mfcc_mean_10"))

    def test_duplicate_metadata_ids_are_rejected(self):
        path = self.metadata / "tracks.csv"
        tracks = pd.read_csv(path, index_col=0, header=[0, 1])
        pd.concat([tracks, tracks.iloc[:1]]).to_csv(path)
        with self.assertRaisesRegex(ValueError, "unique"):
            load_tracks(self.metadata)

    @unittest.skipUnless(CORE.is_file(), "Build ame_core_app first for bridge integration")
    def test_bridge_load_search_laboratory_and_reject_bad_csv(self):
        self.prepare()
        csv = self.output / "tracks_processed.csv"
        bridge = CoreBridge(CORE, csv)
        self.addCleanup(bridge.close)
        self.assertTrue(bridge.is_loaded)
        self.assertEqual(bridge.track_count, 3)
        for query in [2, 3, 4]:
            results, metrics = bridge.find_similar(query, 500, 10)
            self.assertEqual({r.track_id for r in results}, {2, 3, 4} - {query})
            self.assertEqual(metrics.candidates, 2)
            self.assertGreater(metrics.skiplist_comparisons, 0)
            self.assertEqual([r.distance for r in results], sorted(r.distance for r in results))
        self.assertEqual(bridge.lab_splay('access', 2)['root_id'], 2)
        self.assertEqual(bridge.lab_splay('access', 3)['root_id'], 3)
        self.assertEqual(bridge.lab_splay('access', 2)['depth_after'], 0)
        with self.assertRaises(RuntimeError):
            bridge.find_similar(2, -1, 10)
        with self.assertRaises(RuntimeError):
            bridge.find_similar(999, 500, 10)
        data = pd.read_csv(csv)
        for value in [float("nan"), float("inf"), -0.2, 1.1]:
            bad = data.copy()
            bad.loc[0, "rmse_mean"] = value
            path = self.output / "bad input.csv"
            bad.to_csv(path, index=False)
            self.assertEqual(bridge._cmd(f"load {path}")["status"], "error")
            self.assertEqual(len(bridge.find_similar(2, 10, 10)[0]), 2)
        duplicate = pd.concat([data, data.iloc[:1]])
        duplicate.to_csv(self.output / "bad input.csv", index=False)
        self.assertEqual(bridge._cmd(f"load {self.output / 'bad input.csv'}")["status"], "error")
        data.drop(columns="mfcc_mean_01").to_csv(self.output / "bad input.csv", index=False)
        self.assertEqual(bridge._cmd(f"load {self.output / 'bad input.csv'}")["status"], "error")
        # Named columns tolerate reordering; loading the catalogue preserves the independent lab.
        data[data.columns[::-1]].to_csv(self.output / "reordered.csv", index=False)
        self.assertEqual(bridge._cmd(f"load {self.output / 'reordered.csv'}")["loaded"], 3)
        self.assertEqual(bridge.lab_splay()['size'], 2)
        self.assertEqual(len(bridge.find_similar(2, 10, 10)[0]), 2)

    @unittest.skipUnless((CORE.parent / "benchmark_similarity").is_file(), "Build benchmark first")
    def test_real_csv_benchmark_excludes_self(self):
        self.prepare()
        out = self.output / "recall.csv"
        subprocess.run([str(CORE.parent / "benchmark_similarity"),
                        str(self.output / "tracks_processed.csv"), str(out)],
                       check=True, capture_output=True, text=True, timeout=30)
        result = pd.read_csv(out)
        self.assertEqual(result.loc[0, "recall_at_10"], 1.0)
        self.assertEqual(result.loc[0, "dataset_size"], 3)
        self.assertEqual(result.loc[0, "top_k"], 2)
        self.assertEqual(result.loc[0, "dataset_source"], "processed_csv")


if __name__ == "__main__":
    unittest.main()

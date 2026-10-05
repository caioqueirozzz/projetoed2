"""Ensure comparative experiments perform equivalent observable work."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
BIN = Path(os.environ.get('AME_CORE_BINARY', ROOT / 'build/ame_core_app')).parent

@unittest.skipUnless((BIN / 'benchmark_skiplist').is_file(), 'Build benchmarks first')
class BenchmarkTests(unittest.TestCase):
    def test_comparisons_checksums_and_missing_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            for executable in ['benchmark_skiplist', 'benchmark_splay']:
                subprocess.run([str(BIN / executable), temporary, '2'], cwd=temporary, capture_output=True, check=True, timeout=90)
            root = Path(temporary)
            data = pd.read_csv(root / 'benchmark_skiplist.csv')
            self.assertEqual(set(data.operation), {'insert', 'search', 'remove', 'nearest', 'update'})
            self.assertTrue(data.groupby(['n', 'repeat', 'operation']).checksum.nunique().eq(1).all())
            self.assertTrue(data.comparisons.gt(0).all())
            self.assertTrue(data.memory_bytes_estimate.gt(0).all())
            self.assertEqual(set(data.seed), {42, 43})
            for scenario in ['uniform', 'locality']:
                data = pd.read_csv(root / f'benchmark_splay_{scenario}.csv')
                self.assertEqual(set(data.structure), {'SplayTree', 'BST', 'StdMap'})
                self.assertTrue(data.groupby(['n', 'repeat']).checksum.nunique().eq(1).all())
                self.assertTrue(data.avg_comparisons.gt(0).all())
                self.assertTrue(data.loc[data.structure == 'StdMap', ['avg_depth', 'hot_avg_depth', 'total_rotations']].isna().all().all())
            progress = pd.read_csv(root / 'benchmark_splay_progress.csv')
            for _, rows in progress.groupby(['scenario', 'structure', 'n', 'repeat']):
                self.assertEqual(rows.accesses.iloc[-1], 10000)
                self.assertTrue(rows.cumulative_comparisons.diff().dropna().ge(0).all())

if __name__ == '__main__': unittest.main()

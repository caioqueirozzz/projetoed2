"""Run all experiments from any directory and publish their provenance together."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=Path(os.environ.get('AME_DATASET_CSV', ROOT / 'data/processed/tracks_processed.csv')))
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmark/results')
    parser.add_argument('--build', type=Path, default=ROOT / 'build')
    parser.add_argument('--repeats', type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 2:
        parser.error('Use at least two repetitions to report dispersion.')
    dataset, output, build = args.dataset.resolve(), args.output.resolve(), args.build.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.bench-', dir=output) as temporary:
        staging = Path(temporary)
        commands = [[str(build / 'benchmark_skiplist'), str(staging), str(args.repeats)],
                    [str(build / 'benchmark_splay'), str(staging), str(args.repeats)],
                    [str(build / 'benchmark_similarity'), str(dataset), str(staging / 'benchmark_recall.csv'), str(args.repeats)]]
        for command in commands:
            subprocess.run(command, cwd=ROOT, check=True, timeout=150)
        sources = sorted([*ROOT.glob('core/**/*.cpp'), *ROOT.glob('core/**/*.hpp'), *ROOT.glob('benchmark/*.cpp'), *ROOT.glob('benchmark/*.hpp')])
        manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
                    'processor': platform.processor(), 'python': platform.python_version(),
                    'dataset': str(dataset), 'dataset_sha256': sha256(dataset),
                    'repeats': args.repeats, 'seeds': list(range(42, 42+args.repeats)),
                    'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in sources},
                    'binary_sha256': {Path(c[0]).name: sha256(Path(c[0])) for c in commands},
                    'result_sha256': {p.name: sha256(p) for p in staging.glob('*.csv')},
                    'memory_note': 'Estimated container/node storage; excludes allocator overhead and transient buffers. std::map assumes four pointer-width slots for links/color/padding.',
                    'timing_note': 'steady_clock; setup and result-file writes excluded; operation counters and trace instrumentation included. No guarantee of speedup.'}
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        for path in sorted(staging.glob('*.csv')):
            path.replace(output / path.name)
        (staging / 'manifest.json').replace(output / 'manifest.json')
    print(f'Results and provenance: {output}')
if __name__ == '__main__':
    main()

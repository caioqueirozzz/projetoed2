"""Identify stale experimental results before presenting them as current."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pandas as pd
import streamlit as st

# Only columns needed to render each table/plot are mandatory. Other metrics,
# including unobservable std::map internals, may legitimately contain NaN.
_RESULT_COLUMNS = {
    'benchmark_recall.csv': ({'mode'}, {'num_candidates', 'recall_at_10', 'avg_query_ms', 'brute_force_ms', 'avg_evaluated'}),
    'benchmark_skiplist.csv': ({'structure', 'operation'}, {'n', 'time_ms'}),
    'benchmark_splay_uniform.csv': ({'structure'}, {'n', 'time_ms'}),
    'benchmark_splay_locality.csv': ({'structure'}, {'n', 'time_ms'}),
    'benchmark_splay_progress.csv': ({'structure', 'scenario'}, {'n', 'accesses', 'cumulative_comparisons'}),
}

def read_benchmark(path: Path) -> pd.DataFrame:
    """Reject incomplete/invalid result files before they reach plotting code."""
    try:
        data = pd.read_csv(path)
        labels, numeric = _RESULT_COLUMNS[path.name]
        missing = (labels | numeric) - set(data.columns)
        if missing:
            raise ValueError('colunas ausentes: ' + ', '.join(sorted(missing)))
        if data.empty or data[list(labels)].isna().any().any():
            raise ValueError('resultados vazios ou sem identificação')
        for column in numeric:
            data[column] = pd.to_numeric(data[column], errors='raise')
            if data[column].isin([float('inf'), float('-inf')]).any() or data[column].isna().any():
                raise ValueError(f'valores inválidos em {column}')
        return data
    except (OSError, ValueError, KeyError) as exc:
        raise ValueError(f'{path.name}: resultados indisponíveis ({exc}). Execute novamente os benchmarks.') from exc

@st.cache_data(show_spinner=False)
def _fingerprint(path: str, signature: tuple[int, int]) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

def fingerprint(path: Path) -> str:
    stat = path.stat()
    return _fingerprint(str(path.resolve()), (stat.st_mtime_ns, stat.st_size))

def provenance_warnings(root: Path, dataset: Path) -> list[str]:
    path = root / 'benchmark/results/manifest.json'
    if not path.is_file():
        return ['Os resultados não possuem identificação da base e do código. Execute novamente os benchmarks.']
    try:
        manifest = json.loads(path.read_text())
        messages = []
        if not dataset.is_file() or fingerprint(dataset) != manifest.get('dataset_sha256'):
            messages.append('A base atual difere da base usada nestes resultados.')
        for relative, expected in manifest.get('source_sha256', {}).items():
            source = root / relative
            if not source.is_file() or fingerprint(source) != expected:
                messages.append('O código mudou desde a última execução dos benchmarks.')
                break
        for name, expected in manifest.get('result_sha256', {}).items():
            result = path.parent / name
            if not result.is_file() or fingerprint(result) != expected:
                messages.append('Um arquivo de resultados foi alterado ou está ausente.')
                break
        return messages
    except (OSError, ValueError, TypeError, AttributeError):
        return ['Não foi possível validar a identificação dos resultados. Execute novamente os benchmarks.']

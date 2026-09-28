"""Página 2 — Exploração Acústica (plan §25).

Busca candidatos via Skip List e aplica filtros por faixa de feature acústica
(RMS, Centroide Espectral, ZCR, Largura de Banda, Roll-off) no lado Python.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.core_bridge import get_bridge
from services.dataset import format_label, get_track, load_catalog

_REPO_ROOT    = Path(__file__).resolve().parent.parent.parent
_FEATURES_CSV = _REPO_ROOT / "data" / "processed" / "tracks_processed.csv"
_FEATURE_NAMES = ["rms", "spectral_centroid", "zcr", "bandwidth", "rolloff"]
_FEATURE_LABELS = {
    "rms":              "RMS (energia)",
    "spectral_centroid":"Centroide Espectral",
    "zcr":              "ZCR (taxa de cruzamento)",
    "bandwidth":        "Largura de Banda",
    "rolloff":          "Roll-off Espectral",
}


@st.cache_data
def load_features() -> pd.DataFrame | None:
    if not _FEATURES_CSV.exists():
        return None
    df = pd.read_csv(_FEATURES_CSV, header=0)
    feat_cols = df.columns[5:10].tolist()
    result = df[["track_id"] + feat_cols].copy()
    result.columns = ["track_id"] + _FEATURE_NAMES
    return result.set_index("track_id")


st.set_page_config(page_title="Acoustic Explorer — AME", layout="wide")
st.title("Acoustic Explorer")
st.markdown(
    "Combine a busca por vizinhança da **Skip List** com filtros exatos por "
    "atributo acústico para explorar regiões do espaço sonoro (plan §25)."
)

# ── bridge ────────────────────────────────────────────────────────────────────

bridge = get_bridge()

if bridge is None:
    err = st.session_state.get("bridge_error", "Motivo desconhecido.")
    st.error(f"**Núcleo C++ indisponível.** {err}")
    st.code(
        "# No diretório raiz do projeto:\n"
        "cmake -S . -B build && cmake --build build",
        language="bash",
    )
    st.stop()

if not bridge.is_loaded:
    st.warning(
        "Dataset não carregado — busca indisponível. "
        "Execute `python preprocessing/build_dataset.py`.",
        icon="⚠",
    )
    st.stop()

# ── track selector ────────────────────────────────────────────────────────────

catalog = load_catalog()

if catalog.empty:
    st.info("Modo demo — dataset não encontrado. Digite qualquer ID de faixa.")
    track_id = int(st.number_input("ID da faixa", min_value=1, value=2, step=1))
    track_label = f"Track {track_id}"
else:
    options: list[tuple[str, int]] = [
        (format_label(tid, catalog), tid)
        for tid in catalog.index[:500]
    ]
    labels = [lbl for lbl, _ in options]
    chosen = st.selectbox("Selecione uma faixa de referência", labels, key="ae_track_sel")
    track_id = next(tid for lbl, tid in options if lbl == chosen)
    track_label = chosen

# ── search parameters ─────────────────────────────────────────────────────────

with st.expander("Parâmetros de busca", expanded=True):
    num_candidates = st.slider(
        "Candidatos da Skip List", min_value=100, max_value=2000,
        value=500, step=100,
        help="Número de candidatos recuperados pela Skip List antes da filtragem.",
    )

# ── acoustic filters ──────────────────────────────────────────────────────────

features_df = load_features()
filters: dict[str, tuple[float, float]] = {}

st.subheader("Filtros acústicos")

if features_df is None:
    st.info(
        "CSV de features não encontrado — filtros desabilitados. "
        "Os resultados exibidos são os retornados diretamente pela Skip List."
    )
else:
    cols = st.columns(len(_FEATURE_NAMES))
    for col, fname in zip(cols, _FEATURE_NAMES):
        with col:
            filters[fname] = st.slider(
                _FEATURE_LABELS[fname],
                min_value=0.0, max_value=1.0,
                value=(0.0, 1.0), step=0.05,
                key=f"filter_{fname}",
            )

# ── search button ─────────────────────────────────────────────────────────────

do_search = st.button("Buscar e filtrar", type="primary")

if do_search:
    try:
        with st.spinner("Buscando..."):
            results, metrics = bridge.find_similar(track_id, num_candidates, top_k=50)

        filtered_ids = [r.track_id for r in results]
        n_from_sl = len(filtered_ids)

        if features_df is not None and filters:
            def passes(tid: int) -> bool:
                if tid not in features_df.index:
                    return True
                row = features_df.loc[tid]
                return all(
                    filters[f][0] <= float(row[f]) <= filters[f][1]
                    for f in _FEATURE_NAMES
                )
            filtered = [r for r in results if passes(r.track_id)]
        else:
            filtered = results

        st.session_state.ae_results       = filtered
        st.session_state.ae_n_from_sl     = n_from_sl
        st.session_state.ae_n_after_filter= len(filtered)
        st.session_state.ae_metrics       = metrics
        st.session_state.ae_query_label   = track_label

    except Exception as exc:
        st.error(f"Erro na busca: {exc}")

st.divider()

# ── results ───────────────────────────────────────────────────────────────────

if "ae_results" in st.session_state:
    ae_results      = st.session_state.ae_results
    n_sl            = st.session_state.ae_n_from_sl
    n_filt          = st.session_state.ae_n_after_filter
    ae_metrics      = st.session_state.ae_metrics
    ae_query_label  = st.session_state.ae_query_label

    st.subheader(f"Resultados para: {ae_query_label}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Candidatos SL",       n_sl)
    m2.metric("Após filtros",        n_filt)
    m3.metric("Comparações SL",      ae_metrics.skiplist_comparisons)
    m4.metric("Tempo busca (ms)",    f"{ae_metrics.total_ms:.2f}")

    if ae_results:
        rows = []
        for i, r in enumerate(ae_results[:20], start=1):
            info = get_track(r.track_id, catalog)
            rows.append({
                "Posição":   i,
                "Título":    info["title"],
                "Artista":   info["artist"],
                "Gênero":    info["genre"],
                "Distância": round(r.distance, 6),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma faixa passou pelos filtros acústicos definidos.")

# ── explanation ───────────────────────────────────────────────────────────────

with st.expander("Como funciona (plan §25)", expanded=False):
    st.markdown(
        """
**Busca ANN + filtro exato**

1. A **Skip List** retorna os `N` candidatos mais próximos em espaço de chave
   acústica — uma busca aproximada (ANN) eficiente em O(log n).
2. Python carrega os valores de 5 features (RMS, Centroide, ZCR, Largura de
   Banda, Roll-off) para esses candidatos e aplica o filtro por faixa exata.
3. O resultado final contém apenas faixas dentro dos intervalos definidos nos
   sliders, mantendo as mais próximas da faixa de referência.

**Vantagem:** o filtro exato é aplicado sobre um subconjunto pequeno (candidatos
da SL), não sobre todo o dataset, o que mantém a busca eficiente.
        """
    )

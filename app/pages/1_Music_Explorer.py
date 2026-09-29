"""Página 1 — Music Explorer (plan §23, §24).

Seleciona uma faixa, busca as mais semelhantes via Skip List + distância
Euclidiana, e exibe o Top-K com métricas da busca.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.music import track_selector, render_player
from services.core_bridge import SearchMetrics, SearchResult, get_bridge
from services.dataset import format_label, get_track, load_catalog

st.set_page_config(page_title="Music Explorer — AME", layout="wide")
st.title("Music Explorer")
st.markdown(
    "Selecione uma faixa e encontre as músicas acusticamente mais próximas "
    "usando a **Skip List** como índice de vizinhança (plan §23, §24)."
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
        "Dataset não carregado — busca por similaridade indisponível. "
        "Execute `python preprocessing/build_dataset.py` para gerar o CSV.",
        icon="⚠",
    )
    st.stop()

# ── track selector ────────────────────────────────────────────────────────────

catalog = load_catalog()

track_id, track_label = track_selector(catalog, "music_track", "Selecione uma faixa")

st.subheader(track_label)
render_player(track_id, catalog, bridge, "selected_track")
st.caption("Use o botão de registro para incluir o acesso no perfil da Splay Tree.")

# ── search controls ───────────────────────────────────────────────────────────

col_cand, col_k, col_btn = st.columns([3, 2, 2])

with col_cand:
    num_candidates = st.slider(
        "Candidatos da Skip List", min_value=100, max_value=2500,
        value=500, step=100,
        help="Janela de vizinhança no espaço de chaves acústicas.",
    )

with col_k:
    top_k = st.slider(
        "Top-K resultados", min_value=5, max_value=20, value=10,
    )

with col_btn:
    st.write("")
    st.write("")
    do_search = st.button(
        "Encontrar músicas semelhantes", type="primary", use_container_width=True
    )

if do_search:
    try:
        with st.spinner("Buscando..."):
            results, metrics = bridge.find_similar(track_id, num_candidates, top_k)
        st.session_state.search_results = results
        st.session_state.search_metrics = metrics
        st.session_state.search_query_id = track_id
        st.session_state.search_query_label = track_label
    except Exception as exc:
        st.error(f"Erro na busca: {exc}")

st.divider()

# ── results ───────────────────────────────────────────────────────────────────

if "search_results" in st.session_state:
    results: list[SearchResult] = st.session_state.search_results
    metrics: SearchMetrics = st.session_state.search_metrics
    query_label: str = st.session_state.search_query_label

    st.subheader(f"Resultados para: {query_label}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Faixas no índice",  metrics.total_tracks)
    m2.metric("Candidatos SL",     metrics.candidates)
    m3.metric("Comparações SL",    metrics.skiplist_comparisons)
    m4.metric("Tempo total (ms)",  f"{metrics.total_ms:.2f}")

    st.divider()

    rows = []
    for i, r in enumerate(results, start=1):
        info = get_track(r.track_id, catalog)
        rows.append({
            "Posição": i,
            "Título":  info["title"],
            "Artista": info["artist"],
            "Gênero":  info["genre"],
            "Distância": round(r.distance, 6),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    if results:
        result_ids = [r.track_id for r in results]
        listen_id = int(st.selectbox(
            "Ouvir uma recomendação", result_ids,
            format_func=lambda tid: format_label(tid, catalog), key="recommendation_track",
        ))
        render_player(listen_id, catalog, bridge, "recommended_track")
    else:
        st.info("Nenhuma outra faixa disponível para recomendar.")

# ── explanation ───────────────────────────────────────────────────────────────

with st.expander("Como funciona (plan §10–§14)", expanded=False):
    st.markdown(
        """
**Busca por vizinhança acústica**

1. Cada faixa recebe uma **Acoustic Key** — um inteiro de 64 bits calculado pelo
   código Morton (Z-order) sobre 6 dimensões acústicas quantizadas.
2. A **Skip List** armazena as faixas ordenadas por essa chave.
3. Para encontrar vizinhos, a SL percorre uma janela bilateral em torno da chave
   da música consultada, coletando `num_candidates` candidatos.
4. Os candidatos são re-ranqueados pela **distância Euclidiana** exata usando um
   max-heap limitado (`topK`), retornando os K mais próximos.

**Por que `candidatos > top_k`?**
A Acoustic Key aproxima a similaridade — duas faixas com chaves próximas tendem
a ser acusticamente semelhantes, mas não é garantido. Um conjunto maior de
candidatos aumenta a probabilidade de capturar os K vizinhos reais (Recall@K).
        """
    )

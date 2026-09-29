"""Página 4 — Laboratório de Estruturas (plan §28, §29, §30).

Demonstração interativa isolada das duas estruturas de dados:
  - Skip List: busca por similaridade com métricas e análise de níveis.
  - Splay Tree: acesso a faixas com visualização antes/depois do splay.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.music import track_selector as select_catalog_track
from services.core_bridge import AccessResult, get_bridge
from services.dataset import format_label, get_track, load_catalog

st.set_page_config(page_title="Structures Lab — AME", layout="wide")
st.title("Laboratório de Estruturas")
st.markdown(
    "Demonstração interativa das duas estruturas protagonistas do projeto: "
    "**Skip List** (índice acústico) e **Splay Tree** (perfil adaptativo)."
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

catalog = load_catalog()

def track_selector(key: str) -> tuple[int, str]:
    return select_catalog_track(catalog, key)


# ── tabs ──────────────────────────────────────────────────────────────────────

tab_skip, tab_splay = st.tabs(["Skip List", "Splay Tree"])

# ════════════════════════════════════════════════════════════════════════════
# Skip List tab
# ════════════════════════════════════════════════════════════════════════════

with tab_skip:
    st.subheader("Estado da Skip List")

    try:
        sl_state = bridge.get_skiplist_state()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faixas indexadas", sl_state.size)
        c2.metric("Comparações totais", sl_state.comparisons)
        c3.metric("Inserções",          sl_state.insertions)
        c4.metric("Buscas",             sl_state.searches)
    except Exception as exc:
        st.error(f"Erro ao ler estado: {exc}")
        sl_state = None

    st.divider()
    st.subheader("Busca por similaridade")

    if not bridge.is_loaded:
        st.info("Dataset não carregado — busca indisponível.")
    else:
        sl_track_id, sl_track_label = track_selector("sl_track_sel")

        col_cand, col_k = st.columns(2)
        with col_cand:
            sl_candidates = st.slider(
                "Candidatos", min_value=50, max_value=1000, value=200, step=50,
                key="sl_candidates",
            )
        with col_k:
            sl_topk = st.slider(
                "Top-K", min_value=5, max_value=20, value=10, key="sl_topk",
            )

        if st.button("Executar busca", type="primary", key="sl_search_btn"):
            try:
                comps_before = bridge.get_skiplist_state().comparisons
                with st.spinner("Buscando..."):
                    results, metrics = bridge.find_similar(
                        sl_track_id, sl_candidates, sl_topk
                    )
                comps_after = bridge.get_skiplist_state().comparisons
                st.session_state.sl_results        = results
                st.session_state.sl_metrics        = metrics
                st.session_state.sl_comps_delta    = comps_after - comps_before
                st.session_state.sl_query_label    = sl_track_label
            except Exception as exc:
                st.error(f"Erro: {exc}")

    if "sl_results" in st.session_state:
        sl_results = st.session_state.sl_results
        sl_metrics = st.session_state.sl_metrics

        st.markdown(f"**Consulta:** {st.session_state.sl_query_label}")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Candidatos retornados", sl_metrics.candidates)
        d2.metric("Comparações nesta busca", st.session_state.sl_comps_delta)
        d3.metric("Tempo SL (ms)",           f"{sl_metrics.skiplist_ms:.3f}")
        d4.metric("Tempo total (ms)",        f"{sl_metrics.total_ms:.3f}")

        rows = []
        for i, r in enumerate(sl_results[:5], start=1):
            info = get_track(r.track_id, catalog)
            rows.append({
                "Posição":   i,
                "Título":    info["title"],
                "Artista":   info["artist"],
                "Distância": round(r.distance, 6),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("Visualização de níveis e complexidade", expanded=False):
        if sl_state and sl_state.size > 0:
            expected_levels = max(1, int(math.log2(sl_state.size)))
            st.markdown(
                f"Com **N = {sl_state.size}** elementos e probabilidade p = 0,5, "
                f"a Skip List tem aproximadamente **log₂(N) ≈ {expected_levels} níveis** esperados.\n\n"
                "O nível 0 contém todas as faixas em ordem crescente de Acoustic Key. "
                "Cada nível superior contém ~metade dos nós do nível abaixo, "
                "formando uma estrutura de \"atalhos\" que reduz o número de "
                "comparações de O(N) para O(log N) por busca."
            )
        st.markdown(
            """
| Operação     | Complexidade esperada |
|--------------|-----------------------|
| insert       | O(log n)              |
| search       | O(log n)              |
| remove       | O(log n)              |
| nearest(k)   | O(log n + k)          |
| traverse     | O(n)                  |

A aleatoriedade nos níveis garante O(log n) com alta probabilidade, sem
necessidade de rebalanceamento explícito como em AVL ou Red-Black Trees.
            """
        )

# ════════════════════════════════════════════════════════════════════════════
# Splay Tree tab
# ════════════════════════════════════════════════════════════════════════════

with tab_splay:
    st.subheader("Estado da Splay Tree")

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        refresh = st.button("Atualizar estado", key="splay_refresh")

    try:
        splay_state = bridge.get_splay_state()
        s1, s2, s3 = st.columns(3)
        s1.metric("Raiz atual", splay_state.root_id if splay_state.root_id >= 0 else "—")
        s2.metric("Altura",     splay_state.height)
        s3.metric("Faixas no perfil", splay_state.size)
        st.code(splay_state.tree_ascii or "(árvore vazia)", language=None)
    except Exception as exc:
        st.error(f"Erro ao ler estado: {exc}")

    st.divider()
    st.subheader("Acessar faixa")

    sp_track_id, sp_track_label = track_selector("sp_track_sel")

    if st.button("Registrar acesso (inserir/acessar)", type="primary", key="sp_access_btn"):
        try:
            result: AccessResult = bridge.register_access(sp_track_id)
            st.session_state.sp_last_access       = result
            st.session_state.sp_last_access_label = sp_track_label

            hist = st.session_state.get("sp_history", [])
            hist.insert(0, {
                "Faixa":       sp_track_label,
                "ID":          sp_track_id,
                "Operação":    result.step,
                "Prof. antes": result.depth_before,
                "Prof. depois":result.depth_after,
                "Acessos":     result.play_count,
                "Rotações":    result.rotations,
                "Altura":      result.height,
            })
            st.session_state.sp_history = hist[:20]
        except Exception as exc:
            st.error(f"Erro ao registrar acesso: {exc}")

    if "sp_last_access" in st.session_state:
        r: AccessResult = st.session_state.sp_last_access
        lbl: str = st.session_state.sp_last_access_label

        step_colour = {"Zig": "green", "ZigZig": "orange", "ZigZag": "red", "None": "gray"}.get(r.step, "gray")

        st.markdown(f"**Último acesso:** {lbl}")
        a1, a2, a3, a4, a5 = st.columns(5)
        a1.metric("Operação",       r.step)
        a2.metric("Prof. antes",    r.depth_before)
        a3.metric("Prof. depois",   r.depth_after)
        a4.metric("Acessos totais", r.play_count)
        a5.metric("Rotações",       r.rotations)

        left, mid, right = st.columns([5, 1, 5])
        with left:
            st.subheader("Antes do splay")
            st.code(r.tree_before, language=None)
        with mid:
            st.markdown(
                f"<div style='text-align:center;padding-top:60px;font-size:2rem;"
                f"color:{step_colour}'>→</div>"
                f"<div style='text-align:center;color:{step_colour};"
                f"font-weight:bold'>{r.step}</div>",
                unsafe_allow_html=True,
            )
        with right:
            st.subheader("Depois do splay")
            st.code(r.tree_after, language=None)

    st.divider()
    st.subheader("Histórico de acessos")

    history = st.session_state.get("sp_history", [])
    if not history:
        st.caption("Nenhum acesso registrado ainda nesta sessão.")
    else:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)

    with st.expander("Complexidade amortizada e localidade temporal", expanded=False):
        st.markdown(
            """
**Splay Tree — O(log n) amortizado**

Operações individuais podem custar O(n) no pior caso, mas qualquer sequência
de M operações custa O(M log n) no total — O(log n) amortizado por operação.

**Localidade temporal:** faixas acessadas recentemente ficam próximas da raiz.
Se as próximas buscas forem sobre as mesmas faixas (padrão comum em sessões de
reprodução), o custo médio tende a O(1) — a estrutura "aprende" o padrão.

| Operação | Custo amortizado |
|----------|-----------------|
| access   | O(log n)        |
| insert   | O(log n)        |
| search   | O(log n)        |
| remove   | O(log n)        |

**Comparação com outras BSTs:**
- BST desbalanceada: O(n) no pior caso, sem garantia.
- AVL / Red-Black: O(log n) garantido por operação, mas sem auto-ajuste.
- Splay Tree: O(log n) amortizado **e** se adapta ao padrão de acesso.
            """
        )

# Results are generated explicitly by the C++ benchmark on the processed CSV.
st.divider()
st.subheader("Benchmark de similaridade — FMA")
benchmark_path = Path(__file__).resolve().parents[2] / "benchmark" / "results" / "benchmark_recall.csv"
if benchmark_path.is_file():
    benchmark = pd.read_csv(benchmark_path)
    st.dataframe(benchmark, use_container_width=True, hide_index=True)
    if {"num_candidates", "recall_at_10"}.issubset(benchmark.columns):
        st.line_chart(benchmark.set_index("num_candidates")[["recall_at_10"]])
    st.caption("Resultado da última execução do benchmark; execute novamente após substituir o dataset.")
else:
    st.info("Ainda não há resultados medidos com o dataset processado.")
    st.code("./build/benchmark_similarity", language="bash")

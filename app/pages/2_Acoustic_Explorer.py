"""Explore a Skip List candidate window using distribution-aware acoustic filters."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.music import track_selector
from services.acoustic_filters import FEATURE_COLUMNS, FEATURE_LABELS, matching_ids, percentile_bounds
from services.core_bridge import get_bridge
from services.dataset import PROCESSED_CSV, get_track, load_catalog


@st.cache_data
def load_features(signature: tuple[int, int]) -> pd.DataFrame:
    return pd.read_csv(
        PROCESSED_CSV, usecols=["track_id", *FEATURE_COLUMNS], index_col="track_id"
    ).rename(columns=FEATURE_COLUMNS)


def reset_filters() -> None:
    for feature in FEATURE_LABELS:
        st.session_state[f"acoustic_percentile_{feature}"] = (0, 100)
        st.session_state[f"acoustic_value_{feature}"] = (0.0, 1.0)


st.set_page_config(page_title="Acoustic Explorer — AME", layout="wide")
st.title("Acoustic Explorer")
st.markdown(
    "Escolha uma música de referência e explore seus candidatos da **Skip List** "
    "por características acústicas. Os resultados são ordenados por similaridade."
)

bridge = get_bridge()
if bridge is None:
    st.error(st.session_state.get("bridge_error", "Núcleo C++ indisponível."))
    st.code("cmake -S . -B build && cmake --build build", language="bash")
    st.stop()
if not bridge.is_loaded:
    st.warning("Dataset não carregado. Execute `python preprocessing/build_dataset.py`.")
    st.stop()

catalog = load_catalog()
track_id, track_label = track_selector(catalog, "ae_track_sel", "Selecione uma faixa de referência")
stat = PROCESSED_CSV.stat()
signature = (stat.st_mtime_ns, stat.st_size)
features = load_features(signature)

with st.expander("Parâmetros de busca", expanded=True):
    num_candidates = st.slider(
        "Candidatos da Skip List", min_value=100, max_value=5000, value=500, step=100,
        key="ae_candidate_count",
        help="Uma janela maior permite encontrar mais faixas que atendam aos filtros.",
    )

st.subheader("Filtros acústicos")
mode = st.radio(
    "Escala dos filtros", ["Percentis do catálogo", "Valores normalizados"],
    horizontal=True, key="acoustic_filter_mode",
)
if mode == "Percentis do catálogo":
    st.caption(
        "Os percentis indicam a posição no catálogo: 0% é o menor valor e 100% é o maior. "
        "Por exemplo, de 0% a 50% seleciona aproximadamente a metade das faixas com valores mais baixos "
        "naquele atributo. Valores empatados são mantidos juntos."
    )
else:
    st.caption(
        "Ajuste diretamente os valores entre 0 e 1, em passos de 0,001. "
        "As músicas podem estar concentradas em uma faixa pequena dessa escala."
    )
st.button("Restaurar filtros", on_click=reset_filters)

bounds: dict[str, tuple[float, float]] = {}
for col, (feature, label) in zip(st.columns(len(FEATURE_LABELS)), FEATURE_LABELS.items()):
    with col:
        values = features[feature]
        if mode == "Percentis do catálogo":
            interval = st.slider(
                label, min_value=0, max_value=100, value=(0, 100), step=1,
                format="%d%%", key=f"acoustic_percentile_{feature}",
            )
            bounds[feature] = percentile_bounds(values, interval)
        else:
            bounds[feature] = st.slider(
                label, min_value=0.0, max_value=1.0, value=(0.0, 1.0), step=0.001,
                format="%.4f", key=f"acoustic_value_{feature}",
            )
        low, high = bounds[feature]
        st.caption(f"Intervalo aplicado: {low:.4f} a {high:.4f}")
        if track_id in features.index:
            reference = float(features.at[track_id, feature])
            position = float(values.le(reference).mean() * 100)
            st.caption(f"Referência: {reference:.4f} · percentil {position:.1f}%")

# Preview the whole catalog separately from the local candidate window.
allowed_ids = matching_ids(features, bounds)
allowed = set(allowed_ids) - {track_id}
catalog_count = len(allowed)
search_key = (track_id, num_candidates, signature)
cached = st.session_state.get("ae_candidate_search")
current_search = cached is not None and cached["key"] == search_key

st.caption(
    f"{catalog_count:,} outras faixas do catálogo atendem a todos os filtros. "
    "Os cinco intervalos são aplicados em conjunto."
)
if st.button("Buscar e filtrar", type="primary"):
    try:
        with st.spinner("Buscando candidatos..."):
            results, metrics = bridge.find_similar(track_id, num_candidates, top_k=num_candidates)
        cached = {"key": search_key, "results": results, "metrics": metrics}
        st.session_state.ae_candidate_search = cached
        current_search = True
    except RuntimeError as exc:
        st.error(f"Erro na busca: {exc}")

if not current_search:
    # Results from another reference/budget must not look current.
    for name in ("ae_results", "ae_n_from_sl", "ae_n_after_filter", "ae_metrics", "ae_query_label"):
        st.session_state.pop(name, None)
    if cached is not None:
        st.info("A referência ou o número de candidatos mudou. Clique em Buscar e filtrar para atualizar a busca.")
    else:
        st.info("Clique em Buscar e filtrar. Depois, mover os filtros atualizará os resultados automaticamente.")
else:
    candidates = cached["results"]
    filtered = [result for result in candidates if result.track_id in allowed]
    metrics = cached["metrics"]
    st.session_state.ae_results = filtered
    st.session_state.ae_n_from_sl = len(candidates)
    st.session_state.ae_n_after_filter = len(filtered)
    st.session_state.ae_metrics = metrics
    st.session_state.ae_query_label = track_label

    st.divider()
    st.subheader(f"Resultados para: {track_label}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Candidatos recuperados", len(candidates))
    m2.metric("Candidatos após filtros", len(filtered))
    m3.metric("Faixas no catálogo após filtros", catalog_count)
    m4.metric("Tempo da busca (ms)", f"{metrics.total_ms:.2f}")
    st.caption(
        "Os filtros atualizam estes resultados automaticamente. O tempo se refere à última busca de candidatos. "
        "A seleção de candidatos e a contagem do catálogo excluem a música de referência."
    )
    if filtered:
        rows = []
        for i, result in enumerate(filtered[:20], start=1):
            info = get_track(result.track_id, catalog)
            row = {"Posição": i, "Título": info["title"], "Artista": info["artist"],
                   "Gênero": info["genre"], "Distância": round(result.distance, 6)}
            row.update({label: round(float(features.at[result.track_id, feature]), 4)
                        for feature, label in FEATURE_LABELS.items()})
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(f"Exibindo {len(rows)} de {len(filtered):,} candidatos aprovados, por ordem de similaridade.")
    elif catalog_count:
        st.info(
            f"Há {catalog_count:,} faixas compatíveis no catálogo, mas nenhuma entre os {len(candidates):,} "
            "candidatos desta referência. Aumente o número de candidatos e refaça a busca, "
            "escolha outra referência ou amplie os filtros."
        )
    else:
        st.info("Nenhuma outra faixa do catálogo atende à combinação atual. Amplie os intervalos ou restaure os filtros.")

with st.expander("Ver distribuição dos valores"):
    shown = st.selectbox("Atributo", list(FEATURE_LABELS), format_func=FEATURE_LABELS.get,
                         key="acoustic_distribution_feature")
    values = features[shown].dropna()
    counts, edges = np.histogram(values, bins=50, range=(0.0, 1.0))
    distribution = pd.DataFrame({"Valor normalizado": (edges[:-1] + edges[1:]) / 2, "Faixas": counts})
    st.bar_chart(distribution, x="Valor normalizado", y="Faixas")
    quantiles = values.quantile([0.1, 0.5, 0.9])
    st.caption(
        f"10% das faixas têm valor até {quantiles.loc[0.1]:.4f}; "
        f"50% até {quantiles.loc[0.5]:.4f}; 90% até {quantiles.loc[0.9]:.4f}. "
        "Normalizar entre 0 e 1 não distribui as músicas uniformemente."
    )

with st.expander("Como os filtros funcionam"):
    st.markdown(
        "A **Skip List** recupera uma janela em torno da chave acústica da referência. "
        "Esses candidatos são ordenados pela distância euclidiana e filtrados pelos cinco intervalos.\n\n"
        "No modo de percentis, cada controle é convertido em limites dos valores normalizados do catálogo. "
        "A Acoustic Key e a distância continuam usando as mesmas características.\n\n"
        "Os candidatos de uma referência podem se concentrar em regiões específicas. "
        "Por isso, selecionar metade do catálogo em um atributo não garante manter metade dos candidatos; "
        "combinar vários filtros também pode reduzir bastante os resultados."
    )

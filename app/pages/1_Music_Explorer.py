"""Music search with an exact default and an explicitly experimental window."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import streamlit as st
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.music import track_selector, render_player
from services.core_bridge import get_bridge
from services.dataset import get_track, load_catalog

st.set_page_config(page_title="Music Explorer — AME", layout="wide")
st.title("Music Explorer")
bridge = get_bridge()
if bridge is None:
    st.error(st.session_state.get("bridge_error", "Núcleo indisponível")); st.stop()
if not bridge.is_loaded:
    st.warning("Importe o FMA para habilitar a busca."); st.stop()
catalog = load_catalog()
track_id, track_label = track_selector(catalog, "music_track")
st.subheader(track_label)
render_player(track_id, catalog)
st.caption(f"Acoustic Key (Morton): {bridge.track_key(track_id)}")
mode = st.radio("Modo de busca", ["Exata certificada", "Aproximada experimental"], horizontal=True)
exact = mode == "Exata certificada"
if exact:
    st.caption("A janela inicia a busca. O índice expande a consulta até certificar os melhores resultados nas 44 características.")
else:
    st.warning("A janela aproximada pode perder vizinhos relevantes. Ative a comparação exaustiva para medir a precisão desta consulta.")
num_candidates = st.slider("Candidatos iniciais da Skip List", 50, max(100, min(25000, len(catalog))), 500 if len(catalog)>=500 else 50, step=50)
top_k = st.slider("Top-K resultados", 1, 20, 10)
evaluate = st.checkbox("Comparar com busca exaustiva (Recall@K)")
query_key = (track_id, num_candidates, top_k, exact, evaluate)
if st.button("Encontrar músicas semelhantes", type="primary"):
    try:
        with st.spinner("Buscando..."):
            results, metrics = bridge.find_similar(track_id, num_candidates, top_k, exact, evaluate)
        st.session_state.search_snapshot = {"key": query_key, "results": results, "metrics": metrics, "label": track_label}
    except RuntimeError as exc:
        st.error(str(exc))
snapshot = st.session_state.get("search_snapshot")
if snapshot and snapshot["key"] != query_key:
    st.info("A faixa ou os parâmetros mudaram. Execute a busca para atualizar os resultados.")
elif snapshot:
    results, metrics = snapshot["results"], snapshot["metrics"]
    st.subheader(f"Resultados para: {snapshot['label']}")
    c = st.columns(4)
    for col, label, value in zip(c, ["Faixas no índice", "Candidatos iniciais", "Distâncias calculadas", "Descartes certificados"],
                               [metrics.total_tracks, metrics.initial_candidates, metrics.candidates, metrics.pruned]):
        col.metric(label, value)
    c = st.columns(4)
    c[0].metric("Comparações de chave", metrics.skiplist_comparisons)
    c[1].metric("Localização nos índices (ms)", f"{metrics.skiplist_ms:.3f}")
    c[2].metric("Expansão e similaridade (ms)", f"{metrics.similarity_ms:.3f}")
    c[3].metric("Tempo total no núcleo (ms)", f"{metrics.total_ms:.3f}")
    if metrics.recall >= 0:
        a, b = st.columns(2)
        a.metric(f"Recall@{min(top_k, len(catalog)-1)} medido", f"{metrics.recall:.1%}")
        b.metric("Busca exaustiva (ms)", f"{metrics.brute_force_ms:.3f}")
    st.caption("Tempos excluem interface, comunicação e a comparação exaustiva opcional. Comparações de chave e distâncias são contagens diferentes.")
    rows = []
    for position, result in enumerate(results, 1):
        info = get_track(result.track_id, catalog)
        rows.append({"Posição": position, "Título": info["title"], "Artista": info["artist"], "Gênero": info["genre"], "Distância": result.distance})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if results:
        selected, _ = track_selector(catalog.loc[[r.track_id for r in results]], "recommendation_track", "Ouvir uma recomendação")
        render_player(selected, catalog)
    else:
        st.info("Nenhuma outra faixa disponível.")
with st.expander("Como a busca certifica o resultado"):
    st.markdown("A janela Morton fornece os primeiros candidatos. Uma segunda Skip List ordena distâncias a uma faixa pivô. "
                "A busca percorre os vizinhos nos dois sentidos e usa a desigualdade triangular para descartar faixas que não podem melhorar o Top-K. "
                "Quatro pivôs fornecem limites adicionais. Ela só encerra quando as faixas restantes não podem vencer o pior resultado atual. "
                "Empates são resolvidos pelo ID. O modo exato pode custar mais que a busca exaustiva em consultas pouco seletivas; "
                "a janela experimental troca precisão por menor trabalho.")

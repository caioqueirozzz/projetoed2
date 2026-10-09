"""Session playback history backed by its own C++ Splay Tree."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.track_card import render_track_card, render_track_card_styles
from services.core_bridge import get_bridge
from services.dataset import get_track, load_catalog

st.set_page_config(page_title="Perfil de reprodução — AME", layout="wide")
with st.container(horizontal=True, vertical_alignment="center"):
    st.title("Perfil de reprodução")
    refresh = st.button("Atualizar", icon=":material/refresh:",
                        type="tertiary", key="history_refresh", width="content",
                        help="Atualizar a ordem das músicas e as contagens de reprodução.")
st.caption("As reproduções são registradas na hora. Esta lista é atualizada ao voltar à página ou clicar em atualizar.")
bridge = get_bridge()
if bridge is None:
    st.error(st.session_state.get("bridge_error", "Núcleo indisponível"))
    st.stop()
if not bridge.is_loaded:
    st.warning("Importe o FMA para ouvir músicas e criar seu histórico.")
    st.stop()

catalog = load_catalog()


def find_in_history() -> None:
    track_id = st.session_state.history_track
    if track_id is None:
        st.session_state.pop("history_lookup", None)
        return
    try:
        st.session_state.history_lookup = bridge.search_history(int(track_id))
        st.session_state.pop("history_error", None)
    except RuntimeError as exc:
        st.session_state.history_error = str(exc)


def toggle_full_history() -> None:
    st.session_state.history_expanded = not st.session_state.get("history_expanded", False)


try:
    # A play event reruns Streamlit. Keep this visit's view stable so the cards
    # and audio controls do not move while the user is listening. Other pages
    # discard history_view on entry; returning here loads a fresh snapshot.
    if refresh or "history_view" not in st.session_state:
        st.session_state.history_view = bridge.playback_history()
    history = st.session_state.history_view
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

entries = history["entries"]
if not entries:
    st.info("Seu histórico está vazio. Inicie uma música no Music Explorer para adicioná-la aqui.")
    st.page_link("pages/1_Music_Explorer.py", label="Ouvir músicas", icon="🎵")
    st.stop()

first, second = st.columns(2)
first.metric("Músicas no histórico", history["size"])
second.metric("Reproduções na sessão", history["total_plays"])

labels = {
    entry["track_id"]: f"{get_track(entry['track_id'], catalog)['title']} — "
    f"{get_track(entry['track_id'], catalog)['artist']} (#{entry['track_id']})"
    for entry in entries
}
# A stable option order avoids resetting the selection when recency changes.
selected = st.selectbox(
    "Buscar no histórico por título, artista ou ID",
    sorted(labels),
    index=None,
    format_func=labels.get,
    key="history_track",
    filter_mode="contains",
    placeholder="Digite para encontrar uma música que você já ouviu",
    on_change=find_in_history,
)
if st.session_state.get("history_error"):
    st.error(st.session_state.history_error)
st.subheader("Resultado da busca" if selected is not None else "Músicas ouvidas recentemente")
render_track_card_styles()
expanded = st.session_state.get("history_expanded", False)
if selected is not None:
    # Search covers the entire history, including tracks outside the first ten.
    visible_entries = [entry for entry in entries if entry["track_id"] == selected]
else:
    visible_entries = entries if expanded else entries[:10]
for entry in visible_entries:
    plays = entry["play_count"]
    count_label = "1 reprodução" if plays == 1 else f"{plays} reproduções"
    render_track_card(entry["track_id"], catalog, key="history", detail=count_label)

if selected is None and len(entries) > 10:
    st.caption(f"Mostrando {len(visible_entries)} de {len(entries)} músicas")
    st.button("Ver menos" if expanded else "Ver histórico completo",
              key="history_expand", type="tertiary", on_click=toggle_full_history)

with st.expander("Splay Tree na última atualização"):
    st.markdown(
        "Cada reprodução ou busca leva a música acessada à **raiz** da Splay Tree. "
        "A árvore busca pelo ID; o campo acima filtra os títulos, artistas e IDs das músicas já ouvidas. "
        "Buscar não conta como reprodução. A lista de músicas recentes usa a ordem das reproduções, "
        "pois a árvore inteira não fica em ordem cronológica."
    )
    root = history["root_id"]
    st.caption(f"Raiz na última atualização: {labels[root]}")
    a, b = st.columns(2)
    a.metric("Comparações na última operação", history["comparisons"])
    b.metric("Rotações na última operação", history["rotations"])
    st.code(history["tree_ascii"], language=None)
    if history["size"] > 40:
        st.caption("Visualização limitada a 40 nós; todas as músicas continuam no histórico.")

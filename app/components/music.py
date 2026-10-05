"""Catalog selector and audio player for Music Explorer."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.dataset import audio_path, get_track


def track_selector(catalog: pd.DataFrame, key: str,
                   label: str = "Selecione uma faixa") -> tuple[int, str]:
    if catalog.empty:
        tid = int(st.number_input("ID da faixa (demonstração)", min_value=1, value=2, key=key))
        return tid, f"Track {tid}"
    # Streamlit filters the full dropdown in the browser on every keystroke.
    # Contains matching keeps the current text contiguous and preserves catalog
    # order; clearing it restores all options, including with a 25k-track list.
    # Vectorized labels avoid 25k row lookups.
    labels = (catalog.title.astype(str) + " — " + catalog.artist.astype(str)
              + " (#" + catalog.index.astype(str) + ")").to_dict()
    tid = int(st.selectbox(
        label, catalog.index.tolist(), format_func=labels.get, key=key,
        filter_mode="contains",
        placeholder="Digite o nome da música ou percorra a lista",
    ))
    st.caption("Digite no campo para filtrar a cada letra. Apague o texto para ver todas as opções.")
    return tid, labels[tid]


def render_player(track_id: int, catalog: pd.DataFrame) -> None:
    info = get_track(track_id, catalog)
    st.caption(f"{info['artist']} · {info['genre']} · ID {track_id}")
    path = audio_path(track_id, catalog)
    if path:
        st.audio(str(path), format="audio/mpeg")
    else:
        st.info("Áudio desta faixa não encontrado. Verifique a pasta fma_medium.")

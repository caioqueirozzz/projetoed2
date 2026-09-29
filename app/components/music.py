"""Shared catalog selector and explicit playback-profile controls."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.dataset import audio_path, format_label, get_track


def track_selector(catalog: pd.DataFrame, key: str,
                   label: str = "Selecione uma faixa") -> tuple[int, str]:
    if catalog.empty:
        tid = int(st.number_input("ID da faixa (demonstração)", min_value=1, value=2, key=key))
        return tid, f"Track {tid}"
    # All tracks remain searchable; vectorized labels avoid 25k row lookups.
    labels = (catalog.title.astype(str) + " — " + catalog.artist.astype(str)
              + " (#" + catalog.index.astype(str) + ")").to_dict()
    tid = int(st.selectbox(label, catalog.index.tolist(), format_func=labels.get, key=key))
    return tid, labels[tid]


def render_player(track_id: int, catalog: pd.DataFrame, bridge, key: str) -> None:
    info = get_track(track_id, catalog)
    st.caption(f"{info['artist']} · {info['genre']} · ID {track_id}")
    path = audio_path(track_id, catalog)
    if path:
        st.audio(str(path), format="audio/mpeg")
    else:
        st.info("Áudio desta faixa não encontrado. Verifique a pasta fma_medium.")
    # st.audio does not expose a playback event to Python. Register explicitly,
    # never infer a play merely from rendering a player during a Streamlit rerun.
    if st.button("Registrar acesso no perfil", key=f"{key}_access"):
        try:
            access = bridge.register_access(track_id)
            st.session_state.last_access = access
            history = st.session_state.get("access_history", [])
            history.insert(0, {
                "Faixa": format_label(track_id, catalog), "ID": track_id,
                "Operação": access.step, "Prof. antes": access.depth_before,
                "Prof. depois": access.depth_after, "Acessos": access.play_count,
                "Rotações": access.rotations, "Altura": access.height,
            })
            st.session_state.access_history = history[:20]
            st.success(f"Faixa {track_id} na raiz da Splay Tree; {access.play_count} acesso(s).")
        except RuntimeError as exc:
            st.error(str(exc))

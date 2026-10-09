"""Catalog selector and audio player for Music Explorer."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from pathlib import Path

from services.core_bridge import get_bridge
from services.dataset import audio_path, get_track


# Keep the native player (including streamed media URLs and controls). This
# component reports its play event without replacing or restarting the audio.
_playback_events = st.components.v2.component(
    "ame_playback_events",
    js=Path(__file__).with_name("playback_events.js").read_text(encoding="utf-8"),
    isolate_styles=False,
)


def _record_playback(component_key: str, track_id: int) -> None:
    event = st.session_state[component_key].started
    if not isinstance(event, dict) or event.get("track_id") != track_id:
        return
    token, sequence = event.get("token"), event.get("sequence")
    if not isinstance(token, str) or not token or type(sequence) is not int or sequence < 1:
        return
    seen = st.session_state.setdefault("playback_last_events", {})
    previous_token, previous_sequence = seen.get(component_key, (None, 0))
    if previous_token != token:
        previous_sequence = 0
    if sequence <= previous_sequence:
        return
    bridge = get_bridge()
    try:
        if bridge is None:
            raise RuntimeError("Núcleo indisponível para registrar a reprodução.")
        for count in range(previous_sequence + 1, sequence + 1):
            bridge.record_play(track_id)
            seen[component_key] = (token, count)
        st.session_state.pop("playback_error", None)
    except RuntimeError as exc:
        st.session_state.playback_error = str(exc)


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


def render_player(track_id: int, catalog: pd.DataFrame, key: str = "music", *,
                  show_metadata: bool = True) -> None:
    if show_metadata:
        info = get_track(track_id, catalog)
        st.caption(f"{info['artist']} · {info['genre']} · ID {track_id}")
    path = audio_path(track_id, catalog)
    if path:
        container_key = f"playback_player_{key}_{track_id}"
        component_key = f"playback_event_{key}_{track_id}"
        with st.container(key=container_key, gap=None):
            st.audio(str(path), format="audio/mpeg")
            _playback_events(
                key=component_key,
                data={"track_id": track_id, "container_key": container_key},
                on_started_change=lambda: _record_playback(component_key, track_id),
                height=0,
            )
    else:
        st.info("Áudio desta faixa não encontrado. Verifique a pasta fma_medium.")
    if st.session_state.get("playback_error"):
        st.error(f"Não foi possível atualizar o histórico: {st.session_state.playback_error}")

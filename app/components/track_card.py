"""Shared music cards for search results and playback history."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.music import render_player
from services.dataset import get_track


def render_track_card_styles() -> None:
    st.html("""
    <style>
        [class*="st-key-music_card_"] {
            border-radius: 18px;
            padding: 1.15rem 1.35rem;
            background: var(--secondary-background-color, rgba(128, 128, 128, .045));
        }
        .music-track { display: flex; align-items: center; gap: 1rem; min-width: 0; }
        .music-track-icon {
            display: grid; place-items: center; flex: 0 0 3rem; height: 3rem;
            border-radius: 14px; background: rgba(128, 128, 128, .12);
            font-size: 1.5rem;
        }
        .music-track h3 {
            margin: 0 0 .35rem; padding: 0; font-size: 1.3rem;
            font-weight: 700; line-height: 1.35; overflow-wrap: anywhere;
        }
        .music-track p { margin: 0; font-size: 1.05rem; opacity: .85; overflow-wrap: anywhere; }
    </style>
    """)


def render_track_card(track_id: int, catalog: pd.DataFrame, *, key: str,
                      detail: str, position: int | None = None) -> None:
    info = get_track(track_id, catalog)
    badge = f'{position:02d}' if position is not None else '♪'
    with st.container(border=True, key=f"music_card_{key}_{track_id}"):
        details, player = st.columns([3, 2], gap="large", vertical_alignment="center")
        with details:
            st.html(f"""
                <div class="music-track">
                    <div class="music-track-icon">{badge}</div>
                    <div>
                        <h3>{escape(str(info['title']))}</h3>
                        <p>{escape(str(info['artist']))}</p>
                    </div>
                </div>
            """)
            st.caption(f"{info['genre']} · {detail} · ID {track_id}")
        with player:
            render_player(track_id, catalog, key=key, show_metadata=False)

"""Adaptive Music Explorer — Streamlit entry point (plan §22, §47).

Run with:  streamlit run app/app.py

The four pages live in ``app/pages/`` and are auto-discovered by Streamlit's
multipage support:
  1. Music Explorer   — busca por similaridade
  2. Acoustic Explorer — exploração por características
  3. Playback Profile — Splay Tree (perfil adaptativo)
  4. Structures Lab   — demonstração isolada das estruturas
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Adaptive Music Explorer", page_icon="🎵", layout="wide")

st.title("🎵 Adaptive Music Explorer")
st.markdown(
    """
    Busca musical adaptativa sobre o **FMA Medium**, demonstrando duas
    estruturas de dados protagonistas:

    - **Skip List** — índice acústico probabilístico (redução do espaço de busca).
    - **Splay Tree** — perfil de reprodução autoajustável (localidade temporal).

    Use a barra lateral para navegar entre as páginas.
    """
)

st.info("Scaffold inicial — conecte o núcleo C++ pelos serviços em `app/services/`.")

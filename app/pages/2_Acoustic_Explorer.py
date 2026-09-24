"""Página 2 — Exploração Acústica (plan §25).

Visualizar e explorar características das músicas com filtros por atributo
(RMS, Spectral Centroid, ZCR, Bandwidth, Rolloff). Os filtros usam a região
acústica da Skip List como ponto inicial e depois aplicam filtros exatos.
"""

import streamlit as st

st.title("Acoustic Explorer")

# TODO: sliders por característica, barras de atributos, e filtragem que parte
#       da vizinhança na Skip List (§25).
st.write("Scaffold — explorar características acústicas com filtros.")

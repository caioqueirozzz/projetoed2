"""Página 3 — Perfil de Reprodução (plan §26, §27).

Demonstra a Splay Tree como estrutura adaptativa de perfil de reprodução.

Funcionalidades:
  - Selecionar uma faixa e registrar o acesso na Splay Tree.
  - Ver a árvore antes e depois do splay.
  - Identificar a operação realizada: Zig, Zig-Zig, Zig-Zag, ou None.
  - Exibir métricas por acesso: profundidade antes/depois, rotações, acessos.
  - Histórico dos últimos acessos da sessão.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Allow importing services from the app package root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.music import track_selector
from services.core_bridge import AccessResult, get_bridge
from services.dataset import audio_path, format_label, load_catalog

# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Playback Profile — AME", layout="wide")
st.title("Perfil de Reprodução")
st.markdown(
    "Registra acessos às faixas na **Splay Tree**: cada reprodução move a "
    "faixa para a raiz, explorando localidade temporal (plan §17, §45)."
)

# ── bridge availability ───────────────────────────────────────────────────────

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

if not bridge.is_loaded:
    st.warning(
        "Dataset não carregado. O perfil adaptativo funciona normalmente, "
        "mas a busca por similaridade está desabilitada. "
        "Execute `python preprocessing/build_dataset.py` para gerar o CSV.",
        icon="⚠",
    )

# ── catalog + track selector ──────────────────────────────────────────────────

catalog = load_catalog()

track_id, track_label = track_selector(catalog, "profile_track", "Selecione uma faixa")

# ── access button ─────────────────────────────────────────────────────────────

col_btn, col_info = st.columns([1, 3])
with col_btn:
    do_access = st.button("▶ Registrar acesso", type="primary", use_container_width=True)

with col_info:
    st.caption(
        f"Faixa selecionada: **{track_label}** (ID {track_id}). "
        "Clicar registra a reprodução na Splay Tree e mostra o splay."
    )

if do_access:
    try:
        result: AccessResult = bridge.register_access(track_id)
        st.session_state.last_access = result

        # Prepend to history (keep last 20).
        hist = st.session_state.get("access_history", [])
        hist.insert(0, {
            "Faixa": track_label,
            "ID": track_id,
            "Operação": result.step,
            "Prof. antes": result.depth_before,
            "Prof. depois": result.depth_after,
            "Acessos": result.play_count,
            "Rotações": result.rotations,
            "Altura": result.height,
        })
        st.session_state.access_history = hist[:20]
    except Exception as exc:
        st.error(f"Erro ao registrar acesso: {exc}")

st.divider()

# ── last access: before / after visualization ─────────────────────────────────

if "last_access" in st.session_state:
    r: AccessResult = st.session_state.last_access

    # Step badge colour.
    step_colour = {
        "Zig":    "green",
        "ZigZig": "orange",
        "ZigZag": "red",
        "None":   "gray",
    }.get(r.step, "gray")

    # Header row.
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Operação",       r.step)
    m2.metric("Prof. antes",    r.depth_before)
    m3.metric("Prof. depois",   r.depth_after)
    m4.metric("Acessos totais", r.play_count)
    m5.metric("Rotações",       r.rotations)

    # Before / after trees side by side.
    left, mid, right = st.columns([5, 1, 5])

    with left:
        st.subheader("Antes do splay")
        st.code(r.tree_before, language=None)

    with mid:
        st.markdown(
            f"<div style='text-align:center; padding-top:60px; "
            f"font-size:2rem; color:{step_colour}'>→</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='text-align:center; color:{step_colour}; "
            f"font-weight:bold'>{r.step}</div>",
            unsafe_allow_html=True,
        )

    with right:
        st.subheader("Depois do splay")
        st.code(r.tree_after, language=None)

    # Audio player (shown only when the audio file exists).
    apath = audio_path(r.track_id, catalog)
    if apath:
        st.audio(str(apath))

    st.divider()

# ── current splay state ───────────────────────────────────────────────────────

with st.expander("Estado atual da Splay Tree", expanded=False):
    try:
        state = bridge.get_splay_state()
        c1, c2, c3 = st.columns(3)
        c1.metric("Raiz",           state.root_id if state.root_id >= 0 else "—")
        c2.metric("Altura",         state.height)
        c3.metric("Faixas no perfil", state.size)
        st.code(state.tree_ascii or "(árvore vazia)", language=None)
    except Exception as exc:
        st.error(f"Erro ao ler estado da árvore: {exc}")

# ── access history ────────────────────────────────────────────────────────────

st.subheader("Histórico de acessos da sessão")

history = st.session_state.get("access_history", [])
if not history:
    st.caption("Nenhum acesso registrado ainda nesta sessão.")
else:
    import pandas as pd
    df = pd.DataFrame(history)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ── explanation panel ─────────────────────────────────────────────────────────

with st.expander("Como funciona (plan §17–§20)", expanded=False):
    st.markdown(
        """
**Splay Tree — Perfil Adaptativo**

Cada acesso a uma faixa:
1. Busca o nó pelo `trackId` (ou insere se for o primeiro acesso).
2. Incrementa o `playCount`.
3. Realiza o **splay**: move o nó para a raiz por uma sequência de rotações.

**Operações de rotação:**
| Operação | Quando ocorre |
|---|---|
| **Zig** | Nó tem pai, mas não tem avô (rotação simples). |
| **Zig-Zig** | Nó e pai estão na mesma direção (esq-esq ou dir-dir). |
| **Zig-Zag** | Nó e pai estão em direções opostas (esq-dir ou dir-esq). |

**Propriedade de localidade temporal**: faixas acessadas frequentemente
ficam próximas da raiz, reduzindo o custo médio de busca. Isso é o
comportamento adaptativo que a Splay Tree explora.
        """
    )

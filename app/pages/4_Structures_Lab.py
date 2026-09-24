"""Página 4 — Laboratório de Estruturas (plan §28, §29, §30).

Demonstração isolada das duas estruturas para a disciplina de Estrutura de
Dados:
  - Skip List: inserir / buscar / remover / visualizar níveis / percurso /
    contagem de comparações / tempo.
  - Splay Tree: inserir / buscar / remover / acessar / visualizar árvore /
    mostrar rotações / raiz anterior e nova raiz.
"""

import streamlit as st

st.title("Structures Lab")

tab_skip, tab_splay = st.tabs(["Skip List", "Splay Tree"])

with tab_skip:
    # TODO: controles de insert/search/remove e visualização de níveis (§29).
    st.write("Scaffold — laboratório da Skip List.")

with tab_splay:
    # TODO: controles de insert/search/remove/access e rotações (§30).
    st.write("Scaffold — laboratório da Splay Tree.")

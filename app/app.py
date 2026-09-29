"""Adaptive Music Explorer — run with streamlit run app/app.py."""
from __future__ import annotations

import json
import streamlit as st
from services.core_bridge import get_bridge
from services.dataset import PROCESSED_CSV, load_catalog

st.set_page_config(page_title="Adaptive Music Explorer", page_icon="🎵", layout="wide")
st.title("🎵 Adaptive Music Explorer")
st.markdown(
    "Explore o **FMA Medium** por similaridade acústica. A **Skip List** recupera "
    "candidatos para a busca e a **Splay Tree** organiza o perfil de acessos. "
    "Use a barra lateral para navegar entre as páginas."
)
bridge = get_bridge()
if bridge is None:
    st.error(st.session_state.get("bridge_error", "Núcleo C++ indisponível."))
    st.code("cmake -S . -B build\ncmake --build build", language="bash")
elif not bridge.is_loaded:
    st.info("Importe os arquivos do FMA para habilitar a busca e os players.")
    st.code('python preprocessing/build_dataset.py --import-zip "/caminho/archive.zip"', language="bash")
    st.caption("Instruções de download e importação: data/README.md.")
else:
    catalog = load_catalog()
    c1, c2 = st.columns(2)
    c1.metric("Faixas no índice", bridge.track_count)
    c2.metric("Gêneros", catalog.genre.nunique())
    report_path = PROCESSED_CSV.with_name("dataset_report.json")
    if report_path.is_file():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            st.caption(f"Última importação: {report['audio_available']:,} áudios presentes; "
                       f"{report['audio_missing']:,} ausentes ou vazios.")
            if report["audio_missing"]:
                st.warning("Parte dos áudios está ausente. A busca funciona; confira a pasta fma_medium para reproduzir todas as faixas.")
        except (OSError, ValueError, KeyError):
            st.warning("Relatório de importação indisponível; execute novamente o pré-processamento.")
    st.success("Dataset carregado. Abra Music Explorer para buscar e ouvir músicas.")

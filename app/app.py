"""Application entrypoint: open Music Explorer and expose only the three pages."""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Adaptive Music Explorer", page_icon="🎵", layout="wide")
page = st.navigation([
    st.Page("pages/1_Music_Explorer.py", title="Music Explorer", icon="🎵", default=True),
    st.Page("pages/2_Playback_Profile.py", title="Playback Profile", icon="🕘", url_path="Playback_Profile"),
    st.Page("pages/3_Structures_Lab.py", title="Structures Lab", icon="🧪", url_path="Structures_Lab"),
])
page.run()

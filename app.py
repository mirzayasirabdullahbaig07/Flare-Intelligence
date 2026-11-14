"""FLARE Intelligence entry point. Run from the project folder: streamlit run app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

st.set_page_config(page_title="FLARE Intelligence", page_icon="🔥", layout="wide",
                   initial_sidebar_state="expanded")

from src.theme import apply_theme, navigation, sidebar
from src.ui import built_pages, sidebar_note

apply_theme()
pages = [st.Page(path, title=title, default=(index == 0))
         for index, (path, title, _) in enumerate(built_pages())]
nav = navigation(pages)      # built-in menu hidden, our branded sidebar draws it
sidebar(pages, nav)
sidebar_note()
nav.run()
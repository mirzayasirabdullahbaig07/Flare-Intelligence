"""Shared theme, header and cached data loading for the FLARE Intelligence pages."""
from __future__ import annotations

import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import RAW_DIR, DataNotFoundError, load_experiment_table
from src.document_processor import load_chunks
from src.experiment_manager import count_imported_datasets
from src.preprocessing import clean_experiment_table
from src.source_manager import (get_publications, get_study_overview, load_investigation,
                                load_source_registry)

AMBER = "#E8933A"
PSI_URL = "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25"
DOI_BASE = "https://doi.org/"

PAGE_SPECS = [
    ("pages/00_Overview.py", "Overview", "Project status and data summary"),
    ("pages/01_Experiment_Explorer.py", "Experiment Explorer", "Inspect individual BASS-II tests"),
    ("pages/02_Flame_Analytics.py", "Flame Analytics", "Gas readings by fuel, geometry and investigator"),
    ("pages/03_Experiment_Comparison.py", "Experiment Comparison", "Compare selected tests side by side"),
    ("pages/04_AI_Research_Assistant.py", "AI Research Assistant", "Questions answered from NASA documents"),
    ("pages/05_Findings_Ranking.py", "Findings Ranking", "Documented findings and evidence scores"),
    ("pages/06_Mission_Insights.py", "Mission Insights", "Observations, interpretation and mission implications"),
    ("pages/07_Data_Management.py", "Data Management", "Upload, validate and export data"),
]

CSS = f"""
.block-container {{padding-top: 2rem; max-width: 1250px;}}
.flare-brand {{letter-spacing: .18em; font-size: .78rem; color: {AMBER};
               text-transform: uppercase; font-weight: 600;}}
.flare-title {{font-size: 2rem; font-weight: 600; margin: .1rem 0 .2rem 0;}}
.flare-sub {{color: #A8ADB5; margin-bottom: 1.2rem;}}
div[data-testid="stMetric"] {{background: #171A1F; border: 1px solid #262B33;
                              border-radius: 8px; padding: .8rem 1rem;}}
div[data-testid="stMetricLabel"] {{color: #A8ADB5;}}
hr {{border-color: #262B33;}}
a {{color: {AMBER};}}
"""


def built_pages() -> list[tuple[str, str, str]]:
    """Pages whose file exists and is not empty (unfinished pages stay out of the menu)."""
    return [s for s in PAGE_SPECS if (ROOT / s[0]).exists() and (ROOT / s[0]).stat().st_size > 0]


def inject_theme() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="flare-brand">FLARE Intelligence</div>'
                f'<div class="flare-title">{title}</div>'
                f'<div class="flare-sub">{subtitle}</div>', unsafe_allow_html=True)


def sidebar_note() -> None:
    st.sidebar.divider()
    st.sidebar.caption("Data: NASA Physical Sciences Informatics, PSI-25 (BASS-II). "
                       "FLARE is an evidence-exploration tool, not a fire-risk predictor.")
    if st.sidebar.button("Reload data files"):
        st.cache_data.clear()
        st.rerun()


def doi_url(doi: str) -> str:
    return f"{DOI_BASE}{doi}" if doi else ""


@st.cache_data(show_spinner="Loading NASA data...")
def load_all() -> dict:
    """Load everything the pages need. Problems are collected in 'errors', never raised."""
    out = {"df": pd.DataFrame(), "study": {}, "pubs": pd.DataFrame(),
           "registry": load_source_registry(), "n_chunks": 0, "documents": [],
           "n_datasets": 0, "errors": []}
    try:
        out["df"] = clean_experiment_table(load_experiment_table())
    except (DataNotFoundError, ValueError, OSError) as exc:
        out["errors"].append(f"Experimental table: {exc}")
    try:
        fields = load_investigation()
        out["study"] = get_study_overview(fields)
        out["pubs"] = get_publications(fields)
    except (FileNotFoundError, KeyError, OSError, zipfile.BadZipFile) as exc:
        out["errors"].append(f"PSI-25 metadata: {exc}")
    chunks = load_chunks()
    out["n_chunks"] = len(chunks)
    out["documents"] = sorted({c["doc_title"] for c in chunks})
    out["n_datasets"] = count_imported_datasets(RAW_DIR)
    return out


def show_load_errors(data: dict) -> None:
    st.warning("No experiment data could be loaded, so nothing is shown here. "
               "No numbers are invented when data is missing.")
    for message in data.get("errors", []):
        st.text(message)
    st.markdown("Put the NASA files in `data/raw/bass-ii/` (see the README), then run "
                "`python scripts/check_data.py` and press **Reload data files** in the sidebar.")


def log_activity(text: str) -> None:
    """Record an action of this session (shown on the Overview page)."""
    log = st.session_state.setdefault("activity", [])
    if log and log[-1][1] == text:
        return
    log.append((datetime.now().strftime("%H:%M:%S"), text))
    del log[:-20]
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.experiment_manager import dataset_overview
from src.theme import (card, hero, module_grid, panel, panel_title, plot,
                       section_title, stat_cards, timeline)
from src.ui import PSI_URL, built_pages, doi_url, load_all, show_load_errors

data = load_all()
df, study, pubs = data["df"], data["study"], data["pubs"]

# image = astronaut picture saved in the project folder: assets/astronaut.png
hero("Turning NASA's Microgravity Combustion Research into",
     "AI-Powered Insights",
     "Explore flame behaviour, compare experiments, and discover key fire-safety insights "
     "for future space missions.",
     image="assets/astronaut.png")

card("About FLARE Intelligence",
     '<p class="desc">FLARE Intelligence brings together NASA\'s microgravity combustion records, starting with '
     'BASS-II aboard the International Space Station, and the documents around them, so that the '
     'evidence behind spacecraft fire-safety questions can be explored and checked. It is a research '
     'evidence tool, not a fire-risk predictor.</p>', "book", "blue")

if df.empty:
    show_load_errors(data)
    st.stop()

n_pubs = None if pubs.empty else len(pubs)
ov = dataset_overview(df, data["n_datasets"], n_pubs, len(data["documents"]))

section_title("At a glance", "", "activity")
stat_cards([
    ("flask", ov["n_experiments"], "Experiments", "Tests in the PSI-25 table", "orange"),
    ("database", ov["n_imported_datasets"], "Datasets", "Files in data/raw/bass-ii", "blue"),
    ("chart", ov["n_numeric_sensor_readings"], "Readings", "Numeric O2, CO2, CO", "purple"),
    ("book", ov["n_documents"], "Documents", "Processed documents", "green"),
    ("layers", n_pubs if n_pubs is not None else "Not available", "Publications", "Listed in PSI-25 metadata", "orange"),
])
st.caption("Imported datasets = CSV, Excel or JSON files found in data/raw/bass-ii. Numeric sensor readings = "
           "initial and final O2, CO2 and CO values that are numbers in the table (at most 6 per test). "
           "Publications listed = entries in the PSI-25 metadata, not all of them were read.")

st.write("")
left, right = st.columns([3, 2])
with left:
    with panel("tests"):
        panel_title("Tests per investigator", "chart", "orange")
        counts = pd.Series(ov["per_investigator"]).sort_values()
        fig = px.bar(x=counts.values, y=counts.index, orientation="h",
                     labels={"x": "Number of tests", "y": "Principal investigator (as in the table)"})
        fig.update_traces(marker_color="#F97316", hovertemplate="%{y}: %{x} tests<extra></extra>")
        plot(fig, height=320)
        st.caption("Source: PSI-25 experimental table (BASS-II).")
with right:
    years = ", ".join(str(y) for y in ov["years_in_table"])
    card("Data quality",
         f'<div class="bignum">{ov["n_experiments_with_flags"]}</div>'
         '<p class="desc">tests with data-quality flags</p>'
         f'<p class="desc" style="margin-top:.8rem">Years found in the table: {escape(years)}</p>'
         '<p class="desc">Flagged values are kept and marked, never removed or corrected.</p>',
         "shield", "green")
    st.write("")
    links = []
    if study.get("dataset_doi"):
        links.append('Dataset DOI (from PSI-25 metadata): '
                     f'<a href="{escape(doi_url(study["dataset_doi"]))}" target="_blank" rel="noopener">'
                     f'{escape(study["dataset_doi"])}</a>')
    links.append(f'<a href="{escape(PSI_URL)}" target="_blank" rel="noopener">PSI-25 page at NASA</a>')
    card("Source", "".join(f'<p class="desc">{x}</p>' for x in links), "globe", "purple")

st.write("")
activity = st.session_state.get("activity", [])
if activity:
    body = timeline(list(reversed(activity[-8:])))
else:
    body = '<div class="empty">No analysis activity in this session yet.</div>'
card("Recent analysis activity", body, "clock", "orange")

section_title("Modules", "", "layers")
modules = [s for s in built_pages() if s[1] != "Overview"]
if not modules:
    st.caption("No other modules are available yet.")
else:
    module_grid(modules, columns=3)
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src.experiment_manager import experiment_listing, get_experiment, search_experiments
from src.theme import card, header, panel, panel_title, section_title, stat_cards
from src.ui import PSI_URL, doi_url, load_all, log_activity, show_load_errors

data = load_all()
df, study, pubs, registry = data["df"], data["study"], data["pubs"], data["registry"]

header("Experiment Explorer",
       "Inspect individual BASS-II tests. Values are shown as written in the NASA table; "
       "our parsing and calculations are labelled.")
if df.empty:
    show_load_errors(data)
    st.stop()

# ---------------------------------------------------------------- filters
with panel("filters"):
    panel_title("Filter tests", "search", "orange")
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    text = c1.text_input("Search (test number, investigator, fuel text)")
    pis = c2.multiselect("Investigator", sorted(df["pi"].unique()))
    geoms = c3.multiselect("Geometry (our parsing)", sorted(df["geometry"].unique()))
    flagged_only = c4.checkbox("Only tests with data-quality flags")

filtered = search_experiments(df, text, pis, geoms)
if flagged_only:
    filtered = filtered[filtered["flag_count"] > 0]

st.write("")
stat_cards([
    ("flask", len(filtered), "Matching tests", f"of {len(df)} tests", "orange"),
    ("users", int(filtered["pi"].nunique()) if len(filtered) else 0, "Investigators", "in the current selection", "blue"),
    ("shield", int((filtered["flag_count"] > 0).sum()) if len(filtered) else 0, "Flagged tests",
     "with data-quality flags", "red"),
])
if filtered.empty:
    st.info("No tests match these filters.")
    st.stop()

# ---------------------------------------------------------------- listing
section_title("Matching tests", "click a column header to sort", "layers")
listing = experiment_listing(filtered).rename(columns={
    "test_id": "Test", "pi": "Investigator", "date_raw": "Date (as written)",
    "fuel_text": "Fuel description", "geometry": "Geometry (our parsing)",
    "o2_initial_pct": "Initial O2 (%)", "sensor_readings": "Sensor readings (of 6)",
    "flag_count": "Quality flags"})
st.dataframe(listing, hide_index=True)

# ---------------------------------------------------------------- one test
section_title("Inspect a test", "", "search")
labels = {r.test_id: f"{r.test_id}  |  {r.pi}  |  {r.fuel_text}" for r in filtered.itertuples()}
selected = st.selectbox("Select a test to inspect", list(labels), format_func=lambda t: labels[t])
record = get_experiment(df, selected, study)
log_activity(f"Inspected test {selected}")

st.write("")
card(f"Test {escape(str(selected))}",
     '<p class="desc">Measurements are sensor readings as reported by NASA. Sections marked '
     "'our parsing' or 'derived' are our own processing of the table.</p>", "flame", "orange")
st.write("")
flags = record["flat"].get("Quality flags", "None")
if flags != "None":
    st.warning(f"Data-quality flags: {flags}")

open_by_default = {"Identification", "Fuel", "Conditions", "Measurements (sensor readings)"}
for section, items in record["sections"].items():
    if section == "Study context":
        continue
    with st.expander(section, expanded=section in open_by_default):
        st.dataframe(pd.DataFrame(items, columns=["Item", "Value"]), hide_index=True)

st.write("")
flat_rows = [(s, i, v) for s, items in record["sections"].items() for i, v in items]
d1, d2 = st.columns(2)
with d1:
    st.download_button("Download this test (CSV)",
                       pd.DataFrame(flat_rows, columns=["Section", "Item", "Value"]).to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"flare_{selected}.csv", mime="text/csv", icon=":material/download:",
                       use_container_width=True)
with d2:
    st.download_button("Download the filtered tests (CSV, cleaned table)",
                       filtered.to_csv(index=False).encode("utf-8-sig"),
                       file_name="flare_filtered_tests.csv", mime="text/csv", icon=":material/download:",
                       use_container_width=True)

# ---------------------------------------------------------------- study context
section_title("Study context", "PSI-25 metadata", "book")
for key, title in [("objective", "Objectives"),
                   ("hypothesis", "Hypothesis (as stated by the investigators; not a result)"),
                   ("approach", "Approach")]:
    if study.get(key):
        with st.expander(title):
            st.write(study[key])

# ---------------------------------------------------------------- sources
section_title("Sources", "", "globe")
links = []
if study.get("dataset_doi"):
    links.append(f'Dataset DOI: <a href="{escape(doi_url(study["dataset_doi"]))}" target="_blank" rel="noopener">'
                 f'{escape(study["dataset_doi"])}</a>')
links.append(f'Original NASA page: <a href="{escape(PSI_URL)}" target="_blank" rel="noopener">PSI-25</a>')
card("References", "".join(f'<p class="desc">{x}</p>' for x in links), "globe", "purple")

st.write("")
wanted = ["title", "type", "identifier", "status", "url"]
if not registry.empty and all(c in registry.columns for c in wanted):
    st.dataframe(registry[wanted], hide_index=True,
                 column_config={"url": st.column_config.LinkColumn("URL")})
if not pubs.empty:
    with st.expander(f"Publications listed in the PSI-25 metadata ({len(pubs)})"):
        shown = pubs.assign(doi_link=pubs["doi"].map(doi_url))
        st.dataframe(shown[["title", "authors", "doi_link", "link"]], hide_index=True,
                     column_config={"doi_link": st.column_config.LinkColumn("DOI link"),
                                    "link": st.column_config.LinkColumn("Other link")})
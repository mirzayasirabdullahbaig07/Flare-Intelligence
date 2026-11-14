import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import math

import plotly.express as px
import streamlit as st

from src.comparison import GENERAL_NOTES, chart_data, compare_experiments
from src.flame_analysis import VARIABLES, prepare_analysis_frame
from src.theme import card, header, insight, panel, panel_title, plot, section_title, stat_cards
from src.ui import load_all, log_activity, show_load_errors

# brand colours for the charts (orange first, then blue / purple / green / red / yellow / grey)
PALETTE = ["#F97316", "#3B82F6", "#8B5CF6", "#10B981", "#EF4444", "#EAB308", "#64748B"]
CHART_OPTIONS = ["delta_o2_pct", "delta_co2_pct", "delta_co_ppm", "o2_initial_pct",
                 "o2_final_pct", "co2_final_pct", "co_final_ppm"]
DEFAULT_CHART = ["delta_o2_pct", "delta_co2_pct", "delta_co_ppm"]

data = load_all()
df, study = data["df"], data["study"]
header("Experiment Comparison",
       "Compare selected BASS-II tests side by side. Missing values are shown as 'Not available' "
       "and are never filled in.")
if df.empty:
    show_load_errors(data)
    st.stop()

# ---------------------------------------------------------------- choose tests
labels = {r.test_id: f"{r.test_id} | {r.pi} | {r.fuel_text}" for r in df.itertuples()}
default = [t for t in ("B1", "M1", "O1") if t in labels]
with panel("choose"):
    panel_title("Choose tests to compare", "scale", "orange")
    selected = st.multiselect("Select two or more tests (the pre-selection is only an example)",
                              list(labels), default=default, format_func=lambda t: labels[t],
                              max_selections=8)
if len(selected) < 2:
    st.info("Select at least two tests to compare.")
    st.stop()

result = compare_experiments(df, selected, study)
if result["missing_ids"]:
    st.warning("Not found: " + ", ".join(result["missing_ids"]))
log_activity("Compared tests " + ", ".join(selected))

general = set(GENERAL_NOTES)
warnings = [n for n in result["notes"] if n not in general]
infos = [n for n in result["notes"] if n in general]

st.write("")
n_pi = int(df[df["test_id"].isin(selected)]["pi"].nunique()) if "pi" in df.columns else 0
stat_cards([
    ("scale", len(selected), "Tests compared", "of up to 8", "orange"),
    ("users", n_pi, "Investigators", "behind these tests", "blue"),
    ("shield", len(warnings), "Warnings", "to read before comparing", "red" if warnings else "green"),
])

if study.get("objective"):
    st.write("")
    with st.expander("Research objective of the investigation (PSI-25 metadata, the same for every test)"):
        st.write(study["objective"])

# ---------------------------------------------------------------- notes
section_title("Notes before reading the comparison", "", "bulb")
for note in warnings:
    st.warning(note)
if infos:
    card("General notes",
         "".join(insight("bulb", escape(str(n)), "orange", i) for i, n in enumerate(infos)),
         "book", "orange")

# ---------------------------------------------------------------- table
section_title("Side-by-side table", "", "layers")
st.dataframe(result["table"])
st.download_button("Download the comparison (CSV)",
                   result["table"].to_csv().encode("utf-8-sig"),
                   file_name="flare_comparison.csv", mime="text/csv", icon=":material/download:")
st.caption("Observed findings from the documents are on the Findings page; the experimental table itself "
           "contains no findings.")

# ---------------------------------------------------------------- chart
section_title("Chart", "", "chart")
picked = st.multiselect("Variables to chart", CHART_OPTIONS, default=DEFAULT_CHART,
                        format_func=lambda c: f"{VARIABLES[c]['label']} ({VARIABLES[c]['unit']})")
if not picked:
    st.info("Select at least one variable.")
    st.stop()
chart, missing = chart_data(prepare_analysis_frame(df), selected, picked)
if chart.empty:
    st.info("None of the selected tests has numeric values for these variables.")
else:
    chart["panel"] = chart["label"] + " [" + chart["unit"] + "]"
    fig = px.bar(chart, x="test_id", y="value", color="test_id", facet_col="panel", facet_col_wrap=2,
                 color_discrete_sequence=PALETTE,
                 labels={"value": "Value", "test_id": "Test"})
    fig.update_yaxes(matches=None, showticklabels=True)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=", 1)[-1]))
    rows = math.ceil(chart["panel"].nunique() / 2)
    fig.update_layout(showlegend=False)
    plot(fig, height=max(360, 300 * rows))
    st.caption("Each panel has its own scale. 'Derived' panels are our calculation (final minus initial), "
               "not NASA measurements. O2 values outside our screening range are hidden.")
if missing:
    st.caption("Not available for the chart: " + "; ".join(missing))
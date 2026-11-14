import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.flame_analysis import (CATEGORICAL, CORRELATION_CAVEATS, DATA_LIMITATIONS,
                                UNAVAILABLE_VARIABLES, VARIABLES, apply_filters,
                                available_variables, correlate, group_summary,
                                prepare_analysis_frame)
from src.theme import card, header, insight, panel, panel_title, plot, section_title, stat_cards
from src.ui import load_all, log_activity, show_load_errors

# brand colours for the charts (orange first, then blue / purple / green / red / yellow / grey)
PALETTE = ["#F97316", "#3B82F6", "#8B5CF6", "#10B981", "#EF4444", "#EAB308", "#64748B"]


def color_name(c):
    return "None" if c == "None" else CATEGORICAL[c]


data = load_all()
df = data["df"]
header("Flame Analytics",
       "Gas readings and fuel conditions of the BASS-II tests. Only variables that exist in the "
       "NASA table are shown; derived and parsed values are labelled.")
if df.empty:
    show_load_errors(data)
    st.stop()

adf = prepare_analysis_frame(df)
variables = available_variables(adf)
shown = variables[variables["shown"]]
labels = {r.column: f"{r.label} ({r.unit})" for r in shown.itertuples()}
keys = list(labels)
color_options = ["None"] + list(CATEGORICAL)


def default_index(name):
    return keys.index(name) if name in keys else 0


# ---------------------------------------------------------------- filters
o2_series = adf["o2_initial_pct"].dropna()
with panel("filters"):
    panel_title("Filters", "search", "orange")
    f1, f2, f3 = st.columns(3)
    pis = f1.multiselect("Investigator", sorted(adf["pi"].unique()))
    geoms = f2.multiselect("Geometry (our parsing)", sorted(adf["geometry"].unique()))
    mats = f3.multiselect("Material (our parsing)", sorted(adf["material"].unique()))
    o2_arg = None
    if not o2_series.empty and o2_series.min() < o2_series.max():
        lo, hi = float(o2_series.min()), float(o2_series.max())
        chosen = st.slider("Initial O2 (% by volume)", lo, hi, (lo, hi))
        if chosen != (lo, hi):
            o2_arg = chosen

sel = apply_filters(adf, pis=pis or None, materials=mats or None,
                    geometries=geoms or None, o2_initial_range=o2_arg)

st.write("")
stat_cards([
    ("flask", len(sel), "Tests selected", f"of {len(adf)} tests", "orange"),
    ("users", int(sel["pi"].nunique()) if len(sel) else 0, "Investigators", "in the selection", "blue"),
    ("chart", len(shown), "Variables", "shown in the charts", "purple"),
])
st.caption("Source: PSI-25 experimental table (BASS-II). O2 values outside our screening range are "
           "hidden from the charts (they stay in the table, flagged).")
if sel.empty:
    st.info("No tests match these filters.")
    st.stop()
if sel["pi"].nunique() > 1 or sel["geometry"].nunique() > 1:
    st.warning("This selection mixes investigators and/or fuel geometries. Those tests were run for "
               "different purposes, so patterns across them can reflect the mix and not one cause.")
log_activity(f"Flame Analytics: {len(sel)} tests selected")

st.write("")
t1, t2, t3, t4, t5, t6, t7 = st.tabs(["Variables", "Distribution", "Scatter",
                                      "Initial to final", "Groups", "Correlation", "Limits"])

with t1:
    rows = []
    for r in variables.itertuples():
        rows.append({"Variable": r.label, "Unit": r.unit, "Type": r.kind,
                     "Available (all tests)": r.n_available,
                     "Available (selection)": int(sel[r.column].notna().sum()),
                     "Shown in charts": "yes" if r.shown else "no (fewer than 5 values)",
                     "Note": r.note})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    export_cols = [c for c in ["test_id", "pi", "fuel_text", "geometry", "material", "thickness_um",
                               "rod_diameter_mm", "o2_initial_pct", "o2_final_pct", "co2_initial_pct",
                               "co2_final_pct", "co_initial_ppm", "co_final_ppm", "delta_o2_pct",
                               "delta_co2_pct", "delta_co_ppm", "quality_flags"] if c in sel.columns]
    st.download_button("Download the selected tests (CSV)",
                       sel[export_cols].to_csv(index=False).encode("utf-8-sig"),
                       file_name="flare_analysis_selection.csv", mime="text/csv",
                       icon=":material/download:")

with t2:
    s1, s2 = st.columns(2)
    col = s1.selectbox("Variable", keys, format_func=lambda c: labels[c], key="dist_var")
    color_by = s2.selectbox("Colour by", color_options, format_func=color_name, key="dist_color")
    d = sel.dropna(subset=[col])
    if d.empty:
        st.info("No values for this variable in the selection.")
    else:
        fig = px.histogram(d, x=col, nbins=20, color=None if color_by == "None" else color_by,
                           color_discrete_sequence=PALETTE, labels={col: labels[col]})
        plot(fig, height=420)
        st.caption(f"n = {len(d)} tests. {VARIABLES[col]['kind']}. {VARIABLES[col]['note']}")

with t3:
    c1, c2, c3 = st.columns(3)
    x = c1.selectbox("X axis", keys, index=default_index("o2_initial_pct"),
                     format_func=lambda c: labels[c], key="sc_x")
    y = c2.selectbox("Y axis", keys, index=default_index("delta_co_ppm"),
                     format_func=lambda c: labels[c], key="sc_y")
    color_by = c3.selectbox("Colour by", color_options, index=1, format_func=color_name, key="sc_color")
    d = sel.dropna(subset=[x, y])
    if x == y:
        st.info("Choose two different variables.")
    elif d.empty:
        st.info("No tests have both values in the selection.")
    else:
        fig = px.scatter(d, x=x, y=y, color=None if color_by == "None" else color_by,
                         hover_name="test_id", hover_data={"pi": True, "fuel_text": True},
                         color_discrete_sequence=PALETTE, labels={x: labels[x], y: labels[y]})
        fig.update_traces(marker=dict(size=10, line=dict(width=1, color="#FFFFFF")))
        plot(fig, height=420)
        st.caption(f"n = {len(d)} tests. Each point is one test. Pooling different fuels and investigators "
                   "can create or hide patterns; use the filters above to look at one group.")
        st.write(correlate(sel, x, y)["message"])

with t4:
    gas = st.radio("Gas", ["O2", "CO2", "CO"], horizontal=True, key="slope_gas")
    cols = {"O2": ("o2_initial_pct", "o2_final_pct", "% by volume"),
            "CO2": ("co2_initial_pct", "co2_final_pct", "% by volume"),
            "CO": ("co_initial_ppm", "co_final_ppm", "ppm")}
    ci, cf, unit = cols[gas]
    both = sel.dropna(subset=[ci, cf])
    options = both["test_id"].tolist()
    picked = st.multiselect("Tests (up to 12)", options, default=options[:8],
                            max_selections=12, key="slope_tests")
    if not picked:
        st.info("No tests with both an initial and a final reading are selected.")
    else:
        part = both[both["test_id"].isin(picked)]
        long = pd.concat([
            part[["test_id", ci]].rename(columns={ci: "value"}).assign(reading="Initial"),
            part[["test_id", cf]].rename(columns={cf: "value"}).assign(reading="Final")])
        fig = px.line(long, x="reading", y="value", color="test_id", markers=True,
                      category_orders={"reading": ["Initial", "Final"]},
                      color_discrete_sequence=PALETTE, labels={"value": f"{gas} ({unit})", "reading": ""})
        plot(fig, height=420)
        st.caption("Each line connects exactly two sensor readings, one before and one after the test. "
                   "The table has no readings in between, so the lines say nothing about how the values "
                   "changed during the burn.")

with t5:
    c1, c2 = st.columns(2)
    value = c1.selectbox("Value", keys, index=default_index("delta_co_ppm"),
                         format_func=lambda c: labels[c], key="grp_value")
    group = c2.selectbox("Group by", list(CATEGORICAL), format_func=lambda c: CATEGORICAL[c], key="grp_by")
    d = sel.dropna(subset=[value]).copy()
    d[group] = d[group].astype(str).replace("", "n/a")
    if d.empty:
        st.info("No values for this variable in the selection.")
    else:
        fig = px.box(d, x=group, y=value, color=group, points="all", hover_name="test_id",
                     color_discrete_sequence=PALETTE, labels={value: labels[value], group: CATEGORICAL[group]})
        fig.update_layout(showlegend=False)
        plot(fig, height=420)
        summary = group_summary(sel, group, value).rename(columns={
            "group": "Group", "n": "n", "median": "Median", "q1": "25th percentile",
            "q3": "75th percentile", "minimum": "Minimum", "maximum": "Maximum", "small_n": "Fewer than 3 tests"})
        st.dataframe(summary, hide_index=True)
        st.caption("Groups are different experiments (different fuels, geometries and aims). A higher median "
                   "means those tests had higher readings, not that the material is more or less dangerous.")

with t6:
    c1, c2 = st.columns(2)
    cx = c1.selectbox("Variable X", keys, index=default_index("o2_initial_pct"),
                      format_func=lambda c: labels[c], key="corr_x")
    cy = c2.selectbox("Variable Y", keys, index=default_index("delta_co_ppm"),
                      format_func=lambda c: labels[c], key="corr_y")
    res = correlate(sel, cx, cy)
    if res["status"] == "ok":
        st.write(res["message"])
    else:
        st.info(res["message"])
    by = st.radio("Check the same pair within each", ["geometry", "pi"], horizontal=True,
                  format_func=lambda c: CATEGORICAL[c], key="corr_by")
    rows = []
    for name, sub in sel.groupby(by):
        r2 = correlate(sub, cx, cy)
        rows.append({CATEGORICAL[by]: name, "n": r2["n"],
                     "Spearman rho": None if r2["rho"] is None else round(r2["rho"], 2),
                     "p-value": None if r2["p_value"] is None else round(r2["p_value"], 3),
                     "Result": "computed" if r2["status"] == "ok" else r2["message"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.write("")
    card("Read with care",
         "".join(insight("shield", escape(str(c)), "orange", i) for i, c in enumerate(CORRELATION_CAVEATS)),
         "bulb", "orange")

with t7:
    section_title("Not available in the imported dataset", "", "database")
    st.dataframe(pd.DataFrame(UNAVAILABLE_VARIABLES).rename(columns={"variable": "Variable", "reason": "Why"}),
                 hide_index=True)
    section_title("Data limitations", "", "shield")
    st.dataframe(pd.DataFrame(DATA_LIMITATIONS).rename(columns={"text": "Limitation", "source": "Source"}),
                 hide_index=True)
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src.ranking import CATEGORY_MEANING, load_findings
from src.theme import badge, card, header, panel, panel_title, section_title, stat_cards
from src.ui import load_all, log_activity


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def h(s: str) -> str:
    """Collapse multi-line html so Streamlit never treats it as a code block."""
    return "".join(line.strip() for line in s.splitlines())


data = load_all()
df, study, registry = data["df"], data["study"], data["registry"]
findings, load_warnings = load_findings()
for message in load_warnings:
    st.warning(message)
if not findings.empty:
    findings = findings.assign(category=findings["category"].str.strip().str.lower())


def source_lines(source_ids, registry):
    lines = []
    for sid in [s.strip() for s in str(source_ids).split(";") if s.strip()]:
        match = registry[registry["source_id"] == sid] if not registry.empty else registry
        if match.empty:
            lines.append(f"{sid} (not in the source registry)")
        else:
            r = match.iloc[0]
            lines.append(f"[{r['title']}]({r['url']}) ({r['identifier']})" if r["url"]
                         else f"{r['title']} ({r['identifier']})")
    return lines or ["No source listed"]


def show_findings(subset, empty_text):
    if subset.empty:
        st.caption(empty_text)
        return
    for r in subset.itertuples():
        with st.expander(f"{r.finding_id} | {r.title}"):
            st.write(r.statement)
            st.caption(f"Where in the source: {r.locations or 'Not available'}")
            st.markdown("Sources: " + "; ".join(source_lines(r.source_ids, registry)))
            if r.limitations:
                st.markdown(f"**Limits of this evidence:** {r.limitations}")
            st.caption(f"Review status: {r.review_status or 'Not available'}")


def in_category(*names):
    if findings.empty:
        return findings
    return findings[findings["category"].isin(names)]


def finding_titles(ids):
    if findings.empty:
        return []
    found = findings[findings["finding_id"].isin(ids)]
    return [f"{r.finding_id} ({r.category}): {r.title}" for r in found.itertuples()]


def count_of(name: str) -> int:
    return 0 if findings.empty else int((findings["category"] == name).sum())


def topic_card(t: dict, icon_name: str, tint: str, delay: float):
    evidence = "".join(f"<li>{esc(line)}</li>" for line in t["evidence"])
    related = finding_titles(t["findings"])
    related_html = ""
    if related:
        related_html = ('<div style="margin:.6rem 0 .2rem;font-size:.8rem;color:var(--muted)">Related findings</div>'
                        + "".join(badge(x) for x in related))
    body = h(f"""
        <div style="font-size:.8rem;color:var(--muted);margin-bottom:.2rem">What the sources state</div>
        <ul style="margin:0 0 .4rem;padding-left:1.1rem;font-size:.88rem;line-height:1.5">{evidence}</ul>
        {related_html}
        <div style="margin-top:.8rem;padding:.7rem .9rem;border-radius:12px;background:var(--accent-soft);
        border-left:3px solid var(--accent);font-size:.85rem;line-height:1.45">
        <b>Why this may not transfer.</b> {esc(t['limits'])}</div>""")
    card(esc(t["topic"]), body, icon_name, tint, delay=delay)


# ----------------------------------------------------------------------------
# Page
# ----------------------------------------------------------------------------
header("Moon and Mars Mission Insights",
       "What the BASS-II research reports, how it has been interpreted, and what it may mean for "
       "future missions. These three kinds of statement are kept apart on purpose.")
st.warning("BASS-II was run in microgravity aboard the International Space Station. Microgravity experiments "
           "do not automatically represent lunar gravity, Martian gravity or every spacecraft environment. "
           "Nothing here is a risk assessment or a fire-probability estimate.")
log_activity("Opened Mission Insights")

o2_text = "Not available"
if not df.empty and df["o2_initial_pct"].notna().any():
    o2 = df["o2_initial_pct"].dropna()
    o2_text = f"{o2.min():g} to {o2.max():g} % by volume"

stat_cards([
    ("search", count_of("observation"), "Observations", "reported in the documents", "orange"),
    ("bulb", count_of("interpretation"), "Interpretations", "how authors read the data", "blue"),
    ("flask", count_of("hypothesis"), "Hypotheses", "stated, not results", "purple"),
    ("shield", count_of("limitation"), "Limitations", "documented in the sources", "red"),
])

st.write("")
t1, t2, t3, t4 = st.tabs(["1. Direct observations", "2. Scientific interpretation",
                          "3. Potential mission implications", "Limits"])

# ---------- 1. Observations ----------
with t1:
    st.caption(CATEGORY_MEANING["observation"])
    with panel("obs_table"):
        panel_title("From the experimental table (PSI-25)", "database", "orange")
        if df.empty:
            st.info("The experimental table is not loaded.")
        else:
            st.write(f"- {len(df)} tests by {df['pi'].nunique()} investigators, all in microgravity aboard the ISS "
                     "(PSI-25 metadata).")
            st.write(f"- Initial O2 in the tests ranged over {o2_text}.")
            st.write("- Each test has one initial and one final reading of O2, CO2 and CO. There is no continuous "
                     "record in the table.")
    section_title("Observations reported in the documents", "", "search")
    show_findings(in_category("observation"), "No observations are listed in research/findings.csv.")
    st.caption("Ratings and review status come from research/findings.csv; 'draft' means the team has not "
               "reviewed them yet.")

# ---------- 2. Interpretation ----------
with t2:
    st.caption(CATEGORY_MEANING["interpretation"])
    section_title("Interpretations", "what the authors conclude from the data", "bulb")
    show_findings(in_category("interpretation"), "No interpretations are listed in research/findings.csv.")
    section_title("Stated hypothesis", "not a result", "flask")
    show_findings(in_category("hypothesis"), "No hypothesis is listed.")
    if study.get("hypothesis"):
        with st.expander("Hypothesis as written in the PSI-25 metadata"):
            st.write(study["hypothesis"])

# ---------- 3. Mission implications ----------
with t3:
    st.info("This tab is the most uncertain. Each card says what the loaded sources state, what is "
            "not covered, and links to the findings behind it. The wording of the cards was written by "
            "the FLARE team from the sources named; it is not NASA text.")
    if study.get("research_impacts"):
        with panel("impacts"):
            panel_title("The PSI-25 record's own statement of research impact", "rocket", "green")
            st.write(study["research_impacts"])
    if study.get("objective"):
        with st.expander("Objectives stated in the PSI-25 metadata"):
            st.write(study["objective"])

    topics = [
        {"topic": "Lunar habitats",
         "evidence": ["All BASS-II tests were run in microgravity aboard the ISS (PSI-25 metadata).",
                      f"Initial O2 in the tests: {o2_text}."],
         "findings": [],
         "limits": "No BASS-II test was run at lunar gravity, so the data do not show how these flames behave "
                   "there. The atmosphere of a habitat may differ from the atmospheres that were tested."},
        {"topic": "Mars habitats",
         "evidence": ["All BASS-II tests were run in microgravity aboard the ISS (PSI-25 metadata).",
                      f"Initial O2 in the tests: {o2_text}."],
         "findings": [],
         "limits": "No BASS-II test was run at Martian gravity. Habitat pressure and oxygen level are design "
                   "choices that the loaded sources do not discuss."},
        {"topic": "Spacecraft interiors",
         "evidence": ["Small samples (PMMA, SIBAL fabric, Nomex, a candle) were burned in a small flow duct "
                      "inside the Microgravity Science Glovebox (BASS-II data FAQ, PSI-25 metadata)."],
         "findings": ["F-LOWFLOW", "F-QUENCH-FABRIC"],
         "limits": "Real interiors contain other materials, sizes, ventilation patterns and ignition sources. "
                   "Small samples in a duct do not describe the fire behaviour of a whole compartment."},
        {"topic": "Crew safety",
         "evidence": ["The PSI-25 record states that a primary goal of BASS-II is improved spacecraft fire "
                      "safety (Research Impacts)."],
         "findings": ["F-LOWFLOW", "F-CRIT-VELOCITY"],
         "limits": "These are research observations of flames in a test duct. They are not an assessment of "
                   "risk to a crew, and this app does not estimate fire probability or consequences."},
        {"topic": "Material selection",
         "evidence": ["The investigators' hypothesis is that NASA's upward-burning test (NASA-STD-6001 Test 1) "
                      "may not be conservative for flammability in space (PSI-25 metadata).",
                      "Tested materials include PMMA, SIBAL fabric, Nomex III and a wax candle (BASS-II data FAQ)."],
         "findings": ["H-MICROG-HYPOTHESIS", "F-THICK-SPREAD"],
         "limits": "The hypothesis is a stated question, not a result. The loaded findings do not rank materials "
                   "by safety, and behaviour in these tests does not certify a material for use."},
        {"topic": "Fire detection and suppression research",
         "evidence": ["The PSI-25 objectives say BASS-II results contribute to the combustion computational "
                      "models used in designing fire detection and suppression systems.",
                      "O2, CO2 and CO were read before and after each test (experimental table)."],
         "findings": ["I-GLOBAL-STOICH", "L-MODEL-OVERPREDICT"],
         "limits": "The table has no columns for detector response or suppression agents. Gas readings exist at "
                   "two moments per test only, and one model discussed in the Summary Report predicted much "
                   "higher spread rates than were measured."},
    ]
    topic_icons = ["globe", "rocket", "layers", "shield", "flask", "zap"]
    topic_tints = ["orange", "blue", "purple", "green", "orange", "blue"]

    section_title("Topic by topic", "what the sources support, and where they stop", "layers")
    for start in range(0, len(topics), 2):
        cols = st.columns(2)
        for j, t in enumerate(topics[start:start + 2]):
            i = start + j
            with cols[j]:
                topic_card(t, topic_icons[i], topic_tints[i], delay=i * 0.06)
        st.write("")

# ---------- Limits ----------
with t4:
    limits = [
        "BASS-II ran in microgravity. Partial-gravity (lunar, Martian) behaviour is not covered by these data.",
        "Test samples were small and few materials were used.",
        "Sensor readings are initial and final values, not time series.",
        "Findings come from documents the team has read only in part; ratings marked 'draft' are unreviewed.",
        "SAFFIRE (large-scale fires in a spacecraft) is not loaded yet, so its results are not used.",
        "Statements about missions are considerations raised by the sources, not conclusions or recommendations.",
    ]
    with panel("limits_list"):
        panel_title("Limits of this module", "shield", "red")
        for line in limits:
            st.markdown(f"- {line}")
    if not findings.empty:
        section_title("Documented limitations from the sources", "", "book")
        show_findings(in_category("limitation"), "No limitations are listed.")
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ranking import CATEGORY_MEANING, CRITERIA, criteria_table, load_findings, score_findings
from src.theme import badge, card, header, insight, panel, panel_title, plot, section_title, stat_cards
from src.ui import load_all, log_activity

# Brand colours (same order as the theme colorway), one per criterion
PALETTE = ["#F97316", "#3B82F6", "#8B5CF6", "#10B981", "#EAB308"]
SHORT = {"relevance": "Relevance", "evidence": "Evidence strength", "measurable": "Measurable data",
         "applicability": "Mission applicability", "sources": "Supporting sources"}


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def h(s: str) -> str:
    """Collapse multi-line html so Streamlit never treats it as a code block."""
    return "".join(line.strip() for line in s.splitlines())


def reset_weights() -> None:
    for key in CRITERIA:
        st.session_state[f"w_{key}"] = 1.0


def level_of(row, key: str) -> int:
    return min(int(row["sources_n"]), 3) if key == "sources" else int(row[key])


def show_sources(source_ids: str, registry: pd.DataFrame) -> None:
    ids = [s.strip() for s in str(source_ids).split(";") if s.strip()]
    if not ids:
        st.write("No source listed.")
    for sid in ids:
        match = registry[registry["source_id"] == sid] if not registry.empty else registry
        if match.empty:
            st.write(f"- {sid} (not in the source registry)")
            continue
        r = match.iloc[0]
        name = f"[{r['title']}]({r['url']})" if r["url"] else r["title"]
        st.markdown(f"- {name} ({r['identifier']}; status: {r['status']})")


# ----------------------------------------------------------------------------
# Page
# ----------------------------------------------------------------------------
data = load_all()
registry = data["registry"]

header("Findings Ranking",
       "Documented findings, ordered by a transparent evidence score you can inspect and reweight.")
st.warning("This ranks how well a finding is documented and how relevant it is to spacecraft fire safety. "
           "It is not a fire-risk or fire-probability prediction and not a certified assessment.")

findings, load_warnings = load_findings()
for message in load_warnings:
    st.warning(message)
if findings.empty:
    st.info("No findings are loaded. They are listed in research/findings.csv.")
    st.stop()

# ---------- Scoring weights ----------
with st.expander("Scoring weights", expanded=False):
    cols = st.columns(len(CRITERIA))
    weights = {}
    for col, (key, meta) in zip(cols, CRITERIA.items()):
        weights[key] = col.slider(SHORT[key], 0.0, 3.0, 1.0, 0.5, key=f"w_{key}", help=meta["label"])
    st.button("Reset to equal weights", on_click=reset_weights)
    st.caption("Score = 100 x sum(weight x level) / (3 x sum of weights). Each level runs from 0 to 3. "
               "All weights equal by default.")

table, notes = score_findings(findings, weights)
for note in notes:
    st.caption(note)
scored = table[table["status"] == "scored"]
others = table[table["status"] != "scored"]

# ---------- Summary cards ----------
n_draft = int(scored["review_status"].fillna("").astype(str).str.startswith("draft").sum()) if not scored.empty else 0
top_score = f"{scored['score'].max():.1f}" if not scored.empty else "N/A"
stat_cards([
    ("layers", len(table), "Findings", "listed in research/findings.csv", "orange"),
    ("shield", len(scored), "Scored", "complete set of ratings", "green"),
    ("star", top_score, "Top score", "out of 100", "blue"),
    ("bulb", n_draft, "Draft ratings", "not yet reviewed by the team", "purple"),
])

# ---------- Ranked findings ----------
section_title("Ranked findings", "ordered by evidence score", "trophy")
if scored.empty:
    st.info("No finding has a complete set of ratings yet.")
else:
    view = scored[["rank", "finding_id", "title", "category", "score", "supporting_experiment",
                   "sources_n", "review_status"]].rename(columns={
        "rank": "Rank", "finding_id": "ID", "title": "Finding", "category": "Category", "score": "Score (0-100)",
        "supporting_experiment": "Supporting experiment", "sources_n": "Sources (n)",
        "review_status": "Review status"})
    st.dataframe(view, hide_index=True)
    if scored["rank"].duplicated().any():
        st.caption("Findings with equal scores share a rank. The differences between them are small and "
                   "come from the ratings, which are judgements, not measurements.")
    if n_draft:
        st.warning("Ratings of findings marked 'draft' were proposed by the assistant and have not been reviewed "
                   "by the team. Treat the ranking as a starting point.")

    parts = [{"finding_id": r["finding_id"], "criterion": SHORT[key], "points": weights[key] * level_of(r, key)}
             for _, r in scored.iterrows() for key in CRITERIA]
    fig = px.bar(pd.DataFrame(parts), x="points", y="finding_id", color="criterion", orientation="h",
                 color_discrete_sequence=PALETTE,
                 category_orders={"finding_id": list(scored["finding_id"])[::-1]},
                 labels={"points": "Weighted points", "finding_id": "Finding", "criterion": "Criterion"})
    with panel("score_build"):
        panel_title("How each score is built", "chart", "blue")
        plot(fig, height=max(320, 42 * len(scored) + 120))
        st.caption("Each bar is the sum of the five criteria (level x weight).")

# ---------- Finding details ----------
section_title("Finding details", "pick a finding to inspect", "search")
labels = {r.finding_id: f"{r.finding_id} | {r.title}" for r in table.itertuples()}
selected = st.selectbox("Select a finding", list(labels), format_func=lambda f: labels[f])
row = table[table["finding_id"] == selected].iloc[0]
log_activity(f"Viewed finding {selected}")

category_note = CATEGORY_MEANING.get(row["category"], "Unknown category.")
review = row["review_status"] or "Not available"
head_body = h(f"""
    <div>{badge(row['category'])}{badge('Review: ' + str(review))}</div>
    <p class="desc" style="margin-top:.5rem">{esc(category_note)}</p>""")

top_l, top_r = st.columns([3, 1])
with top_l:
    card(esc(row["title"]), head_body, "flame", "orange", min_height=140)
with top_r:
    if row["status"] == "scored":
        score_body = h(f"""<div class="bignum">{esc(row['score'])}
            <span style="font-size:1rem;font-weight:600;color:var(--muted)"> / 100</span></div>
            <p class="desc">Evidence score</p>""")
        card("Ranking score", score_body, "trophy", "green", min_height=140)
    else:
        card("Ranking score", f'<p class="desc">Not scored ({esc(row["status"])}).</p>', "trophy", "red",
             min_height=140)

with panel("statement"):
    panel_title("Statement (as reported in the source)", "book", "purple")
    st.write(row["statement"])

c1, c2 = st.columns(2)
with c1:
    with panel("experiment"):
        panel_title("Supporting NASA experiment", "flask", "orange")
        st.write(row["supporting_experiment"] or "Not available")
        st.markdown("**Where in the sources**")
        st.write(row["locations"] or "Not available")
with c2:
    with panel("references"):
        panel_title("Supporting references", "database", "blue")
        show_sources(row["source_ids"], registry)

with panel("limits"):
    panel_title("Limitations of this evidence", "shield", "red")
    st.write(row["limitations"] or "None recorded.")

if row["status"] == "scored":
    with panel("breakdown"):
        panel_title("How this score was calculated", "scale", "green")
        rows = [{"Criterion": meta["label"], "Level (0-3)": level_of(row, key),
                 "Meaning of this level": meta["levels"][level_of(row, key)],
                 "Assigned by": meta["assigned_by"]} for key, meta in CRITERIA.items()]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption("Calculation: " + row["explanation"])
else:
    st.info(f"This item is not scored ({row['status']}). It is shown for context.")

# ---------- Shown but not scored ----------
if not others.empty:
    section_title("Shown but not scored", "context only", "layers")
    st.caption("Hypotheses, limitations and statements still awaiting review are listed for context. "
               "Scoring them next to experimental results would be misleading.")
    st.dataframe(others[["finding_id", "title", "category", "locations", "review_status"]].rename(columns={
        "finding_id": "ID", "title": "Item", "category": "Category", "locations": "Where in the sources",
        "review_status": "Review status"}), hide_index=True)

# ---------- Method ----------
section_title("Method", "", "bulb")
card("Reading this ranking",
     insight("star", "Five criteria, each rated from 0 to 3. Four are judgements recorded in research/findings.csv; "
                     "the fifth is calculated from the number of listed sources.", "orange", 0)
     + insight("shield", "Only observations and interpretations are scored. Hypotheses and limitations are "
                         "shown separately.", "blue", 1)
     + insight("bulb", "A high score means well documented and relevant. It does not mean a fire is likely.",
               "green", 2),
     "book", "orange")

with st.expander("Criteria and score formula"):
    st.dataframe(criteria_table(), hide_index=True)
    st.markdown("Score = 100 x sum(weight x level) / (3 x sum of weights). 'Supporting sources' counts listed "
                "sources; it does not prove that they are independent.")

st.download_button("Download the ranking table (CSV)", table.to_csv(index=False).encode("utf-8-sig"),
                   file_name="flare_findings_ranking.csv", mime="text/csv")
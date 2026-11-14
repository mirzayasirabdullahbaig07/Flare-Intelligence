"""Evidence ranking of documented findings.

This ranks how well a finding is documented and how relevant it is. It is NOT a fire-risk
or fire-probability prediction and must not be presented as one. Ratings are reviewer
judgements recorded in research/findings.csv; only the source count is calculated.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINDINGS_CSV = PROJECT_ROOT / "research" / "findings.csv"

REQUIRED_COLUMNS = ["finding_id", "title", "category", "statement", "supporting_experiment",
                    "source_ids", "locations", "relevance", "evidence", "measurable",
                    "applicability", "limitations", "review_status"]
RATING_COLUMNS = ["relevance", "evidence", "measurable", "applicability"]
SCORED_CATEGORIES = {"observation", "interpretation"}

CATEGORY_MEANING = {
    "observation": "Reported by a source as observed or measured in an experiment.",
    "interpretation": "Reported by a source as a scientific explanation of observations.",
    "hypothesis": "A stated hypothesis, not a result. Shown but not scored.",
    "limitation": "A documented limitation of the data or hardware. Shown but not scored.",
    "needs_review": "Statement copied from a document whose context has not been checked yet. Shown but not scored.",
}

CRITERIA = {
    "relevance": {"label": "Relevance to spacecraft fire safety", "assigned_by": "reviewer",
        "levels": {0: "No stated link to fire safety",
                   1: "General combustion science",
                   2: "Relates to material flammability or flame limits",
                   3: "Directly concerns spacecraft fire safety (ventilation, detection, suppression, material selection)"}},
    "evidence": {"label": "Strength of experimental evidence", "assigned_by": "reviewer",
        "levels": {0: "Hypothesis or claim without a reported test",
                   1: "Reported in a single presentation or abstract",
                   2: "Reported from BASS-II tests in a NASA report",
                   3: "Reported from tests and also supported by an independent peer-reviewed publication"}},
    "measurable": {"label": "Availability of measurable observations", "assigned_by": "reviewer",
        "levels": {0: "None", 1: "Qualitative description only",
                   2: "Quantitative values given in the documents",
                   3: "Quantitative values also in the app's imported dataset"}},
    "applicability": {"label": "Applicability to future missions", "assigned_by": "reviewer",
        "levels": {0: "None stated", 1: "Indirect", 2: "Relevant to spacecraft conditions",
                   3: "Mission conditions discussed explicitly"}},
    "sources": {"label": "Supporting sources (proxy for reproducibility)", "assigned_by": "calculated from source_ids",
        "levels": {0: "No source", 1: "One source", 2: "Two distinct sources",
                   3: "Three or more distinct sources (not necessarily independent)"}},
}
DEFAULT_WEIGHTS = {key: 1.0 for key in CRITERIA}


def count_sources(source_ids) -> int:
    parts = [p.strip() for p in str(source_ids if source_ids is not None else "").split(";")]
    return len({p for p in parts if p})


def parse_rating(value):
    text = str(value if value is not None else "").strip()
    return int(text) if text in {"0", "1", "2", "3"} else None


def normalise_weights(weights) -> tuple[dict, list[str]]:
    merged, notes = dict(DEFAULT_WEIGHTS), []
    for key, value in (weights or {}).items():
        if key not in merged:
            notes.append(f"Unknown criterion '{key}' ignored.")
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            notes.append(f"Weight for '{key}' is not a number; default used.")
            continue
        if number < 0:
            notes.append(f"Negative weight for '{key}' ignored.")
            continue
        merged[key] = number
    if sum(merged.values()) <= 0:
        notes.append("All weights were zero; equal weights are used.")
        merged = dict(DEFAULT_WEIGHTS)
    return merged, notes


def load_findings(path=FINDINGS_CSV) -> tuple[pd.DataFrame, list[str]]:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=REQUIRED_COLUMNS), [f"Findings file not found: {path}"]
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return pd.DataFrame(columns=REQUIRED_COLUMNS), [f"Findings file lacks columns: {missing}"]
    warnings = []
    unknown = sorted(set(df["category"].str.strip().str.lower()) - set(CATEGORY_MEANING))
    if unknown:
        warnings.append(f"Unknown categories (treated as not scored): {unknown}")
    duplicates = df["finding_id"][df["finding_id"].duplicated()].tolist()
    if duplicates:
        warnings.append(f"Duplicate finding_id values: {duplicates}")
    return df, warnings


def score_findings(df: pd.DataFrame, weights=None) -> tuple[pd.DataFrame, list[str]]:
    w, notes = normalise_weights(weights)
    total_w = sum(w.values())
    out_rows = []
    for _, r in df.iterrows():
        category = str(r["category"]).strip().lower()
        ratings = {c: parse_rating(r[c]) for c in RATING_COLUMNS}
        n_sources = count_sources(r["source_ids"])
        levels = {**ratings, "sources": min(n_sources, 3)}
        score, explanation = None, ""
        if category not in SCORED_CATEGORIES:
            status = f"not scored ({category or 'no category'})"
        elif any(v is None for v in ratings.values()):
            absent = [k for k, v in ratings.items() if v is None]
            status = "not rated (missing: " + ", ".join(absent) + ")"
        else:
            points = sum(w[k] * levels[k] for k in CRITERIA)
            score = round(100 * points / (3 * total_w), 1)
            status = "scored"
            explanation = (" + ".join(f"{k} {levels[k]}x{w[k]:g}" for k in CRITERIA)
                           + f" = {points:g} of {3 * total_w:g} -> {score}")
        out_rows.append({
            "finding_id": r["finding_id"], "title": r["title"], "category": category,
            "supporting_experiment": r["supporting_experiment"], "source_ids": r["source_ids"],
            "locations": r["locations"], "statement": r["statement"], "limitations": r["limitations"],
            "review_status": r["review_status"], **ratings, "sources_n": n_sources,
            "status": status, "score": score, "explanation": explanation})
    table = pd.DataFrame(out_rows)
    if table.empty:
        return table, notes
    table["rank"] = table["score"].rank(method="min", ascending=False)
    table = table.sort_values(["rank", "finding_id"], na_position="last").reset_index(drop=True)
    table["rank"] = table["rank"].astype("Int64")
    return table, notes


def criteria_table() -> pd.DataFrame:
    rows = []
    for key, meta in CRITERIA.items():
        row = {"criterion": key, "label": meta["label"], "assigned_by": meta["assigned_by"]}
        row.update({f"level_{n}": text for n, text in meta["levels"].items()})
        rows.append(row)
    return pd.DataFrame(rows)
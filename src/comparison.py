"""Side-by-side comparison of selected BASS-II experiments. Missing values stay 'Not available'."""
from __future__ import annotations

import pandas as pd

from src.experiment_manager import (NOT_AVAILABLE, SENSOR_COLUMNS, build_record, is_missing,
                                    sensor_completeness)
from src.flame_analysis import VARIABLES

SKIP_ROWS = {"Study objective (PSI-25 metadata)"}  # same for every test, shown once on the page
DEFAULT_CHART_COLUMNS = ["delta_o2_pct", "delta_co2_pct", "delta_co_ppm"]

GENERAL_NOTES = [
    "Gas values are one initial and one final reading per test, not time series. The table has no burn "
    "duration or burned fuel mass, so gas increases cannot be normalised or read as a measure of fire severity.",
    "Flame spread rate, flame length, temperature and extinction outcome are not columns of this table. "
    "See the Findings page for what the documents report.",
]


def _find_rows(df: pd.DataFrame, test_ids):
    rows, seen, missing = [], set(), []
    for tid in test_ids:
        key = str(tid).strip().upper()
        if key in seen:
            continue
        seen.add(key)
        match = df[df["test_id"].astype(str).str.strip().str.upper() == key] if not df.empty else df
        if match.empty:
            missing.append(str(tid))
        else:
            rows.append(match.iloc[0])
    return rows, missing


def _notes(rows) -> list[str]:
    notes = []
    if len(rows) < 2:
        notes.append("Select at least two experiments to compare.")
        return notes + GENERAL_NOTES

    pis = sorted({str(r.get("pi")) for r in rows})
    if len(pis) > 1:
        notes.append("These tests come from different investigators (" + ", ".join(pis)
                     + "), whose experiments had different aims (see 'Investigator focus').")
    geometries = sorted({str(r.get("geometry")) for r in rows})
    if len(geometries) > 1:
        notes.append("Different fuel geometries (our parsing): " + ", ".join(geometries) + ".")

    o2 = {str(r.get("test_id")): float(r.get("o2_initial_pct"))
          for r in rows if not is_missing(r.get("o2_initial_pct"))}
    if len(o2) >= 2 and max(o2.values()) - min(o2.values()) > 1.0:
        notes.append(f"Initial O2 differs by {max(o2.values()) - min(o2.values()):.1f} percentage points "
                     f"({min(o2.values()):g} to {max(o2.values()):g} %). Oxygen concentration is one of the "
                     "primary variables of BASS-II, so these tests were not run at the same oxygen level.")

    by_sample: dict[str, list[str]] = {}
    for r in rows:
        sid = str(r.get("sample_id", "")).strip()
        if sid:
            by_sample.setdefault(sid, []).append(str(r.get("test_id")))
    for sid, ids in by_sample.items():
        if len(ids) > 1:
            notes.append(f"Tests {', '.join(ids)} share sample number {sid}; per the FAQ some samples "
                         "were used for more than one run.")

    incomplete = [f"{r.get('test_id')} ({sensor_completeness(r)} of {len(SENSOR_COLUMNS)})"
                  for r in rows if sensor_completeness(r) < len(SENSOR_COLUMNS)]
    if incomplete:
        notes.append("Incomplete gas readings: " + ", ".join(incomplete) + ".")

    for r in rows:
        flags = "" if is_missing(r.get("quality_flags")) else str(r.get("quality_flags"))
        if flags:
            notes.append(f"Data-quality flags for {r.get('test_id')}: {flags}")
    return notes + GENERAL_NOTES


def compare_experiments(df: pd.DataFrame, test_ids, study: dict | None = None) -> dict:
    rows, missing = _find_rows(df, test_ids)
    if not rows:
        return {"table": pd.DataFrame(), "notes": ["None of the selected tests was found."],
                "missing_ids": missing}
    records = [build_record(r, study) for r in rows]
    labels = [l for l in records[0]["flat"] if l not in SKIP_ROWS]
    table = pd.DataFrame({rec["test_id"]: [rec["flat"].get(l, NOT_AVAILABLE) for l in labels]
                          for rec in records}, index=labels)
    return {"table": table, "notes": _notes(rows), "missing_ids": missing}


def chart_data(df: pd.DataFrame, test_ids, columns=None):
    """Long table of numeric values for plotting, plus the pairs that are missing."""
    columns = columns or DEFAULT_CHART_COLUMNS
    rows, _ = _find_rows(df, test_ids)
    records, missing = [], []
    for r in rows:
        for col in columns:
            meta = VARIABLES.get(col, {"label": col, "unit": "", "kind": ""})
            value = r.get(col)
            if is_missing(value):
                missing.append(f"{r.get('test_id')}: {meta['label']}")
                continue
            records.append({"test_id": str(r.get("test_id")), "variable": col, "label": meta["label"],
                            "unit": meta["unit"], "kind": meta["kind"], "value": float(value)})
    out = pd.DataFrame(records, columns=["test_id", "variable", "label", "unit", "kind", "value"])
    return out, missing
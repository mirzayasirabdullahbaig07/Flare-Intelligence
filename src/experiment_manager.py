"""Experiment records built from the PSI-25 (BASS-II) experimental table.

Every value comes from the table, the PSI-25 metadata or the BASS-II data FAQ.
Missing values are shown as "Not available"; nothing is filled in or estimated.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.preprocessing import O2_SCREEN_RANGE

NOT_AVAILABLE = "Not available"

GRAVITY_ENVIRONMENT = "Microgravity aboard the International Space Station (Microgravity Science Glovebox)"
GRAVITY_SOURCE = "PSI-25 investigation metadata"
DATASET_NAME = "PSI-25 experimental table (BASS-II)"

# From the BASS-II data FAQ ("Test Matrix explanation").
PI_FOCUS = {
    "Bhattacharjee": "Burned various thicknesses of very thin PMMA films.",
    "Ferkul": "Burned Nomex III fabric and a candle, to round out the earlier BASS-I testing.",
    "Miller": "Burned PMMA slabs of various thicknesses and widths (one-sided and two-sided burns).",
    "Olson": "Burned PMMA rods of three sizes (mostly clear), igniting the upstream end (stagnation flame, concurrent flow).",
    "Fernandez-Pello": "Burned PMMA rods of three sizes (mostly black), igniting the downstream end (opposed-flow flame spread).",
    "T'ien": "Burned mostly SIBAL fabric (75/25 cotton/fiberglass blend); also one sample (2 tests) of a 4 cm PMMA spherical section.",
}

FLOW_RESTRICTOR_MEANING = {
    0: "highest flow, lowest restriction",
    1: "between settings 0 and 2 (not described separately in the FAQ)",
    2: "lowest flow, highest restriction",
}

# (numeric column, raw text column, label, unit)
SENSOR_COLUMNS = [
    ("o2_initial_pct", "o2_initial_raw", "Initial O2", "% by volume"),
    ("o2_final_pct", "o2_final_raw", "Final O2", "% by volume"),
    ("co2_initial_pct", "co2_initial_raw", "Initial CO2", "% by volume"),
    ("co2_final_pct", "co2_final_raw", "Final CO2", "% by volume"),
    ("co_initial_ppm", "co_initial_raw", "Initial CO", "ppm"),
    ("co_final_ppm", "co_final_raw", "Final CO", "ppm"),
]
DERIVED_COLUMNS = [
    ("delta_o2_pct", "O2 drop, initial minus final (derived)", "percentage points"),
    ("delta_co2_pct", "CO2 increase, final minus initial (derived)", "percentage points"),
    ("delta_co_ppm", "CO increase, final minus initial (derived)", "ppm"),
]


def is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _text(value) -> str:
    if is_missing(value):
        return NOT_AVAILABLE
    s = str(value).strip()
    return s if s else NOT_AVAILABLE


def display_value(numeric, raw="", unit: str = "") -> str:
    """Number with unit; else say what the source holds; else 'Not available'."""
    if not is_missing(numeric):
        return f"{float(numeric):g} {unit}".strip()
    raw_text = "" if is_missing(raw) else str(raw).strip()
    if raw_text:
        return f"not numeric in source ('{raw_text}')"
    return NOT_AVAILABLE


def sensor_completeness(row) -> int:
    """How many of the 6 gas readings are numeric for this test."""
    return sum(0 if is_missing(row.get(num)) else 1 for num, _, _, _ in SENSOR_COLUMNS)


def _flow_text(row) -> str:
    flow = row.get("flow_restrictor")
    if is_missing(flow):
        return display_value(None, row.get("flow_restrictor_raw"))
    value = float(flow)
    meaning = FLOW_RESTRICTOR_MEANING.get(int(value)) if value.is_integer() else None
    return f"{int(value)} ({meaning})" if meaning else f"{value:g}"


def _flagged_sensor_value(row, num, raw, unit) -> str:
    text = display_value(row.get(num), row.get(raw), unit)
    if num in ("o2_initial_pct", "o2_final_pct") and not is_missing(row.get(num)):
        lo, hi = O2_SCREEN_RANGE
        if not (lo <= float(row.get(num)) <= hi):
            text += " [flagged: outside our screening range, possible data-entry error]"
    return text


def build_record(row, study: dict | None = None) -> dict:
    """One experiment as labelled sections. 'flat' maps every label to its value."""
    study = study or {}
    pi = _text(row.get("pi"))
    flags = "" if is_missing(row.get("quality_flags")) else str(row.get("quality_flags"))

    sections = {
        "Identification": [
            ("Test number", _text(row.get("test_id"))),
            ("Investigator", pi),
            ("Investigator focus (BASS-II data FAQ)", PI_FOCUS.get(pi, NOT_AVAILABLE)),
            ("Test date (as written in the table)", _text(row.get("date_raw"))),
            ("Sample number", _text(row.get("sample_id"))),
        ],
        "Study context": [
            ("Study objective (PSI-25 metadata)", study.get("objective") or NOT_AVAILABLE),
        ],
        "Fuel": [
            ("Fuel description (as written)", _text(row.get("fuel_text"))),
            ("Material (our parsing)", _text(row.get("material"))),
            ("Geometry (our parsing)", _text(row.get("geometry"))),
            ("Thickness", display_value(row.get("thickness_um"), "", "micrometres")),
            ("Rod diameter (our conversion to mm)", display_value(row.get("rod_diameter_mm"), "", "mm")),
            ("Rod colour (our parsing)", _text(row.get("rod_color"))),
            ("Sides burned (only if stated)", display_value(row.get("sides"))),
        ],
        "Conditions": [
            ("Gravity environment", GRAVITY_ENVIRONMENT),
            ("Flow restrictor setting", _flow_text(row)),
            ("Fan display (as written)", _text(row.get("fan_display_raw"))),
            ("Air display (as written)", _text(row.get("air_display_raw"))),
            ("Radiometer gain (as written, uncalibrated)", _text(row.get("radiometer_gain_raw"))),
            ("Total camera frames shot (as written)", _text(row.get("total_frames_raw"))),
        ],
        "Measurements (sensor readings)": [
                        (label, _flagged_sensor_value(row, num, raw, unit))
            for num, raw, label, unit in SENSOR_COLUMNS
        ],
        "Derived values (our calculation)": [
            (label, display_value(row.get(col), "", unit)) for col, label, unit in DERIVED_COLUMNS
        ],
        "Data quality": [
            ("Sensor readings available", f"{sensor_completeness(row)} of {len(SENSOR_COLUMNS)}"),
            ("Quality flags", flags or "None"),
        ],
        "Source": [
            ("Dataset", DATASET_NAME),
            ("Dataset DOI (from PSI-25 metadata)", study.get("dataset_doi") or NOT_AVAILABLE),
            ("Gravity environment source", GRAVITY_SOURCE),
        ],
    }
    flat = {label: value for items in sections.values() for label, value in items}
    return {"test_id": _text(row.get("test_id")), "sections": sections, "flat": flat}


def get_experiment(df: pd.DataFrame, test_id: str, study: dict | None = None):
    if df.empty or "test_id" not in df.columns:
        return None
    key = str(test_id).strip().upper()
    match = df[df["test_id"].astype(str).str.strip().str.upper() == key]
    return None if match.empty else build_record(match.iloc[0], study)


def search_experiments(df: pd.DataFrame, text: str = "", pis=None, geometries=None,
                       materials=None) -> pd.DataFrame:
    if df.empty:
        return df
    out = df
    if pis:
        out = out[out["pi"].isin(pis)]
    if geometries:
        out = out[out["geometry"].isin(geometries)]
    if materials:
        out = out[out["material"].isin(materials)]
    text = (text or "").strip().lower()
    if text and not out.empty:
        hay = (out["test_id"].astype(str) + " " + out["pi"].astype(str) + " "
               + out["fuel_text"].astype(str) + " " + out["geometry"].astype(str)).str.lower()
        out = out[hay.str.contains(text, regex=False)]
    return out


def experiment_listing(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["test_id", "pi", "date_raw", "fuel_text", "geometry", "o2_initial_pct",
            "sensor_readings", "flag_count"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    out = df.copy()
    out["sensor_readings"] = out.apply(sensor_completeness, axis=1)
    return out[[c for c in cols if c in out.columns]].reset_index(drop=True)


def count_imported_datasets(directory, extensions=(".csv", ".xlsx", ".json")) -> int:
    folder = Path(directory)
    if not folder.exists():
        return 0
    return sum(1 for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in extensions)


def dataset_overview(df: pd.DataFrame, n_datasets=None, n_publications=None, n_documents=None) -> dict:
    """Counts for the Overview page. Computed from the data only; None means unknown."""
    if df.empty:
        return {"n_experiments": 0, "n_investigators": 0, "per_investigator": {},
                "n_numeric_sensor_readings": 0, "n_experiments_with_flags": 0,
                "years_in_table": [], "n_imported_datasets": n_datasets,
                "n_publications_listed": n_publications, "n_documents": n_documents}
    readings = sum(int(df[num].notna().sum()) for num, _, _, _ in SENSOR_COLUMNS if num in df.columns)
    years = (sorted(int(y) for y in df["date"].dt.year.dropna().unique())
             if "date" in df.columns else [])
    flagged = int((df["quality_flags"] != "").sum()) if "quality_flags" in df.columns else 0
    return {"n_experiments": int(len(df)), "n_investigators": int(df["pi"].nunique()),
            "per_investigator": df["pi"].value_counts().to_dict(),
            "n_numeric_sensor_readings": readings, "n_experiments_with_flags": flagged,
            "years_in_table": years, "n_imported_datasets": n_datasets,
            "n_publications_listed": n_publications, "n_documents": n_documents}
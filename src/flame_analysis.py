"""Analysis helpers for the PSI-25 (BASS-II) experimental table.

What is analysed: only columns that exist in the table. Gas readings are one initial and
one final reading per test, not time series. Derived values are our own calculations.
Correlations are exploratory: tests differ in investigator, fuel and geometry, and some
samples were reused, so rows are not fully independent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.preprocessing import NUMBER_RE, O2_SCREEN_RANGE

MIN_N_TO_SHOW = 5
MIN_N_CORRELATION = 10

VARIABLES = {
    "o2_initial_pct": {"label": "Initial O2", "unit": "% by volume", "kind": "measured (sensor)",
        "note": "FAQ: the O2 sensor was out of calibration, so NASA corrected the day's initial air reading with a constant offset from the ISS MCA reading."},
    "o2_final_pct": {"label": "Final O2", "unit": "% by volume", "kind": "measured (sensor)",
        "note": "Same sensor and correction as initial O2. Values outside our screening range are hidden here."},
    "co2_initial_pct": {"label": "Initial CO2", "unit": "% by volume", "kind": "measured (sensor)",
        "note": "FAQ: CDM sensor readings."},
    "co2_final_pct": {"label": "Final CO2", "unit": "% by volume", "kind": "measured (sensor)",
        "note": "FAQ: CDM sensor readings."},
    "co_initial_ppm": {"label": "Initial CO", "unit": "ppm", "kind": "measured (sensor)",
        "note": "FAQ: CSA-CP sensor; 'OR' means over range (above 1000 ppm). Such entries are not numeric here."},
    "co_final_ppm": {"label": "Final CO", "unit": "ppm", "kind": "measured (sensor)",
        "note": "FAQ: CSA-CP sensor; 'OR' means over range (above 1000 ppm). Such entries are not numeric here."},
    "delta_o2_pct": {"label": "O2 drop (initial minus final)", "unit": "percentage points", "kind": "derived (our calculation)",
        "note": "Difference of two sensor readings; only where both lie in the screening range."},
    "delta_co2_pct": {"label": "CO2 increase (final minus initial)", "unit": "percentage points", "kind": "derived (our calculation)",
        "note": "Difference of two sensor readings."},
    "delta_co_ppm": {"label": "CO increase (final minus initial)", "unit": "ppm", "kind": "derived (our calculation)",
        "note": "Difference of two sensor readings; missing where either reading is 'none', 'OR' or text."},
    "thickness_um": {"label": "Fuel thickness", "unit": "micrometres", "kind": "parsed from text (our parsing)",
        "note": "Read from the fuel description; absent for rods, fabrics and the candle."},
    "rod_diameter_mm": {"label": "Rod diameter", "unit": "mm", "kind": "parsed from text (our parsing)",
        "note": "Read from the fuel description; the inch-to-mm conversion is ours."},
    "size_cm": {"label": "Size as written in the fuel description", "unit": "cm", "kind": "parsed from text (our parsing)",
        "note": "First 'cm' value in the description; its meaning (for example strip width) depends on the sample."},
    "sides": {"label": "Sides burned", "unit": "count", "kind": "parsed from text (our parsing)",
        "note": "Only where the description says 1 or 2 sided."},
    "flow_restrictor": {"label": "Flow restrictor setting", "unit": "setting 0-2", "kind": "setting (ordinal)",
        "note": "FAQ: 0 is highest flow and lowest restriction; 2 is lowest flow and highest restriction."},
    "air_display_single_cm_s": {"label": "Duct air speed (single reading only)", "unit": "cm/s", "kind": "parsed from text (our parsing)",
        "note": "Only tests whose Air display holds one number. FAQ: the sensor responds slowly (about 1 min), and many tests changed flow in steps."},
}

CATEGORICAL = {"pi": "Principal investigator", "material": "Material",
               "geometry": "Geometry (our parsing)", "rod_color": "Rod colour (our parsing)"}

DERIVED_FROM = {
    "delta_o2_pct": {"o2_initial_pct", "o2_final_pct"},
    "delta_co2_pct": {"co2_initial_pct", "co2_final_pct"},
    "delta_co_ppm": {"co_initial_ppm", "co_final_ppm"},
}

UNAVAILABLE_VARIABLES = [
    {"variable": "Flame spread rate", "reason": "No such column in the PSI-25 experimental table. The publications derived it from video; the videos are not part of this app."},
    {"variable": "Flame length", "reason": "No such column in the PSI-25 experimental table."},
    {"variable": "Burning duration", "reason": "No such column. 'Total frames shot' is a count of camera images (it includes post-burn pictures), not a duration."},
    {"variable": "Temperature", "reason": "No such column in the PSI-25 experimental table."},
    {"variable": "Extinction outcome", "reason": "No dedicated column. Words like 'ext' appear in free-text flow entries, and their exact meaning is not defined in the FAQ."},
]

DATA_LIMITATIONS = [
    {"text": "The gas columns hold one initial and one final reading per test, not a continuous record.",
     "source": "PSI-25 experimental table (column structure)"},
    {"text": "The BASS hardware could not measure O2 throughout the whole experiment.",
     "source": "BASS-II Summary Report, page 68"},
    {"text": "O2 readings were corrected with a constant daily offset because the sensor was out of calibration.",
     "source": "BASS-II data FAQ"},
    {"text": "CO entries marked OR are over range (above 1000 ppm); they are not numeric values and are left out of calculations.",
     "source": "BASS-II data FAQ"},
    {"text": "Duct air speed responds slowly (about 1 minute), so a reading is steady only if the flow stayed constant.",
     "source": "BASS-II data FAQ"},
    {"text": "Some samples were used for more than one run, so rows are not fully independent.",
     "source": "BASS-II data FAQ"},
    {"text": "Tests differ in investigator, fuel and geometry. Pooling them mixes conditions that cannot be compared directly.",
     "source": "PSI-25 experimental table"},
]

CORRELATION_CAVEATS = [
    "Exploratory only: a correlation does not show that one variable causes the other.",
    "Tests of different fuels, geometries and investigators are pooled unless you filter them.",
    "Some samples were reused, so tests are not independent; the p-value is therefore optimistic.",
    "Many pairs tested together will produce some apparent patterns by chance.",
]


def parse_single_number(text) -> float:
    t = str(text if text is not None else "").strip()
    return float(t) if NUMBER_RE.match(t) else np.nan


def prepare_analysis_frame(clean: pd.DataFrame) -> pd.DataFrame:
    """Copy of the cleaned table for analysis. Raw text columns are untouched; O2 values
    outside our screening range are hidden (NaN) in the numeric columns and the row is marked."""
    df = clean.copy()
    lo, hi = O2_SCREEN_RANGE
    masked = pd.Series(False, index=df.index)
    for col in ("o2_initial_pct", "o2_final_pct"):
        if col in df.columns:
            bad = df[col].notna() & ~df[col].between(lo, hi)
            masked |= bad
            df.loc[bad, col] = np.nan
    df["o2_screen_masked"] = masked
    if "air_display_raw" in df.columns:
        df["air_display_single_cm_s"] = df["air_display_raw"].map(parse_single_number)
    return df


def available_variables(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col, meta in VARIABLES.items():
        if col not in df.columns:
            continue
        n = int(df[col].notna().sum())
        rows.append({"column": col, "label": meta["label"], "unit": meta["unit"],
                     "kind": meta["kind"], "n_available": n, "n_total": int(len(df)),
                     "shown": n >= MIN_N_TO_SHOW, "note": meta["note"]})
    return pd.DataFrame(rows)


def apply_filters(df: pd.DataFrame, pis=None, materials=None, geometries=None,
                  o2_initial_range=None) -> pd.DataFrame:
    out = df
    if pis:
        out = out[out["pi"].isin(pis)]
    if materials:
        out = out[out["material"].isin(materials)]
    if geometries:
        out = out[out["geometry"].isin(geometries)]
    if o2_initial_range:
        lo, hi = o2_initial_range
        out = out[out["o2_initial_pct"].between(lo, hi)]  # rows without a valid O2 drop out
    return out


def describe_variable(df: pd.DataFrame, col: str) -> dict:
    s = df[col].dropna() if col in df.columns else pd.Series(dtype=float)
    if s.empty:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {"n": int(len(s)), "min": float(s.min()), "median": float(s.median()), "max": float(s.max())}


def group_summary(df: pd.DataFrame, by: str, value: str, min_n: int = 3) -> pd.DataFrame:
    cols = ["group", "n", "median", "q1", "q3", "minimum", "maximum", "small_n"]
    if by not in df.columns or value not in df.columns:
        return pd.DataFrame(columns=cols)
    data = df[[by, value]].dropna().copy()
    data[by] = data[by].astype(str).replace("", "n/a")
    if data.empty:
        return pd.DataFrame(columns=cols)
    out = data.groupby(by)[value].agg(
        n="count", median="median", q1=lambda s: s.quantile(0.25),
        q3=lambda s: s.quantile(0.75), minimum="min", maximum="max").reset_index()
    out = out.rename(columns={by: "group"})
    out["small_n"] = out["n"] < min_n
    return out.sort_values("n", ascending=False).reset_index(drop=True)


def _strength(rho: float) -> str:
    a = abs(rho)
    word = ("very weak" if a < 0.2 else "weak" if a < 0.4 else "moderate" if a < 0.6
            else "strong" if a < 0.8 else "very strong")
    return f"{word} {'positive' if rho > 0 else 'negative'}"


def correlate(df: pd.DataFrame, x: str, y: str, min_n: int = MIN_N_CORRELATION) -> dict:
    """Spearman rank correlation, only where it is appropriate. Always check 'status'."""
    result = {"x": x, "y": y, "n": 0, "rho": None, "p_value": None, "status": "", "message": ""}
    if x == y:
        result.update(status="same_variable", message="Both variables are the same.")
        return result
    if x not in df.columns or y not in df.columns:
        result.update(status="missing_column", message="One of the variables is not in the data.")
        return result
    if x in DERIVED_FROM.get(y, set()) or y in DERIVED_FROM.get(x, set()):
        result.update(status="linked", message="One variable is calculated from the other, so a correlation is expected and says nothing new.")
        return result
    pair = df[[x, y]].dropna()
    result["n"] = int(len(pair))
    if len(pair) < min_n:
        result.update(status="too_few", message=f"Only {len(pair)} complete pairs; at least {min_n} are needed.")
        return result
    if pair[x].nunique() < 3 or pair[y].nunique() < 3:
        result.update(status="no_variation", message="One variable has fewer than 3 distinct values.")
        return result
    rho, p = stats.spearmanr(pair[x], pair[y])
    result.update(status="ok", rho=float(rho), p_value=float(p),
                  message=(f"Spearman rho = {rho:.2f} ({_strength(rho)}; wording is a rule of thumb), "
                           f"p = {p:.3g}, n = {len(pair)}."))
    return result


def correlation_table(df: pd.DataFrame, columns: list[str], min_n: int = MIN_N_CORRELATION) -> pd.DataFrame:
    rows = []
    for i, x in enumerate(columns):
        for y in columns[i + 1:]:
            r = correlate(df, x, y, min_n)
            rows.append({"x": x, "y": y, "n": r["n"], "rho": r["rho"], "p_value": r["p_value"],
                         "status": r["status"]})
    return pd.DataFrame(rows, columns=["x", "y", "n", "rho", "p_value", "status"])
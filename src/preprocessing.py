"""Cleaning and parsing of the BASS-II experimental table.

Rules: source text is never overwritten; non-numeric entries are not converted;
suspicious values are flagged, not removed. Derived columns are our own
calculations, not NASA measurements.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

NUMBER_RE = re.compile(r"^-?(?:\d+(?:\.\d*)?|\.\d+)$")

# Raw text column -> parsed numeric column.
NUMERIC_COLUMNS = {
    "o2_initial_raw": "o2_initial_pct",
    "o2_final_raw": "o2_final_pct",
    "co2_initial_raw": "co2_initial_pct",
    "co2_final_raw": "co2_final_pct",
    "co_initial_raw": "co_initial_ppm",
    "co_final_raw": "co_final_ppm",
    "flow_restrictor_raw": "flow_restrictor",
    "total_frames_raw": "total_frames",
}

# Columns checked for missing / non-numeric entries (analysis-critical ones).
FLAGGED_COLUMNS = {
    "o2_initial_raw": "o2_initial",
    "o2_final_raw": "o2_final",
    "co2_initial_raw": "co2_initial",
    "co2_final_raw": "co2_final",
    "co_initial_raw": "co_initial",
    "co_final_raw": "co_final",
}

# Our own screening range for O2 (% by volume). NOT a NASA limit.
O2_SCREEN_RANGE = (10.0, 25.0)

FUEL_FIELDS = ["material", "geometry", "thickness_um", "size_cm", "sides",
               "rod_diameter_mm", "rod_color"]

MATERIAL_KEYWORDS = [("pmma", "PMMA"), ("sibal", "SIBAL"),
                     ("nomex", "Nomex"), ("wax", "Wax candle")]

_THICKNESS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(micron|mm)", re.I)
_SIZE_CM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*cm", re.I)
_SIDES_RE = re.compile(r"\b([12])\s*sided", re.I)
_FRACTION_RE = re.compile(r"(\d+)\s*/\s*(\d+)")
_DECIMAL_RE = re.compile(r"(?<![\d/])(\d*\.\d+)")


def classify_value(text) -> str:
    """Return one of: numeric, missing, none, over_range, text."""
    t = str(text if text is not None else "").strip()
    if t == "":
        return "missing"
    if NUMBER_RE.match(t):
        return "numeric"
    low = t.lower()
    if low == "none":
        return "none"
    if low in {"or", "over"}:
        return "over_range"
    return "text"


def parse_number(text) -> float:
    """Convert only clean numeric strings; everything else becomes NaN."""
    if classify_value(text) == "numeric":
        return float(str(text).strip())
    return np.nan


def parse_fuel(text) -> dict:
    """Extract what the fuel description literally states. Unknown stays unknown."""
    t = " ".join(str(text if text is not None else "").split())
    low = t.lower()
    out = {"material": "not stated", "geometry": "unparsed", "thickness_um": np.nan,
           "size_cm": np.nan, "sides": np.nan, "rod_diameter_mm": np.nan, "rod_color": ""}
    if not t:
        return out

    for keyword, name in MATERIAL_KEYWORDS:
        if keyword in low:
            out["material"] = name
            break

    m = _THICKNESS_RE.search(t)
    if m:
        value = float(m.group(1))
        out["thickness_um"] = value if m.group(2).lower() == "micron" else value * 1000.0
    m = _SIZE_CM_RE.search(t)
    if m:
        out["size_cm"] = float(m.group(1))
    m = _SIDES_RE.search(t)
    if m:
        out["sides"] = float(m.group(1))

    if "rod" in low:
        out["geometry"] = "rod"
        frac = _FRACTION_RE.search(t)
        if frac and float(frac.group(2)) != 0:
            inches = float(frac.group(1)) / float(frac.group(2))
            out["rod_diameter_mm"] = round(inches * 25.4, 2)
        else:
            dec = _DECIMAL_RE.search(t)
            if dec:
                out["rod_diameter_mm"] = round(float(dec.group(1)) * 25.4, 2)
        if "black" in low:
            out["rod_color"] = "black"
        elif "clear" in low:
            out["rod_color"] = "clear"
    elif "spher" in low:
        out["geometry"] = "spherical section"
    elif "sibal" in low or "nomex" in low:
        out["geometry"] = "fabric"
    elif "candle" in low:
        out["geometry"] = "candle"
    elif "film" in low:
        out["geometry"] = "film"
    elif not np.isnan(out["thickness_um"]):
        out["geometry"] = "flat sample (thickness only)"
    return out


def clean_experiment_table(raw: pd.DataFrame) -> pd.DataFrame:
    """Add parsed numeric columns, fuel fields, derived deltas and quality flags."""
    df = raw.copy()
    if df.empty:
        return df

    for raw_col, num_col in NUMERIC_COLUMNS.items():
        if raw_col in df.columns:
            df[num_col] = df[raw_col].map(parse_number)

    fuel = pd.DataFrame([parse_fuel(t) for t in df["fuel_text"]],
                        index=df.index, columns=FUEL_FIELDS)
    df = pd.concat([df, fuel], axis=1)

    df["date"] = pd.to_datetime(df["date_raw"], format="%m/%d/%Y", errors="coerce")
    df["gmt_day"] = df["gmt_day_raw"].map(parse_number)

    lo, hi = O2_SCREEN_RANGE
    o2_ok = (df["o2_initial_pct"].between(lo, hi)) & (df["o2_final_pct"].between(lo, hi))
    # Derived (our calculation): O2 drop, CO2 and CO increase during the test.
    df["delta_o2_pct"] = np.where(o2_ok, df["o2_initial_pct"] - df["o2_final_pct"], np.nan)
    df["delta_co2_pct"] = df["co2_final_pct"] - df["co2_initial_pct"]
    df["delta_co_ppm"] = df["co_final_ppm"] - df["co_initial_ppm"]

    years = df["date"].dt.year.dropna()
    majority_year = int(years.mode().iloc[0]) if not years.empty else None

    all_flags = []
    for _, row in df.iterrows():
        flags = []
        for raw_col, label in FLAGGED_COLUMNS.items():
            status = classify_value(row[raw_col])
            if status == "missing":
                flags.append(f"{label}: missing")
            elif status == "none":
                flags.append(f"{label}: 'none' in source")
            elif status == "over_range":
                flags.append(f"{label}: over range in source")
            elif status == "text":
                flags.append(f"{label}: non-numeric text '{row[raw_col]}'")
        for col, label in (("o2_initial_pct", "o2_initial"), ("o2_final_pct", "o2_final")):
            value = row[col]
            if pd.notna(value) and not (lo <= value <= hi):
                flags.append(f"{label}: {value} outside screening range {lo}-{hi} % (possible data-entry error)")
        if row["date_raw"] and pd.isna(row["date"]):
            flags.append(f"date: could not be parsed ('{row['date_raw']}')")
        if pd.notna(row["date"]):
            if majority_year and row["date"].year != majority_year:
                flags.append(f"date: year {row['date'].year} differs from the most common year ({majority_year}); verify")
            if pd.notna(row["gmt_day"]):
                doy = row["date"].dayofyear
                if abs(doy - row["gmt_day"]) > 1:
                    flags.append(f"date/GMT: date is day {doy} of the year, GMT column says {int(row['gmt_day'])}")
        if row["geometry"] == "unparsed":
            flags.append("fuel: description could not be parsed")
        all_flags.append("; ".join(flags))

    df["quality_flags"] = all_flags
    df["flag_count"] = [len(f.split("; ")) if f else 0 for f in all_flags]
    return df


def quality_summary(df: pd.DataFrame) -> dict:
    """Plain counts for the data-quality panel. Computed from the data only."""
    if df.empty:
        return {"n_rows": 0}
    years = df["date"].dt.year.dropna()
    return {
        "n_rows": int(len(df)),
        "n_rows_with_flags": int((df["quality_flags"] != "").sum()),
        "n_o2_delta_available": int(df["delta_o2_pct"].notna().sum()),
        "n_co2_delta_available": int(df["delta_co2_pct"].notna().sum()),
        "n_co_delta_available": int(df["delta_co_ppm"].notna().sum()),
        "n_fuel_unparsed": int((df["geometry"] == "unparsed").sum()),
        "years_present": sorted(int(y) for y in years.unique()),
    }
"""Logic tests with toy numbers (not NASA data). Run: python tests/test_flame_analysis.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.flame_analysis import (UNAVAILABLE_VARIABLES, apply_filters, available_variables,
                                correlate, group_summary, prepare_analysis_frame)


def _frame():
    n = 12
    return pd.DataFrame({
        "pi": ["A"] * 6 + ["B"] * 6, "material": ["PMMA"] * n,
        "geometry": ["rod"] * 6 + ["film"] * 6,
        "o2_initial_pct": [21.0] * 10 + [18.0, 22.2],
        "o2_final_pct": [20.5] * 9 + [1.6, 17.0, 21.9],
        "delta_o2_pct": [0.5] * n,
        "delta_co_ppm": [float(2 * i) for i in range(n)],
        "x_series": [float(i) for i in range(n)],
        "air_display_raw": ["5", "3 5", "10"] + ["none"] * 9,
    })


def test_prepare_masks_bad_o2():
    df = prepare_analysis_frame(_frame())
    assert pd.isna(df.loc[9, "o2_final_pct"]) and bool(df.loc[9, "o2_screen_masked"])
    assert df.loc[0, "air_display_single_cm_s"] == 5 and pd.isna(df.loc[1, "air_display_single_cm_s"])


def test_correlation_perfect_and_guards():
    df = _frame()
    ok = correlate(df, "x_series", "delta_co_ppm")
    assert ok["status"] == "ok" and abs(ok["rho"] - 1.0) < 1e-9 and ok["n"] == 12
    assert correlate(df.head(5), "x_series", "delta_co_ppm")["status"] == "too_few"
    assert correlate(df, "o2_final_pct", "delta_o2_pct")["status"] == "linked"
    assert correlate(df, "x_series", "x_series")["status"] == "same_variable"


def test_group_summary_and_filters():
    df = _frame()
    g = group_summary(df, "geometry", "delta_co_ppm", min_n=7)
    assert set(g["group"]) == {"rod", "film"} and g["small_n"].all() and int(g["n"].sum()) == 12
    assert len(apply_filters(df, pis=["A"])) == 6 and len(apply_filters(df, geometries=["film"])) == 6
    assert len(apply_filters(df, o2_initial_range=(20, 23))) == 11


def test_availability_and_unavailable_list():
    table = available_variables(prepare_analysis_frame(_frame()))
    assert "air_display_single_cm_s" in set(table["column"])
    assert bool(table.set_index("column").loc["delta_co_ppm", "shown"])
    assert any(u["variable"] == "Flame spread rate" for u in UNAVAILABLE_VARIABLES)


if __name__ == "__main__":
    test_prepare_masks_bad_o2()
    test_correlation_perfect_and_guards()
    test_group_summary_and_filters()
    test_availability_and_unavailable_list()
    print("all flame analysis tests passed")
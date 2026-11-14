"""Plain-assert tests for the parsing logic. Run: python tests/test_preprocessing.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import math

import pandas as pd

from src.preprocessing import classify_value, clean_experiment_table, parse_fuel


def _row(**overrides):
    base = {"pi": "Bhattacharjee", "test_id": "B1", "date_raw": "2/19/2014", "gmt_day_raw": "50",
            "sample_id": "147", "fuel_text": "100 micron PMMA film 2 cm wide",
            "flow_restrictor_raw": "2", "fan_display_raw": "62", "air_display_raw": "5",
            "radiometer_gain_raw": "50", "total_frames_raw": "57",
            "o2_initial_raw": "22.2", "o2_final_raw": "22.2", "co2_initial_raw": "0.44",
            "co2_final_raw": "0.44", "co_initial_raw": "0", "co_final_raw": "6"}
    base.update(overrides)
    return base


def test_classify():
    assert classify_value("22.2") == "numeric"
    assert classify_value("OR") == "over_range"
    assert classify_value("none") == "none"
    assert classify_value(">500") == "text"
    assert classify_value("") == "missing"


def test_fuel_parsing():
    f = parse_fuel("100 micron PMMA film 2 cm wide")
    assert f["thickness_um"] == 100 and f["size_cm"] == 2 and f["geometry"] == "film" and f["material"] == "PMMA"
    assert parse_fuel("2 cm 0.1 mm PMMA film")["thickness_um"] == 100
    assert parse_fuel("3 mm thick PMMA 2 sided 2 cm thick")["sides"] == 2
    rod = parse_fuel('1/4" clear rod')
    assert rod["geometry"] == "rod" and rod["rod_color"] == "clear" and abs(rod["rod_diameter_mm"] - 6.35) < 0.01
    assert parse_fuel('0.5" black rod')["rod_diameter_mm"] == 12.7
    assert parse_fuel("4 cm spherical section")["geometry"] == "spherical section"
    assert parse_fuel("2 cm SIBAL")["geometry"] == "fabric"
    assert parse_fuel("")["geometry"] == "unparsed"


def test_cleaning_flags():
    raw = pd.DataFrame([
        _row(),
        _row(test_id="B2", o2_final_raw="1.6", co2_final_raw="", co_final_raw=""),
        _row(test_id="T9", date_raw="6/24/2018", gmt_day_raw="175"),
    ])
    clean = clean_experiment_table(raw).set_index("test_id")
    assert clean.loc["B1", "quality_flags"] == ""
    assert abs(clean.loc["B1", "delta_co_ppm"] - 6) < 1e-9
    assert "o2_final" in clean.loc["B2", "quality_flags"] and "outside" in clean.loc["B2", "quality_flags"]
    assert math.isnan(clean.loc["B2", "delta_o2_pct"])
    assert "year 2018" in clean.loc["T9", "quality_flags"]


if __name__ == "__main__":
    test_classify()
    test_fuel_parsing()
    test_cleaning_flags()
    print("all tests passed")
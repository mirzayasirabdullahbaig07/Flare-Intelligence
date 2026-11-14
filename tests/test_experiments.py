"""Logic tests with toy rows (not NASA data). Run: python tests/test_experiments.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.comparison import chart_data, compare_experiments
from src.experiment_manager import (count_imported_datasets, dataset_overview, experiment_listing,
                                    get_experiment, search_experiments)
from src.preprocessing import clean_experiment_table


def _row(**overrides):
    base = {"pi": "Bhattacharjee", "test_id": "B1", "date_raw": "2/19/2014", "gmt_day_raw": "50",
            "sample_id": "147", "fuel_text": "100 micron PMMA film 2 cm wide",
            "flow_restrictor_raw": "2", "fan_display_raw": "62", "air_display_raw": "5",
            "radiometer_gain_raw": "50", "total_frames_raw": "57",
            "o2_initial_raw": "22.2", "o2_final_raw": "22.2", "co2_initial_raw": "0.44",
            "co2_final_raw": "0.44", "co_initial_raw": "0", "co_final_raw": "6"}
    base.update(overrides)
    return base


def _frame():
    raw = pd.DataFrame([
        _row(),
        _row(pi="Miller", test_id="M1", sample_id="222", fuel_text="1 mm thick PMMA 1 sided 2 cm",
             o2_initial_raw="18.9", o2_final_raw="18.4", co2_initial_raw="1.42", co2_final_raw="1.84",
             co_initial_raw="398", co_final_raw="612"),
        _row(pi="Olson", test_id="O2", sample_id="147", fuel_text='1/4" clear rod',
             o2_final_raw="none", co2_final_raw=""),
    ])
    return clean_experiment_table(raw)


def test_record():
    df = _frame()
    rec = get_experiment(df, "b1")
    assert rec["flat"]["Investigator"] == "Bhattacharjee"
    assert rec["flat"]["Rod diameter (our conversion to mm)"] == "Not available"
    assert rec["flat"]["Flow restrictor setting"].startswith("2 (")
    o2 = get_experiment(df, "O2")
    assert o2["flat"]["Final O2"] == "not numeric in source ('none')"
    assert o2["flat"]["Final CO2"] == "Not available"
    assert get_experiment(df, "ZZ") is None


def test_search_and_listing():
    df = _frame()
    assert list(search_experiments(df, text="rod")["test_id"]) == ["O2"]
    assert list(search_experiments(df, pis=["Miller"])["test_id"]) == ["M1"]
    listing = experiment_listing(df)
    assert len(listing) == 3 and "sensor_readings" in listing.columns


def test_compare():
    df = _frame()
    result = compare_experiments(df, ["B1", "M1", "O2", "NOPE"])
    assert result["missing_ids"] == ["NOPE"]
    assert list(result["table"].columns) == ["B1", "M1", "O2"]
    notes = " ".join(result["notes"])
    assert "different investigators" in notes and "Initial O2 differs" in notes and "share sample number 147" in notes
    assert result["table"].loc["Fuel description (as written)", "M1"] == "1 mm thick PMMA 1 sided 2 cm"
    assert "Select at least two" in compare_experiments(df, ["B1"])["notes"][0]


def test_chart_data():
    df = _frame()
    chart, missing = chart_data(df, ["B1", "O2"], ["delta_o2_pct"])
    assert list(chart["test_id"]) == ["B1"] and "O2: O2 drop (initial minus final)" in missing


def test_overview_and_datasets():
    overview = dataset_overview(_frame(), n_datasets=2)
    assert overview["n_experiments"] == 3 and overview["n_investigators"] == 3
    assert overview["n_numeric_sensor_readings"] == 16 and overview["n_imported_datasets"] == 2
    assert dataset_overview(pd.DataFrame())["n_experiments"] == 0
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("a.csv", "b.xlsx", "c.txt"):
            (Path(tmp) / name).write_text("x")
        assert count_imported_datasets(tmp) == 2
    assert count_imported_datasets("does-not-exist") == 0


if __name__ == "__main__":
    test_record()
    test_search_and_listing()
    test_compare()
    test_chart_data()
    test_overview_and_datasets()
    print("all experiment tests passed")
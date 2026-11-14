"""Loading of the real BASS-II files from data/raw. No data is generated here."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "bass-ii"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPERIMENT_CSV = RAW_DIR / "PSI-25_Experimental table_BASS-II.csv"
TEST_MATRIX_XLSX = RAW_DIR / "BASS-II Test Matrix by PI Final.xlsx"

# Source column names (lower-case, whitespace collapsed) -> internal names.
# "_raw" means: text exactly as in the source, only whitespace tidied.
COLUMN_MAP = {
    "pi": "pi",
    "test #": "test_id",
    "test no.": "test_id",
    "date": "date_raw",
    "actual date (for video display date, add 1 for leap year)": "date_raw",
    "gmt": "gmt_day_raw",
    "gmt 2014-": "gmt_day_raw",
    "sample #": "sample_id",
    "sample no.": "sample_id",
    "fuel sample material": "fuel_text",
    "material": "fuel_text",
    "flow restrictor": "flow_restrictor_raw",
    "fan display": "fan_display_raw",
    "air display": "air_display_raw",
    "radiometer gain (1000 250 50 10)": "radiometer_gain_raw",
    "radiometer gain (1000, 250, 50, 10)": "radiometer_gain_raw",
    "total frames shot": "total_frames_raw",
    "calibrated initial o2 % by vol": "o2_initial_raw",
    "calibrated final o2 % by vol": "o2_final_raw",
    "initial co2 % by vol": "co2_initial_raw",
    "final co2 % by vol": "co2_final_raw",
    "initial co (ppm)": "co_initial_raw",
    "final co (ppm)": "co_final_raw",
}

REQUIRED_CSV_COLUMNS = [
    "pi", "test_id", "date_raw", "gmt_day_raw", "sample_id", "fuel_text",
    "o2_initial_raw", "o2_final_raw", "co2_initial_raw", "co2_final_raw",
    "co_initial_raw", "co_final_raw",
]


class DataNotFoundError(FileNotFoundError):
    """Raised when an expected NASA data file is not in data/raw."""


def _tidy_text(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse repeated whitespace in every cell. Content is not changed."""
    return df.apply(lambda col: col.astype(str).str.split().str.join(" "))


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        key = " ".join(str(col).replace("\ufeff", "").split()).lower()
        renamed[col] = COLUMN_MAP.get(key, " ".join(str(col).split()))
    return df.rename(columns=renamed)


def validate_required_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Expected columns not found: {missing}. Found: {list(df.columns)}"
        )


def load_experiment_table(path: Path = EXPERIMENT_CSV) -> pd.DataFrame:
    """Read the PSI-25 experimental table as text (nothing is converted)."""
    if not Path(path).exists():
        raise DataNotFoundError(
            f"File not found: {path}. Download it from the PSI-25 page and put it in data/raw/bass-ii/."
        )
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df = _rename_columns(_tidy_text(df))
    validate_required_columns(df, REQUIRED_CSV_COLUMNS)
    return df


def load_test_matrix(path: Path = TEST_MATRIX_XLSX) -> tuple[pd.DataFrame, list[str]]:
    """Read every PI sheet of the test-matrix workbook. Returns (table, warnings)."""
    if not Path(path).exists():
        raise DataNotFoundError(f"File not found: {path}.")
    warnings: list[str] = []
    frames = []
    sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    for sheet_name, sheet in sheets.items():
        sheet = _rename_columns(_tidy_text(sheet.fillna("")))
        if "test_id" not in sheet.columns:
            warnings.append(f"Sheet '{sheet_name}' skipped: no test-number column found.")
            continue
        sheet.insert(0, "pi_sheet", sheet_name)
        frames.append(sheet)
    table = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return table, warnings


def cross_check_sources(csv_df: pd.DataFrame, matrix_df: pd.DataFrame) -> dict:
    """Compare which test IDs appear in the CSV and in the workbook."""
    if matrix_df.empty or "test_id" not in matrix_df.columns:
        return {"n_csv": len(csv_df), "n_matrix": 0, "only_in_csv": [], "only_in_matrix": []}
    csv_ids = set(csv_df["test_id"].str.strip().str.upper())
    mat_ids = set(matrix_df["test_id"].str.strip().str.upper()) - {""}
    return {
        "n_csv": len(csv_df),
        "n_matrix": len(matrix_df),
        "only_in_csv": sorted(csv_ids - mat_ids),
        "only_in_matrix": sorted(mat_ids - csv_ids),
    }
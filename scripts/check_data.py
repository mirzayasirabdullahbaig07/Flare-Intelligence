"""Run the loader and cleaner on the real files and print an honest report."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.data_loader import (PROCESSED_DIR, DataNotFoundError, cross_check_sources,
                             load_experiment_table, load_test_matrix)
from src.preprocessing import clean_experiment_table, quality_summary


def main() -> None:
    try:
        raw = load_experiment_table()
    except (DataNotFoundError, ValueError) as exc:
        print(f"STOP: {exc}")
        return

    clean = clean_experiment_table(raw)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "bass_ii_clean.csv"
    clean.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("QUALITY SUMMARY")
    for key, value in quality_summary(clean).items():
        print(f"  {key}: {value}")

    print("\nROWS PER PI")
    print(clean["pi"].value_counts().to_string())

    print("\nGEOMETRY COUNTS")
    print(clean["geometry"].value_counts().to_string())

    flagged = clean[clean["quality_flags"] != ""]
    print(f"\nFLAGGED ROWS ({len(flagged)})")
    pd.set_option("display.max_colwidth", 200)
    for _, row in flagged.iterrows():
        print(f"  {row['test_id']}: {row['quality_flags']}")

    try:
        matrix, warnings = load_test_matrix()
        print("\nCSV vs TEST MATRIX")
        print(f"  {cross_check_sources(clean, matrix)}")
        for w in warnings:
            print(f"  WARNING: {w}")
    except (DataNotFoundError, ValueError) as exc:
        print(f"\nTest matrix not checked: {exc}")

    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
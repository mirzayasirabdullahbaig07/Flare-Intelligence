"""Run experiment_manager and comparison on the REAL table and print an honest report."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.comparison import chart_data, compare_experiments
from src.data_loader import RAW_DIR, DataNotFoundError, load_experiment_table
from src.experiment_manager import (count_imported_datasets, dataset_overview, experiment_listing,
                                    get_experiment)
from src.preprocessing import clean_experiment_table
from src.source_manager import get_publications, get_study_overview, load_investigation


def main() -> None:
    try:
        df = clean_experiment_table(load_experiment_table())
    except (DataNotFoundError, ValueError) as exc:
        print(f"STOP: {exc}")
        return

    study, n_pubs = None, None
    try:
        fields = load_investigation()
        study = get_study_overview(fields)
        n_pubs = len(get_publications(fields))
    except (FileNotFoundError, KeyError, OSError) as exc:
        print(f"(metadata not loaded: {exc})")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 60)

    print("OVERVIEW")
    for key, value in dataset_overview(df, count_imported_datasets(RAW_DIR), n_pubs).items():
        print(f"  {key}: {value}")

    print("\nLISTING (first 8)")
    print(experiment_listing(df).head(8).to_string(index=False))

    print("\nRECORD B1")
    record = get_experiment(df, "B1", study)
    for section, items in record["sections"].items():
        print(f"  [{section}]")
        for label, value in items:
            print(f"    {label}: {str(value)[:110]}")

    ids = ["B1", "M1", "O2", "P22b", "NOPE"]
    result = compare_experiments(df, ids, study)
    print(f"\nCOMPARISON {ids}  (missing: {result['missing_ids']})")
    print(result["table"].to_string())
    print("\nNOTES")
    for note in result["notes"]:
        print(f"  - {note}")

    chart, missing = chart_data(df, ids)
    print(f"\nCHART DATA: {len(chart)} points; missing: {missing}")


if __name__ == "__main__":
    main()
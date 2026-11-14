"""Run the analysis helpers on the REAL table and print an honest report."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.data_loader import DataNotFoundError, load_experiment_table
from src.flame_analysis import (apply_filters, available_variables, correlate,
                                group_summary, prepare_analysis_frame)
from src.preprocessing import clean_experiment_table


def main() -> None:
    try:
        clean = clean_experiment_table(load_experiment_table())
    except (DataNotFoundError, ValueError) as exc:
        print(f"STOP: {exc}")
        return
    df = prepare_analysis_frame(clean)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    print(f"Rows: {len(df)} | rows with an O2 value hidden by screening: {int(df['o2_screen_masked'].sum())}\n")

    print("AVAILABLE VARIABLES")
    table = available_variables(df)
    print(table[["column", "unit", "kind", "n_available", "shown"]].to_string(index=False))

    print("\nCO INCREASE (ppm) BY GEOMETRY")
    print(group_summary(df, "geometry", "delta_co_ppm").to_string(index=False))

    print("\nINITIAL O2 (%) BY INVESTIGATOR")
    print(group_summary(df, "pi", "o2_initial_pct").to_string(index=False))

    print("\nCORRELATIONS (all tests pooled, then rods only)")
    pairs = [("o2_initial_pct", "delta_co_ppm"), ("o2_initial_pct", "delta_co2_pct"),
             ("thickness_um", "delta_co_ppm"), ("rod_diameter_mm", "delta_co_ppm"),
             ("air_display_single_cm_s", "delta_co_ppm")]
    rods = apply_filters(df, geometries=["rod"])
    for x, y in pairs:
        print(f"  pooled  {x} vs {y}: {correlate(df, x, y)['status']} | {correlate(df, x, y)['message']}")
        print(f"  rods    {x} vs {y}: {correlate(rods, x, y)['status']} | {correlate(rods, x, y)['message']}")


if __name__ == "__main__":
    main()
"""Score the real research/findings.csv and print an honest report."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.ranking import load_findings, score_findings


def main() -> None:
    df, warnings = load_findings()
    for w in warnings:
        print(f"WARNING: {w}")
    if df.empty:
        print("No findings loaded.")
        return
    table, notes = score_findings(df)
    for n in notes:
        print(f"NOTE: {n}")
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 70)
    print(f"{len(table)} findings loaded\n")
    print(table[["finding_id", "category", "status", "score", "rank"]].to_string(index=False))
    scored = table[table["status"] == "scored"]
    for _, r in scored.iterrows():
        print(f"\n{r['finding_id']}: {r['explanation']}")
        print(f"   sources: {r['source_ids']} | {r['locations']}")
        print(f"   review status: {r['review_status']}")


if __name__ == "__main__":
    main()
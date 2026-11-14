"""Logic tests with toy rows (not findings). Run: python tests/test_ranking.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.ranking import (REQUIRED_COLUMNS, count_sources, criteria_table, load_findings,
                         normalise_weights, score_findings)


def _row(fid, category="observation", sources="s1", ratings=("3", "3", "3", "3")):
    row = {c: "" for c in REQUIRED_COLUMNS}
    row.update(finding_id=fid, title=fid, category=category, source_ids=sources,
               relevance=ratings[0], evidence=ratings[1], measurable=ratings[2], applicability=ratings[3])
    return row


def test_scoring():
    df = pd.DataFrame([
        _row("A", sources="s1;s2;s3"),
        _row("B", sources="s1", ratings=("3", "0", "0", "0")),
        _row("C", category="hypothesis"),
        _row("D", ratings=("3", "", "2", "1")),
    ])
    table, notes = score_findings(df)
    t = table.set_index("finding_id")
    assert t.loc["A", "score"] == 100.0 and t.loc["A", "rank"] == 1
    assert abs(t.loc["B", "score"] - 26.7) < 0.05 and t.loc["B", "rank"] == 2
    assert t.loc["C", "status"].startswith("not scored") and t.loc["C", "score"] is None or pd.isna(t.loc["C", "score"])
    assert t.loc["D", "status"] == "not rated (missing: evidence)"
    weighted, _ = score_findings(df, {"sources": 0})
    assert weighted.set_index("finding_id").loc["B", "score"] == 25.0


def test_weights_and_sources():
    merged, notes = normalise_weights({"relevance": -1, "bogus": 2, "evidence": "x"})
    assert merged["relevance"] == 1.0 and len(notes) == 3
    merged, notes = normalise_weights({k: 0 for k in merged})
    assert all(v == 1.0 for v in merged.values()) and notes
    assert count_sources("a; b;a") == 2 and count_sources("") == 0 and count_sources(None) == 0


def test_loading_and_criteria():
    df, warnings = load_findings("does-not-exist.csv")
    assert df.empty and warnings
    assert len(criteria_table()) == 5
    empty, _ = score_findings(pd.DataFrame(columns=REQUIRED_COLUMNS))
    assert empty.empty


if __name__ == "__main__":
    test_scoring()
    test_weights_and_sources()
    test_loading_and_criteria()
    print("all ranking tests passed")
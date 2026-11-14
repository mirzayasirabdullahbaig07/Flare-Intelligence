"""Logic tests with toy data (not NASA data). Run: python tests/test_data_tools.py"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import docx
import numpy as np
import pandas as pd
import pymupdf

from src.data_tools import (chunk_uploaded_document, clean_table, column_report, read_table,
                            table_summary, validate_bass_schema)


def raises_value_error(function, *args) -> bool:
    try:
        function(*args)
    except ValueError:
        return True
    return False


def test_reading():
    df, _ = read_table("a.csv", b"a,b\n1,x\n2,\n3,y\n")
    assert len(df) == 3 and int(df["b"].isna().sum()) == 1
    df, _ = read_table("a.json", b'[{"a": 1, "b": "x"}, {"a": 2}]')
    assert len(df) == 2
    df, notes = read_table("a.json", b'{"data": [{"a": 1}, {"a": 2}]}')
    assert len(df) == 2 and notes
    for name, payload in [("a.csv", b""), ("a.json", b"not json"), ("a.txt", b"x"), ("a.json", b"[1, 2]")]:
        assert raises_value_error(read_table, name, payload), name


def test_reports():
    df = pd.DataFrame({"a": ["1", "1", np.nan], "b": [np.nan, np.nan, np.nan]})
    summary = table_summary(df)
    assert summary["rows"] == 3 and summary["empty_columns"] == 1 and summary["missing_cells"] == 4
    report = column_report(df).set_index("Column")
    assert report.loc["a", "Missing"] == 1 and report.loc["b", "Missing (%)"] == 100.0


def test_cleaning():
    df = pd.DataFrame({"v": ["1", " 2 ", "x", np.nan], "w": [np.nan] * 4, "z": ["a", "b", "b", "b"]})
    cleaned, log = clean_table(df, numeric_columns=["v"], drop_missing_in=["v"])
    assert "w" not in cleaned.columns and list(cleaned["v"]) == [1.0, 2.0]
    assert "v_original_text" in cleaned.columns and any("not numbers" in line for line in log)
    dup = pd.DataFrame({"a": ["1", "1", "2"]})
    assert len(clean_table(dup, drop_duplicates=True)[0]) == 2
    assert len(clean_table(dup)[0]) == 3


def test_bass_schema():
    cols = ["PI", "Test #", "Date", "GMT", "Sample #", "Fuel Sample Material", "Flow restrictor",
            "Calibrated  initial O2 % by vol ", "Calibrated final O2 % by vol", "Initial CO2 % by vol",
            "Final CO2 % by vol", "Initial CO (ppm)", "Final CO (ppm)"]
    assert validate_bass_schema(pd.DataFrame(columns=cols))["complete"]
    partial = validate_bass_schema(pd.DataFrame({"PI": [1]}))
    assert not partial["complete"] and "test_id" in partial["missing_required"]
    assert validate_bass_schema(pd.DataFrame({"x": [1]}))["n_recognised"] == 0


def test_documents():
    document = docx.Document()
    for i in range(40):
        document.add_paragraph(f"Sentence number {i} about flames burning in a test chamber for the check.")
    buffer = io.BytesIO()
    document.save(buffer)
    chunks, info = chunk_uploaded_document("t.docx", buffer.getvalue())
    assert chunks and chunks[0]["doc_title"] == "Uploaded: t.docx" and chunks[0]["source_id"] == ""

    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_textbox(pymupdf.Rect(72, 72, 520, 720), " ".join(f"word{i}" for i in range(80)), fontsize=10)
    chunks, info = chunk_uploaded_document("t.pdf", pdf.tobytes())
    assert chunks and info["n_pages"] == 1 and chunks[0]["page"] == 1

    assert raises_value_error(chunk_uploaded_document, "t.txt", b"x")
    assert raises_value_error(chunk_uploaded_document, "t.pdf", b"not a pdf")


if __name__ == "__main__":
    test_reading()
    test_reports()
    test_cleaning()
    test_bass_schema()
    test_documents()
    print("all data tools tests passed")
"""Reading, checking, cleaning and exporting user-supplied files (Data Management page).

Values are never invented or imputed. Every change is written to a log.
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pymupdf

from src.data_loader import COLUMN_MAP, REQUIRED_CSV_COLUMNS, _rename_columns
from src.document_processor import chunk_blocks, chunk_pages, clean_text, extract_docx_blocks

MAX_BYTES = 50 * 1024 * 1024
MIN_PAGE_WORDS = 8


def _extension(name: str) -> str:
    return name.lower().rsplit(".", 1)[-1] if "." in name else ""


def _tidy_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen: dict[str, int] = {}
    names = []
    for col in df.columns:
        name = " ".join(str(col).replace("\ufeff", "").split()) or "unnamed"
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    out = df.copy()
    out.columns = names
    return out


def _read_csv(data: bytes, notes: list[str]) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(data), dtype=str, sep=None, engine="python",
                             encoding=encoding, keep_default_na=False, na_values=[""])
        except UnicodeDecodeError:
            continue
        except (pd.errors.ParserError, pd.errors.EmptyDataError, csv.Error) as exc:
            raise ValueError(f"Could not read the CSV file: {exc}") from exc
        if encoding != "utf-8-sig":
            notes.append("The file was not valid UTF-8 and was read as Latin-1; check special characters.")
        return df.replace(r"^\s*$", np.nan, regex=True)
    raise ValueError("Could not decode the CSV file.")


def _read_json(data: bytes, notes: list[str]) -> pd.DataFrame:
    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise ValueError("The JSON file is not valid UTF-8 text.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"The file is not valid JSON: {exc}") from exc

    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        lists = [k for k, v in payload.items()
                 if isinstance(v, list) and v and all(isinstance(i, dict) for i in v)]
        if len(lists) == 1:
            records = payload[lists[0]]
            notes.append(f"Used the list stored under the key '{lists[0]}'.")
        elif len(lists) > 1:
            raise ValueError("The JSON object holds several lists of records; upload one list per file.")
        elif payload and all(isinstance(v, list) for v in payload.values()):
            try:
                return pd.DataFrame(payload)
            except ValueError as exc:
                raise ValueError("The JSON columns have different lengths.") from exc
        else:
            records = [payload]
            notes.append("The JSON object was read as a single record.")
    else:
        raise ValueError("JSON must be a list of records or an object that holds one.")

    if not records:
        raise ValueError("The JSON file holds no records.")
    if not all(isinstance(r, dict) for r in records):
        raise ValueError("Every JSON record must be an object with named fields.")
    return pd.json_normalize(records)


def _read_xlsx(data: bytes, notes: list[str]) -> pd.DataFrame:
    try:
        book = pd.ExcelFile(io.BytesIO(data), engine="openpyxl")
        first = book.sheet_names[0]
        df = book.parse(first, dtype=str)
    except Exception as exc:  # unreadable upload: report it, do not crash the page
        raise ValueError(f"Could not read the Excel file: {exc}") from exc
    if len(book.sheet_names) > 1:
        notes.append(f"Only the first sheet ('{first}') was read; the file has {len(book.sheet_names)} sheets.")
    return df.replace(r"^\s*$", np.nan, regex=True)


def read_table(name: str, data: bytes) -> tuple[pd.DataFrame, list[str]]:
    """Read an uploaded CSV, JSON or XLSX file. CSV and Excel values stay as text."""
    if not data:
        raise ValueError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError("The file is larger than 50 MB; please upload a smaller file.")
    notes: list[str] = []
    extension = _extension(name)
    if extension == "csv":
        df = _read_csv(data, notes)
    elif extension == "json":
        df = _read_json(data, notes)
    elif extension == "xlsx":
        df = _read_xlsx(data, notes)
    else:
        raise ValueError(f"Unsupported file type '.{extension}'. Use CSV, JSON or XLSX.")
    if df.empty:
        raise ValueError("The file has no data rows.")
    return _tidy_columns(df), notes


def table_summary(df: pd.DataFrame) -> dict:
    return {"rows": int(len(df)), "columns": int(len(df.columns)),
            "empty_rows": int(df.isna().all(axis=1).sum()),
            "empty_columns": int(df.isna().all(axis=0).sum()),
            "duplicate_rows": int(df.astype(str).duplicated().sum()),
            "missing_cells": int(df.isna().sum().sum())}


def column_report(df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    rows = []
    for col in df.columns:
        series = df[col]
        present = series.dropna()
        missing = int(series.isna().sum())
        rows.append({"Column": col, "Type": str(series.dtype), "Non-missing": n - missing,
                     "Missing": missing, "Missing (%)": round(100 * missing / n, 1) if n else 0.0,
                     "Distinct values": int(present.astype(str).nunique()),
                     "First value": "" if present.empty else str(present.iloc[0])[:40]})
    return pd.DataFrame(rows)


def validate_bass_schema(df: pd.DataFrame) -> dict:
    """Layout check only: does the table have the columns of the PSI-25 experimental table?"""
    renamed = _rename_columns(df)
    known = set(COLUMN_MAP.values())
    recognised = sorted(c for c in renamed.columns if c in known)
    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in renamed.columns]
    return {"n_recognised": len(recognised), "recognised": recognised,
            "missing_required": missing, "complete": not missing}


def clean_table(df: pd.DataFrame, trim_text: bool = True, drop_empty_rows: bool = True,
                drop_empty_columns: bool = True, drop_duplicates: bool = False,
                numeric_columns=(), drop_missing_in=()) -> tuple[pd.DataFrame, list[str]]:
    """Apply the chosen cleaning steps in a fixed order. Nothing is filled in or estimated."""
    out = df.copy()
    log: list[str] = []
    before = len(out)

    if trim_text:
        for col in out.columns:
            if out[col].dtype == object:
                out[col] = out[col].map(lambda v: v.strip() if isinstance(v, str) else v)
        out = out.replace(r"^$", np.nan, regex=True)
        log.append("Trimmed spaces around text and treated blank cells as missing.")

    for col in numeric_columns:
        if col not in out.columns:
            continue
        original = out[col]
        text = original.where(original.isna(), original.astype(str).str.strip())
        converted = pd.to_numeric(text, errors="coerce")
        lost = original.notna() & converted.isna()
        if lost.any():
            examples = ", ".join(sorted({str(v) for v in original[lost]})[:5])
            out[f"{col}_original_text"] = original.where(lost)
            log.append(f"'{col}': {int(lost.sum())} value(s) are not numbers and became missing "
                       f"(kept in '{col}_original_text'); examples: {examples}.")
        else:
            log.append(f"'{col}': all values were converted to numbers.")
        out[col] = converted

    if drop_empty_rows:
        mask = out.isna().all(axis=1)
        if mask.any():
            out = out.loc[~mask]
            log.append(f"Removed {int(mask.sum())} completely empty row(s).")
    if drop_empty_columns:
        empty = [c for c in out.columns if out[c].isna().all()]
        if empty:
            out = out.drop(columns=empty)
            log.append(f"Removed {len(empty)} completely empty column(s): {', '.join(map(str, empty))}.")

    chosen = [c for c in drop_missing_in if c in out.columns]
    if chosen:
        mask = out[chosen].isna().any(axis=1)
        if mask.any():
            out = out.loc[~mask]
            log.append(f"Removed {int(mask.sum())} row(s) with no value in: {', '.join(chosen)}.")

    if drop_duplicates:
        dup = out.astype(str).duplicated()
        if dup.any():
            out = out.loc[~dup]
            log.append(f"Removed {int(dup.sum())} exact duplicate row(s).")

    out = out.reset_index(drop=True)
    log.append(f"Rows: {before} before, {len(out)} after.")
    return out, log


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def to_json_bytes(df: pd.DataFrame) -> bytes:
    return df.to_json(orient="records", force_ascii=False, indent=2, date_format="iso").encode("utf-8")


def metadata_bytes(file_name: str, source_name: str, source_link: str, notes: str,
                   original_shape: tuple, final_shape: tuple, log: list[str]) -> bytes:
    info = {"file": file_name, "source": source_name or "not recorded",
            "source_link_or_doi": source_link or "not recorded", "notes": notes or "",
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rows_columns_before": list(original_shape), "rows_columns_after": list(final_shape),
            "operations": log,
            "disclaimer": "User-supplied data processed with FLARE Intelligence; not verified by FLARE."}
    return json.dumps(info, ensure_ascii=False, indent=2).encode("utf-8")


def chunk_uploaded_document(name: str, data: bytes) -> tuple[list[dict], dict]:
    """Extract text from an uploaded PDF or Word file and cut it into citable chunks."""
    if not data:
        raise ValueError(f"'{name}' is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError(f"'{name}' is larger than 50 MB.")
    extension = _extension(name)
    slug = re.sub(r"\W+", "-", name.rsplit(".", 1)[0].lower()).strip("-") or "document"
    meta = {"doc_id": f"upload-{slug}", "title": f"Uploaded: {name}", "source_id": "", "file": name}
    info = {"file": name, "n_pages": None, "n_chunks": 0, "n_words": 0, "pages_without_text": 0}
    try:
        if extension == "pdf":
            pages = []
            with pymupdf.open(stream=data, filetype="pdf") as doc:
                for number, page in enumerate(doc, start=1):
                    pages.append((number, clean_text(page.get_text())))
            info["n_pages"] = len(pages)
            info["pages_without_text"] = sum(1 for _, t in pages if len(t.split()) < MIN_PAGE_WORDS)
            chunks = chunk_pages(pages, meta)
        elif extension == "docx":
            chunks = chunk_blocks(extract_docx_blocks(io.BytesIO(data)), meta)
        else:
            raise ValueError(f"Unsupported document type '.{extension}'. Use PDF or DOCX.")
    except ValueError:
        raise
    except Exception as exc:  # unreadable upload: report it, do not crash the page
        raise ValueError(f"Could not read '{name}': {exc}") from exc
    if not chunks:
        raise ValueError(f"No extractable text found in '{name}'. Scanned documents need OCR, "
                         "which this app does not do.")
    info["n_chunks"] = len(chunks)
    info["n_words"] = sum(c["n_words"] for c in chunks)
    return chunks, info
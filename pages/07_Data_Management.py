import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re

import numpy as np
import pandas as pd
import streamlit as st

from src.data_tools import (chunk_uploaded_document, clean_table, column_report, metadata_bytes,
                            read_table, table_summary, to_csv_bytes, to_json_bytes, validate_bass_schema)
from src.flame_analysis import DATA_LIMITATIONS
from src.preprocessing import NUMERIC_COLUMNS, classify_value
from src.theme import header, panel, panel_title, section_title, stat_cards
from src.ui import PSI_URL, ROOT, doi_url, load_all, log_activity

PREVIEW_ROWS = 200
SAVE_DIR = ROOT / "data" / "processed" / "uploads"
DISPLAY_COLUMNS = ["test_id", "pi", "date_raw", "gmt_day_raw", "sample_id", "fuel_text",
                   "flow_restrictor_raw", "fan_display_raw", "air_display_raw", "radiometer_gain_raw",
                   "total_frames_raw", "o2_initial_raw", "o2_final_raw", "co2_initial_raw", "co2_final_raw",
                   "co_initial_raw", "co_final_raw", "quality_flags"]


# ----------------------------------------------------------------------------
# Tab 1: NASA data
# ----------------------------------------------------------------------------
def render_builtin(data) -> None:
    df = data["df"]
    if df.empty:
        st.warning("The PSI-25 experimental table is not loaded.")
        for message in data["errors"]:
            st.text(message)
        return

    stat_cards([
        ("flask", len(df), "Tests", "in the PSI-25 table", "orange"),
        ("shield", int((df["quality_flags"] != "").sum()), "Flagged tests", "with quality flags", "red"),
        ("layers", len(df.columns), "Columns", "in the cleaned table", "blue"),
    ])

    section_title("Experimental table", "values shown as written", "database")
    st.dataframe(df[[c for c in DISPLAY_COLUMNS if c in df.columns]], hide_index=True)
    st.caption("Source: PSI-25 experimental table (BASS-II). The flags column is added by FLARE.")

    c1, c2 = st.columns(2)
    with c1:
        with panel("missing_cols"):
            panel_title("Missing values by column", "search", "orange")
            raw_cols = ["pi", "test_id", "fuel_text"] + [c for c in df.columns if c.endswith("_raw")]
            st.dataframe(column_report(df[raw_cols].replace("", np.nan)), hide_index=True)
    with c2:
        with panel("storage_kinds"):
            panel_title("How the reading columns are stored", "layers", "purple")
            rows = []
            for raw_col in NUMERIC_COLUMNS:
                if raw_col in df.columns:
                    kinds = df[raw_col].map(classify_value).value_counts()
                    rows.append({"Column": raw_col, **{k: int(kinds.get(k, 0)) for k in
                                 ["numeric", "missing", "none", "over_range", "text"]}})
            st.dataframe(pd.DataFrame(rows), hide_index=True)
            st.caption("numeric = a clean number; none = the source says 'none'; over_range = 'OR' or 'over'; "
                       "text = other text such as '>500'; missing = blank. Only clean numbers enter "
                       "calculations.")

    section_title("Download", "", "download")
    d1, d2, d3 = st.columns(3)
    d1.download_button("Cleaned table (CSV)", to_csv_bytes(df), file_name="flare_bass_ii_clean.csv",
                       mime="text/csv")
    d2.download_button("Cleaned table (JSON)", to_json_bytes(df), file_name="flare_bass_ii_clean.json",
                       mime="application/json")
    d3.download_button("Flagged tests only (CSV)", to_csv_bytes(df[df["quality_flags"] != ""]),
                       file_name="flare_bass_ii_flagged.csv", mime="text/csv")


# ----------------------------------------------------------------------------
# Tab 2: Upload a table
# ----------------------------------------------------------------------------
def render_upload() -> None:
    st.write("Upload a CSV, JSON or Excel file to preview it, check its columns and missing values, clean it "
             "and export the result. Nothing is guessed or filled in.")
    file = st.file_uploader("Data file (CSV, JSON or XLSX, up to 50 MB)", type=["csv", "json", "xlsx"],
                            key="table_upload")
    if file is None:
        st.info("No file selected.")
        return
    try:
        table, notes = read_table(file.name, file.getvalue())
    except ValueError as exc:
        st.error(str(exc))
        return
    key = re.sub(r"\W+", "_", file.name)
    base = Path(file.name).stem
    safe_base = re.sub(r"[^\w.\-]+", "_", base)
    log_activity(f"Opened {file.name} in Data Management")
    for note in notes:
        st.caption(note)

    # 1. Source information
    with panel("up_source"):
        panel_title("1. Source information", "book", "blue")
        c1, c2 = st.columns(2)
        source_name = c1.text_input("Source (organisation, dataset or paper)", key=f"src_{key}")
        source_link = c2.text_input("URL or DOI", key=f"lnk_{key}")
        source_notes = st.text_input("Notes (optional)", key=f"note_{key}")
        if not (source_name or source_link):
            st.warning("No source recorded. Exports will say 'not recorded'. Uploaded data is not verified "
                       "by FLARE.")

    # 2. Preview and summary
    summary = table_summary(table)
    stat_cards([
        ("layers", summary["rows"], "Rows", "in the file", "orange"),
        ("database", summary["columns"], "Columns", "in the file", "blue"),
        ("clock", summary["empty_rows"], "Empty rows", "no values at all", "purple"),
        ("users", summary["duplicate_rows"], "Duplicate rows", "exact copies", "green"),
        ("search", summary["missing_cells"], "Missing cells", "blank values", "red"),
    ])
    with panel("up_preview"):
        panel_title("2. Preview", "search", "orange")
        st.dataframe(table.head(PREVIEW_ROWS), hide_index=True)
        st.caption(f"Showing the first {min(PREVIEW_ROWS, len(table))} of {len(table)} rows.")

    # 3 and 4. Columns, layout check
    with panel("up_columns"):
        panel_title("3. Columns and missing values", "chart", "purple")
        st.dataframe(column_report(table), hide_index=True)

    with panel("up_schema"):
        panel_title("4. Layout check against the BASS-II table", "shield", "green")
        check = validate_bass_schema(table)
        if check["n_recognised"] == 0:
            st.info("No column matches the PSI-25 experimental table, so this is treated as a general table.")
        elif check["complete"]:
            st.success("All required BASS-II columns were found. This checks the layout only, not the values, "
                       "and your file is not merged with the NASA table.")
        else:
            st.warning("Some columns match the PSI-25 layout, but these required ones are missing: "
                       + ", ".join(check["missing_required"]))

    # 5. Clean
    with panel("up_clean"):
        panel_title("5. Clean", "sparkles", "orange")
        o1, o2 = st.columns(2)
        trim = o1.checkbox("Trim spaces and treat blank cells as missing", value=True, key=f"trim_{key}")
        drop_rows = o1.checkbox("Remove completely empty rows", value=True, key=f"rows_{key}")
        drop_cols = o2.checkbox("Remove completely empty columns", value=True, key=f"cols_{key}")
        drop_dups = o2.checkbox("Remove exact duplicate rows", value=False, key=f"dups_{key}")
        numeric = st.multiselect("Convert these columns to numbers", list(table.columns), key=f"num_{key}")
        need = st.multiselect("Remove rows that have no value in these columns", list(table.columns),
                              key=f"need_{key}")
        cleaned, log = clean_table(table, trim_text=trim, drop_empty_rows=drop_rows,
                                   drop_empty_columns=drop_cols, drop_duplicates=drop_dups,
                                   numeric_columns=numeric, drop_missing_in=need)
        with st.expander("What was done", expanded=True):
            for line in log:
                st.write(f"- {line}")
        st.dataframe(cleaned.head(PREVIEW_ROWS), hide_index=True)

    # 6. Export
    with panel("up_export"):
        panel_title("6. Export", "download", "green")
        e1, e2, e3 = st.columns(3)
        e1.download_button("Processed data (CSV)", to_csv_bytes(cleaned),
                           file_name=f"{safe_base}_processed.csv", mime="text/csv", key=f"dl_csv_{key}")
        e2.download_button("Processed data (JSON)", to_json_bytes(cleaned),
                           file_name=f"{safe_base}_processed.json", mime="application/json",
                           key=f"dl_json_{key}")
        e3.download_button("Source and operations log (JSON)",
                           metadata_bytes(file.name, source_name, source_link, source_notes,
                                          (len(table), len(table.columns)),
                                          (len(cleaned), len(cleaned.columns)), log),
                           file_name=f"{safe_base}_source_metadata.json", mime="application/json",
                           key=f"dl_meta_{key}")
        if st.button("Save a copy in data/processed/uploads on this computer", key=f"save_{key}"):
            try:
                SAVE_DIR.mkdir(parents=True, exist_ok=True)
                target = SAVE_DIR / f"{safe_base}_processed.csv"
                target.write_bytes(to_csv_bytes(cleaned))
                st.success(f"Saved to {target}")
            except OSError as exc:
                st.error(f"Could not save the file: {exc}")
            st.caption("On a hosted app (for example Streamlit Community Cloud) saved files are temporary.")


# ----------------------------------------------------------------------------
# Tab 3: Import documents
# ----------------------------------------------------------------------------
def render_documents() -> None:
    st.write("Import PDF or Word documents. Their text is cut into passages that the AI Research Assistant can "
             "search during this session. Uploaded documents are labelled 'Uploaded' and are not treated as "
             "verified NASA sources.")
    files = st.file_uploader("Documents (PDF or DOCX)", type=["pdf", "docx"], accept_multiple_files=True,
                             key="doc_upload")
    if not files:
        current = st.session_state.get("uploaded_chunks", [])
        if current:
            st.info(f"{len(current)} passages from earlier uploads are still available to the assistant.")
            if st.button("Remove imported documents"):
                st.session_state["uploaded_chunks"] = []
                st.rerun()
        else:
            st.info("No documents imported.")
        return
    all_chunks, rows = [], []
    for f in files:
        try:
            chunks, info = chunk_uploaded_document(f.name, f.getvalue())
        except ValueError as exc:
            st.error(str(exc))
            continue
        all_chunks.extend(chunks)
        rows.append({"File": info["file"], "Pages": info["n_pages"] if info["n_pages"] is not None else "n/a",
                     "Passages": info["n_chunks"], "Words": info["n_words"],
                     "Pages without text": info["pages_without_text"]})
    if rows:
        st.session_state["uploaded_chunks"] = all_chunks
        log_activity(f"Imported {len(rows)} document(s)")
        with panel("doc_result"):
            panel_title("Imported documents", "book", "blue")
            st.dataframe(pd.DataFrame(rows), hide_index=True)
            st.success("The text was extracted. Open the AI Research Assistant to ask questions about it.")
            with st.expander("Preview of the first passage"):
                st.write(all_chunks[0]["text"][:1200])
            st.caption("Word files have no page numbers; their passages are located by paragraph range.")


# ----------------------------------------------------------------------------
# Tab 4: Sources and metadata
# ----------------------------------------------------------------------------
def render_sources(data) -> None:
    registry, study, pubs = data["registry"], data["study"], data["pubs"]

    section_title("Source registry", "research/nasa_sources.csv", "database")
    if registry.empty:
        st.info("The source registry is empty.")
    else:
        wanted = [c for c in ["source_id", "title", "type", "identifier", "doi", "status", "url", "notes"]
                  if c in registry.columns]
        config = {"url": st.column_config.LinkColumn("URL")} if "url" in wanted else None
        st.dataframe(registry[wanted], hide_index=True, column_config=config)

    if study:
        section_title("PSI-25 study record", "from the metadata file", "flask")
        labels = [("study_id", "Study identifier"), ("title", "Title"), ("acronym", "Acronym"),
                  ("dataset_doi", "Dataset DOI"), ("flight_platform", "Flight platform"),
                  ("hardware", "Hardware"), ("managing_center", "Managing NASA center"),
                  ("research_area", "Research area")]
        st.dataframe(pd.DataFrame([(label, study.get(key) or "Not available") for key, label in labels],
                                  columns=["Field", "Value"]), hide_index=True)
        if study.get("dataset_doi"):
            st.markdown(f"[Dataset DOI link]({doi_url(study['dataset_doi'])})  |  [PSI-25 page]({PSI_URL})")

    if not pubs.empty:
        with st.expander(f"Publications listed in the PSI-25 metadata ({len(pubs)})"):
            shown = pubs.assign(doi_link=pubs["doi"].map(doi_url))
            st.dataframe(shown[["title", "authors", "doi_link", "link"]], hide_index=True,
                         column_config={"doi_link": st.column_config.LinkColumn("DOI link"),
                                        "link": st.column_config.LinkColumn("Other link")})

    section_title("Data limitations", "", "shield")
    st.dataframe(pd.DataFrame(DATA_LIMITATIONS).rename(columns={"text": "Limitation", "source": "Source"}),
                 hide_index=True)


# ----------------------------------------------------------------------------
# Page
# ----------------------------------------------------------------------------
data = load_all()
header("Data Management",
       "Inspect the NASA data, import your own files, check them, clean them and export the result.")
st.info("Files you upload stay in this session. They are not merged into the NASA dataset and are not treated "
        "as NASA sources.")

t1, t2, t3, t4 = st.tabs(["NASA data", "Upload a table", "Import documents", "Sources and metadata"])
with t1:
    render_builtin(data)
with t2:
    render_upload()
with t3:
    render_documents()
with t4:
    render_sources(data)
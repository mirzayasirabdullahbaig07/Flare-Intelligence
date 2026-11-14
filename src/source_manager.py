"""Source registry and PSI-25 metadata parsing. Reads only files that exist on disk."""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES_CSV = PROJECT_ROOT / "research" / "nasa_sources.csv"
METADATA_ZIP = (PROJECT_ROOT / "data" / "raw" / "bass-ii"
                / "PSI-25_metadata_PSI_metadata_PSI-101_BASS-II.zip")
INVESTIGATION_FILE = "i_Investigation.txt"
SOURCE_COLUMNS = ["source_id", "title", "type", "identifier", "doi", "url", "status", "notes"]


def load_source_registry(path: Path = SOURCES_CSV) -> pd.DataFrame:
    """Read research/nasa_sources.csv. Returns an empty table if it is missing."""
    if not Path(path).exists():
        return pd.DataFrame(columns=SOURCE_COLUMNS)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def citation_label(source_id: str, registry: pd.DataFrame, location: str = "") -> str:
    """Human-readable citation, e.g. 'Title (NTRS 2021...), page 12'."""
    match = registry[registry["source_id"] == source_id] if not registry.empty else registry
    if match.empty:
        label = source_id or "unregistered source"
    else:
        row = match.iloc[0]
        label = f"{row['title']} ({row['identifier']})"
    return f"{label}, {location}" if location else label


def parse_isa_tab(text: str) -> dict[str, list[str]]:
    """Parse a tab-separated PSI/ISA-Tab file into {label: [values]}.
    Quoted multi-line fields (hypothesis, objective) are kept whole."""
    fields: dict[str, list[str]] = {}
    for row in csv.reader(io.StringIO(text, newline=""), delimiter="\t"):
        if not row or not row[0].strip():
            continue
        fields.setdefault(row[0].strip(), [v.strip() for v in row[1:]])
    return fields


def load_investigation(zip_path: Path = METADATA_ZIP) -> dict[str, list[str]]:
    """Read i_Investigation.txt straight from the metadata zip."""
    if not Path(zip_path).exists():
        raise FileNotFoundError(f"Metadata zip not found: {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        if INVESTIGATION_FILE not in archive.namelist():
            raise FileNotFoundError(f"{INVESTIGATION_FILE} not inside {zip_path}")
        text = archive.read(INVESTIGATION_FILE).decode("utf-8-sig", errors="replace")
    return parse_isa_tab(text)


def _first(fields: dict[str, list[str]], label: str) -> str:
    values = fields.get(label, [])
    return values[0] if values else ""


def get_study_overview(fields: dict[str, list[str]]) -> dict[str, str]:
    """Official study facts exactly as written in the PSI metadata (no contacts)."""
    return {
        "study_id": _first(fields, "Study Identifier"),
        "title": _first(fields, "Study Title"),
        "acronym": _first(fields, "Comment[Investigation Acronym]"),
        "dataset_doi": _first(fields, "Comment[DOI]"),
        "flight_platform": _first(fields, "Comment[Flight Platform]"),
        "hardware": _first(fields, "Comment[Experiment Hardware]"),
        "managing_center": _first(fields, "Comment[Managing NASA Center]"),
        "research_area": _first(fields, "Comment[Research Area]"),
        "approach": _first(fields, "Comment[Approach]"),
        "hypothesis": _first(fields, "Comment[Hypothesis]"),
        "objective": _first(fields, "Comment[Objective]"),
        "research_impacts": _first(fields, "Comment[Research Impacts]"),
    }


def get_publications(fields: dict[str, list[str]]) -> pd.DataFrame:
    """Publication list from the metadata, aligned by position."""
    titles = fields.get("Study Publication Title", [])
    n = len(titles)

    def column(label: str) -> list[str]:
        values = list(fields.get(label, []))
        return (values + [""] * n)[:n]

    table = pd.DataFrame({
        "title": titles,
        "authors": column("Study Publication Author List"),
        "doi": column("Study Publication DOI"),
        "link": column("Comment[Study Publication Link]"),
    })
    return table[table["title"] != ""].reset_index(drop=True)



def overview_chunks(overview: dict[str, str]) -> list[dict]:
    """Turn the PSI-25 study overview into citable chunks (text as written by NASA)."""
    parts = [
        ("approach", "Approach"),
        ("hypothesis", "Hypothesis (as stated by the investigators)"),
        ("objective", "Objectives"),
        ("research_impacts", "Research impacts (as stated in the PSI record)"),
    ]
    chunks = []
    for key, label in parts:
        text = " ".join(overview.get(key, "").split())
        if not text:
            continue
        chunks.append({
            "chunk_id": f"psi25-metadata-{key}",
            "doc_id": "psi25-metadata",
            "doc_title": "PSI-25 investigation metadata",
            "source_id": "psi-25",
            "file": "i_Investigation.txt (inside the PSI-25 metadata zip)",
            "page": None,
            "location": f"metadata field: {label}",
            "text": f"{label}: {text}",
            "n_words": len(text.split()),
        })
    return chunks
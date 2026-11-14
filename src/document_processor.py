"""Extract text from NASA documents and cut it into citable chunks.

PDF chunks never cross a page boundary, so every chunk has an exact page number.
Word files have no page numbers; their chunks are located by paragraph range.
No OCR is done: pages that are only images give no text and are reported.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_DIR = PROJECT_ROOT / "data" / "raw" / "documents"
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"

CHUNK_WORDS = 180
OVERLAP_WORDS = 40
MIN_WORDS = 8

# Citation info per downloaded file. SRD is not expanded: we do not assume what it stands for.
DOCUMENT_REGISTRY = {
    "BASS-II Summary Report.pdf": {
        "doc_id": "bass2-summary-report", "title": "BASS-II Summary Report",
        "source_id": "ntrs-20210011385"},
    "SRD_BASS-II.pdf": {
        "doc_id": "bass2-srd", "title": "SRD_BASS-II (PSI-25 Science Documents)",
        "source_id": "psi-25"},
    "BASS-II data FAQ.docx": {
        "doc_id": "bass2-faq", "title": "BASS-II data FAQ (PSI-25)", "source_id": "psi-25"},
    "BASS-II Procedure.docx": {
        "doc_id": "bass2-procedure", "title": "BASS-II Procedure (PSI-25)", "source_id": "psi-25"},
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00ad", "")).strip()


def extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    pages = []
    with pymupdf.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            pages.append((number, clean_text(page.get_text())))
    return pages


def extract_docx_blocks(path: Path) -> list[str]:
    """Paragraphs and table rows in document order."""
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(path)
    blocks: list[str] = []
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            text = clean_text(Paragraph(child, document).text)
            if text:
                blocks.append(text)
        elif child.tag.endswith("}tbl"):
            for row in Table(child, document).rows:
                cells = list(dict.fromkeys(clean_text(c.text) for c in row.cells))
                line = " | ".join(c for c in cells if c)
                if line:
                    blocks.append(line)
    return blocks


def _windows(words: list[str], size: int, overlap: int):
    start = 0
    while start < len(words):
        yield words[start:start + size]
        if start + size >= len(words):
            break
        start += size - overlap


def _chunk(meta: dict, chunk_id: str, location: str, page, words: list[str]) -> dict:
    return {"chunk_id": chunk_id, "doc_id": meta["doc_id"], "doc_title": meta["title"],
            "source_id": meta["source_id"], "file": meta["file"], "page": page,
            "location": location, "text": " ".join(words), "n_words": len(words)}


def chunk_pages(pages, meta, size=CHUNK_WORDS, overlap=OVERLAP_WORDS, min_words=MIN_WORDS):
    chunks = []
    for page_no, text in pages:
        words = text.split()
        if len(words) < min_words:
            continue
        for part, window in enumerate(_windows(words, size, overlap), start=1):
            chunks.append(_chunk(meta, f"{meta['doc_id']}-p{page_no}-{part}",
                                 f"page {page_no}", page_no, window))
    return chunks


def chunk_blocks(blocks, meta, size=CHUNK_WORDS, min_words=MIN_WORDS):
    chunks, buffer, start_idx, number = [], [], 1, 0
    for idx, block in enumerate(blocks, start=1):
        if not buffer:
            start_idx = idx
        buffer.append(block)
        words = " ".join(buffer).split()
        if len(words) >= size or idx == len(blocks):
            if len(words) >= min_words:
                number += 1
                chunks.append(_chunk(meta, f"{meta['doc_id']}-b{number}",
                                     f"paragraphs {start_idx}-{idx}", None, words))
            buffer = []
    return chunks


def process_document(path: Path) -> tuple[list[dict], dict]:
    path = Path(path)
    default = {"doc_id": re.sub(r"\W+", "-", path.stem.lower()), "title": path.stem, "source_id": ""}
    meta = {**DOCUMENT_REGISTRY.get(path.name, default), "file": path.name}
    info = {"file": path.name, "n_pages": None, "n_chunks": 0, "n_words": 0,
            "pages_without_text": [], "first_page_preview": ""}

    if path.suffix.lower() == ".pdf":
        pages = extract_pdf_pages(path)
        info["n_pages"] = len(pages)
        info["pages_without_text"] = [n for n, t in pages if len(t.split()) < MIN_WORDS]
        info["first_page_preview"] = pages[0][1][:200] if pages else ""
        chunks = chunk_pages(pages, meta)
    elif path.suffix.lower() == ".docx":
        blocks = extract_docx_blocks(path)
        info["first_page_preview"] = blocks[0][:200] if blocks else ""
        chunks = chunk_blocks(blocks, meta)
    else:
        return [], info

    info["n_chunks"] = len(chunks)
    info["n_words"] = sum(c["n_words"] for c in chunks)
    return chunks, info


def build_corpus(doc_dir: Path = DOCUMENT_DIR) -> tuple[list[dict], list[dict]]:
    if not Path(doc_dir).exists():
        raise FileNotFoundError(f"Document folder not found: {doc_dir}")
    all_chunks, report = [], []
    for path in sorted(Path(doc_dir).iterdir()):
        if path.suffix.lower() in {".pdf", ".docx"}:
            chunks, info = process_document(path)
            all_chunks.extend(chunks)
            report.append(info)
    return all_chunks, report


def save_chunks(chunks: list[dict], path: Path = CHUNKS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return path


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
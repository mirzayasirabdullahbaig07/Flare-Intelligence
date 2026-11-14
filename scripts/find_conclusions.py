"""Find conclusion-like pages in the Summary Report, or print given pages.
Usage:  python scripts/find_conclusions.py            (list candidate pages)
        python scripts/find_conclusions.py 120 121   (print the full text of those PDF pages)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.document_processor import load_chunks

DOC_ID = "bass2-summary-report"
HEADING = re.compile(r"\b(conclusions?|summary|findings|key results?|lessons learned|recommendations?)\b", re.I)


def main() -> None:
    chunks = [c for c in load_chunks() if c["doc_id"] == DOC_ID]
    if not chunks:
        print("STOP: no chunks. Run scripts/build_chunks.py first.")
        return
    pages = sys.argv[1:]
    if pages:
        for page in pages:
            parts = [c for c in chunks if str(c["page"]) == page]
            print(f"\n===== PDF page {page} ({len(parts)} chunk(s)) =====")
            for c in parts:
                print(c["text"])
        return
    print("Pages whose beginning mentions a conclusion-like heading:")
    for c in chunks:
        if c["chunk_id"].endswith("-1") and HEADING.search(c["text"][:160]):
            print(f"  PDF page {c['page']}: {c['text'][:160]}")


if __name__ == "__main__":
    main()
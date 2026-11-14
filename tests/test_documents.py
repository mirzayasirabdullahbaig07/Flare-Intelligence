"""Run: python tests/test_documents.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.document_processor import chunk_blocks, chunk_pages
from src.source_manager import get_publications, parse_isa_tab

META = {"doc_id": "demo", "title": "Demo", "source_id": "x", "file": "demo.pdf"}


def test_isa_parser():
    text = ('Study Identifier\tPSI-25\n'
            'Comment[Hypothesis]\t"line one\nline two"\n'
            'Study Publication Title\tA\tB\n'
            'Study Publication DOI\t10.1/x\n')
    fields = parse_isa_tab(text)
    assert fields["Study Identifier"] == ["PSI-25"]
    assert fields["Comment[Hypothesis]"] == ["line one\nline two"]
    pubs = get_publications(fields)
    assert len(pubs) == 2 and pubs.loc[0, "doi"] == "10.1/x" and pubs.loc[1, "doi"] == ""


def test_page_chunks():
    words = " ".join(f"w{i}" for i in range(400))
    chunks = chunk_pages([(1, words), (2, "too short")], META)
    assert len(chunks) == 3
    assert all(c["page"] == 1 for c in chunks)
    assert chunks[0]["n_words"] == 180


def test_block_chunks():
    blocks = ["alpha beta gamma delta epsilon zeta eta theta iota kappa"] * 40
    chunks = chunk_blocks(blocks, META)
    assert chunks and chunks[0]["location"].startswith("paragraphs 1-")
    assert sum(c["n_words"] for c in chunks) == 400


if __name__ == "__main__":
    test_isa_parser()
    test_page_chunks()
    test_block_chunks()
    print("all document tests passed")
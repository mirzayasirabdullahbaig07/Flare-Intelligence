"""Extra logic tests (toy text, not NASA data). Run: python tests/test_rag2.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.rag_engine import Retriever, answer_question, clean_sentence, expand_query

REGISTRY = pd.DataFrame(columns=["source_id", "title", "identifier"])


def _chunk(cid, text):
    return {"chunk_id": cid, "doc_title": "Toy " + cid, "source_id": "x", "file": cid + ".pdf",
            "location": "page 1", "page": 1, "text": text}


CHUNKS = [
    _chunk("c1", "The main limitations of this method are the small sample size and the short test duration in the glovebox."),
    _chunk("c2", "The experiment was performed aboard the station using a small wind tunnel with a fan."),
    _chunk("c3", "This research describes the experiment and the research goals in general terms for readers."),
]


def test_reference_entry_rejected():
    ref = "Chan, Ryan Lesley: Effect of Oxygen Concentration on Flame Spread Over Thin Fuels in Different Regimes: A Numerical Investigation."
    assert clean_sentence(ref) is None


def test_key_term_must_be_in_sentence():
    result = answer_question("What are the limitations?", Retriever(CHUNKS), REGISTRY)
    assert result["evidence"] == "sufficient"
    assert result["sentences"] and all("limitations" in s["text"].lower() for s in result["sentences"])


def test_expansion_terms():
    assert expand_query("What did it hypothesize?")[1] == ["hypothesis"]
    assert expand_query("What was investigated?")[1] == ["objectives"]


def test_result_has_label_and_key_terms():
    result = answer_question("What are the limitations?", Retriever(CHUNKS), REGISTRY)
    assert "not a generated answer" in result["label"] and "limitations" in result["key_terms"]


if __name__ == "__main__":
    test_reference_entry_rejected()
    test_key_term_must_be_in_sentence()
    test_expansion_terms()
    test_result_has_label_and_key_terms()
    print("all rag2 tests passed")
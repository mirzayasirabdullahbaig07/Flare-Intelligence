"""Logic tests. Toy passages are NOT NASA data. Run: python tests/test_rag.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.rag_engine import Retriever, answer_question, clean_sentence, expand_query, list_ollama_models

EMPTY_REGISTRY = pd.DataFrame(columns=["source_id", "title", "identifier"])


def _chunk(cid, text):
    return {"chunk_id": cid, "doc_title": "Toy Doc " + cid, "source_id": "x", "file": cid + ".pdf",
            "location": "page 1", "page": 1, "text": text}


CHUNKS = [
    _chunk("a", "Flames burning in microgravity are rounder and dimmer because there is no buoyancy. "
                "Low flow speed produces a stable dim blue flame in the test chamber."),
    _chunk("b", "The wind tunnel fan voltage was recorded from the video display during every test run. "
                "Sensor readings were taken before and after each burn."),
]


def test_relevant_chunk_first():
    hits = Retriever(CHUNKS).search("flame shape in microgravity", k=2)
    assert hits and hits[0].chunk["chunk_id"] == "a"


def test_irrelevant_question_is_insufficient():
    result = answer_question("Who won the football world cup?", Retriever(CHUNKS), EMPTY_REGISTRY)
    assert result["evidence"] == "insufficient"
    assert "do not contain enough information" in result["answer"]


def test_relevant_question_has_sources():
    result = answer_question("How do flames behave in microgravity?", Retriever(CHUNKS), EMPTY_REGISTRY)
    assert result["evidence"] == "sufficient" and result["sources"]
    assert "Toy Doc a" in result["sources"][0]["label"]


def test_unknown_name_is_reported():
    result = answer_question("What is the purpose of the SAFFIRE experiments?",
                             Retriever(CHUNKS), EMPTY_REGISTRY)
    assert result["evidence"] == "insufficient" and "SAFFIRE" in result["note"]


def test_empty_corpus_does_not_crash():
    assert Retriever([]).search("anything") == []
    assert answer_question("anything", Retriever([]), EMPTY_REGISTRY)["evidence"] == "insufficient"


def test_no_llm_is_fine():
    assert list_ollama_models("http://127.0.0.1:9", timeout=1) == []


def test_sentence_filter():
    table = "21.0 20.8 20.1 19.9 0.33 0.43 0 22 Spread at 10 cm/s, did not blowoff 7/2/14 GMT 183 --------- 51 B16 150m"
    broken = "A simplified scale analysis produces a closed-form expression ( ) ( ) ("
    reference = ("Marcum, Jeremy; Olson, Sandra; and Ferkul, Paul: Mixed Convection Blowoff Limits as a "
                 "Function of Oxygen Concentration and Upward Forced Stretch Rate for Burning PMMA Rods of Various Sizes.")
    assert clean_sentence(table) is None
    assert clean_sentence(broken) is None
    assert clean_sentence(reference) is None
    heading = ("NASA/TM-20210011385 60 5.4 Oxygen Concentration Analysis The BASS hardware does not have "
               "a provision to measure O2 concentration throughout the entire experiment.")
    assert clean_sentence(heading).startswith("Oxygen Concentration Analysis")
    good = ("Primary variables: The main variables to be tested are the effects of ambient oxygen "
            "concentration, ventilation flow velocity, and fuel type, thickness, and geometry.")
    assert clean_sentence(good) == good


def test_expansion():
    query, extras = expand_query("What can this suggest for future habitats?")
    assert "spacecraft" in query and extras == ["spacecraft"]


if __name__ == "__main__":
    test_relevant_chunk_first()
    test_irrelevant_question_is_insufficient()
    test_relevant_question_has_sources()
    test_unknown_name_is_reported()
    test_empty_corpus_does_not_crash()
    test_no_llm_is_fine()
    test_sentence_filter()
    test_expansion()
    print("all rag tests passed")
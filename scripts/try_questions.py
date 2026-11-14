"""Ask test questions against the REAL documents and show scores, so we can tune honestly."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.document_processor import load_chunks
from src.rag_engine import Retriever, answer_question
from src.source_manager import load_source_registry

QUESTIONS = [
    "How does microgravity affect flame behaviour?",
    "What was investigated in BASS-II?",
    "What were the objectives of BASS-II?",
    "What did BASS-II hypothesize about burning in microgravity?",
    "What is the purpose of the SAFFIRE experiments?",
    "What are the limitations of current microgravity combustion research?",
    "What can these findings suggest for future space habitats?",
    "How does oxygen concentration affect extinction of PMMA?",
    "Who won the football world cup?",
    "What is the capital of France?",
]


def main() -> None:
    chunks = load_chunks()
    if not chunks:
        print("STOP: no chunks found. Run scripts/build_chunks.py first.")
        return
    retriever = Retriever(chunks)
    registry = load_source_registry()
    print(f"{len(chunks)} chunks loaded\n")
    for q in QUESTIONS:
        r = answer_question(q, retriever, registry)
        print("=" * 80)
        print(f"Q: {q}\n   evidence={r['evidence']}  top_score={r['top_score']}  coverage={r['coverage']}")
        if r["expanded_with"]:
            print(f"   search also used: {r['expanded_with']}")
        if r["note"]:
            print(f"   note: {r['note']}")
        print(r["answer"][:900])
        for s in r["sources"][:3]:
            print(f"   [{s['n']}] score={s['score']}  {s['label']}")


if __name__ == "__main__":
    main()
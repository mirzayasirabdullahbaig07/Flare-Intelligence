"""Run the assistant page through the app on the real documents. Run: python tests/test_assistant_page.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from src.document_processor import CHUNKS_PATH

PAGE = "pages/04_AI_Research_Assistant.py"


def ask(question: str) -> dict:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    at.switch_page(PAGE)
    at.session_state["question_text"] = question
    at.session_state["run_now"] = True
    at.run()
    assert not at.exception, [str(e.value)[:300] for e in at.exception]
    assert "last_result" in at.session_state, (
        "the page did not store an answer; if the page was redesigned, check that it still "
        "uses the session keys 'question_text', 'run_now' and 'last_result'")
    return at.session_state["last_result"]


def main() -> None:
    if not CHUNKS_PATH.exists():
        print("STOP: run scripts/build_chunks.py first.")
        return
    result = ask("What were the objectives of BASS-II?")
    assert result["evidence"] == "sufficient" and result["sources"], result["evidence"]
    result = ask("Who won the football world cup?")
    assert result["evidence"] == "insufficient", result["evidence"]
    result = ask("What is the purpose of the SAFFIRE experiments?")
    assert result["evidence"] == "insufficient" and "SAFFIRE" in result["note"]
    print("all assistant page tests passed")


if __name__ == "__main__":
    main()
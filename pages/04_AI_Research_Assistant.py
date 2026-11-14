import sys
from collections import Counter
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.document_processor import CHUNKS_PATH, load_chunks
from src.rag_engine import Retriever, answer_question, list_ollama_models
from src.theme import card, header, insight, panel, panel_title, section_title, stat_cards
from src.ui import load_all, log_activity

EXAMPLES = [
    "What were the objectives of BASS-II?",
    "What did BASS-II hypothesize about burning in microgravity?",
    "How does oxygen concentration affect extinction of PMMA?",
    "What are the limitations of current microgravity combustion research?",
]

HOW_ANSWERS_ARE_MADE = [
    "The question is matched against passages of the documents with TF-IDF (word statistics). "
    "No generated text is used by default.",
    "The answer is a few sentences copied word for word from the best passages, each marked with "
    "the source it came from.",
    "If a name in the question never appears in the documents, or the best match is weak, the "
    "assistant says the documents do not contain enough information.",
    "The score shown is word-overlap similarity. It is not the probability that an answer is correct.",
]


def chunks_mtime() -> float:
    return CHUNKS_PATH.stat().st_mtime if CHUNKS_PATH.exists() else 0.0


@st.cache_resource(show_spinner="Indexing the documents...")
def get_retriever(mtime: float) -> Retriever:
    return Retriever(load_chunks())


def set_question(text: str) -> None:
    st.session_state["question_text"] = text
    st.session_state["run_now"] = True


def safe(text: str) -> str:
    """Stop '$' in PDF text from being read as a formula."""
    return str(text).replace("$", "\\$")


data = load_all()
registry = data["registry"]
uploaded = st.session_state.get("uploaded_chunks", [])
retriever = Retriever(load_chunks() + uploaded) if uploaded else get_retriever(chunks_mtime())

header("AI Research Assistant",
       "Ask questions about the BASS-II documents. Answers are built only from the loaded NASA "
       "documents and always come with their sources.")

if not retriever.chunks:
    st.warning("No document text is loaded, so the assistant has nothing to search. "
               "Nothing is answered from outside knowledge.")
    st.markdown("Create the document index first:")
    st.code("python scripts/build_chunks.py")
    st.stop()

per_doc = Counter(c["doc_title"] for c in retriever.chunks)
stats_slot = st.empty()          # filled in below, after a new question has been handled
st.write("")

with st.expander(f"Documents the assistant can search ({len(per_doc)} sources, {len(retriever.chunks)} passages)"):
    for title, n in per_doc.most_common():
        st.write(f"{title}: {n} passages")
    st.caption("SAFFIRE documents are not loaded yet, so SAFFIRE questions cannot be answered. "
               "Page numbers are PDF page numbers; in the Summary Report the printed report page "
               "number is 8 lower.")

with st.expander("How answers are made"):
    st.markdown("\n".join(f"- {line}" for line in HOW_ANSWERS_ARE_MADE))

use_llm, model = False, None
with st.expander("Optional: local language model (Ollama)"):
    use_llm = st.checkbox("Rewrite the answer with a local model (off by default)", value=False)
    if use_llm:
        models = list_ollama_models()
        if models:
            model = st.selectbox("Local model", models)
            st.caption("The model is told to use only the retrieved passages; check its answer against the sources.")
        else:
            st.info("No local model is running on this computer, so the sentences copied from the "
                    "documents are shown instead. This feature needs no account and no paid API.")

# ---------------------------------------------------------------- ask
section_title("Ask a question", "", "bot")
with panel("ask"):
    panel_title("Example questions", "sparkles", "orange")
    cols = st.columns(len(EXAMPLES))
    for col, example in zip(cols, EXAMPLES):
        col.button(example, on_click=set_question, args=(example,), use_container_width=True)
    st.write("")
    with st.form("ask_form", border=False):
        st.text_input("Your question", key="question_text")
        submitted = st.form_submit_button("Ask", icon=":material/search:")

run_now = st.session_state.pop("run_now", False)
question = st.session_state.get("question_text", "").strip()
if (submitted or run_now) and question:
    result = answer_question(question, retriever, registry, use_llm=use_llm, model=model)
    st.session_state["last_result"] = result
    st.session_state.setdefault("qa_history", []).append((question, result["evidence"]))
    log_activity(f"Asked the assistant: {question[:60]}")

history = st.session_state.get("qa_history", [])
with stats_slot.container():
    stat_cards([
        ("book", len(per_doc), "Sources", "documents loaded", "blue"),
        ("layers", len(retriever.chunks), "Passages", "searchable text chunks", "purple"),
        ("bot", len(history), "Questions", "asked in this session", "orange"),
    ])

# ---------------------------------------------------------------- answer
result = st.session_state.get("last_result")
if result:
    st.write("")
    with panel("answer"):
        panel_title("Answer", "bulb", "green" if result["evidence"] == "sufficient" else "orange")
        st.caption(f"Question: {result['question']}")
        if result["evidence"] == "sufficient":
            st.caption(result["label"])
            st.markdown(safe(result["answer"]))
        elif result["evidence"] == "passages_only":
            st.info(result["answer"])
        else:
            st.warning(result["answer"])
        if result["note"]:
            st.caption(result["note"])
        if result["expanded_with"]:
            st.caption("The search also used these related words: " + ", ".join(result["expanded_with"])
                       + " (a small word list defined in the app; not part of the answer).")
        st.caption(f"Best match score {result['top_score']} (word-overlap similarity, not a probability); "
                   f"share of question words found in the top passages: {result['coverage']}.")

    sources = result["sources"]
    if sources:
        weak = result["evidence"] == "insufficient"
        section_title("Closest passages (weak matches, not an answer)" if weak else "Sources", "",
                      "book")
        for s in sources:
            flag = " (weak match)" if s["low_relevance"] else ""
            with st.expander(f"[{s['n']}] {s['label']}  |  score {s['score']}{flag}"):
                st.caption(f"{s['registry_ref']}  |  file: {s['file']}")
                st.markdown(safe(s["text"]))

if len(history) > 1:
    st.write("")
    with st.expander("Questions asked in this session"):
        for q, evidence in reversed(history[:-1]):
            st.write(f"{q}  ({evidence})")
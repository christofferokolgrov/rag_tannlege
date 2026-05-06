import streamlit as st

from tannhelse.config import DB_PATH
from tannhelse.llm import chat as llm_chat
from tannhelse.prompts import build_messages, format_kontekst, parse_citations
from tannhelse.retrieval import retrieve
from tannhelse.store import Store

st.set_page_config(page_title="Tannhelse RAG", page_icon=None)
st.title("Tannhelse RAG")


@st.cache_resource
def _store() -> Store:
    return Store(DB_PATH)


store = _store()

if not DB_PATH.exists() or store.count_chunks() == 0:
    st.info("Ingen dokumenter er ingestert ennå. Kjør `uv run python ingest.py` først.")
    st.chat_input("Still et spørsmål…", disabled=True)
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

query = st.chat_input("Still et spørsmål…")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Henter kontekst og svarer…"):
            chunks = retrieve(query, store)
            kontekst = format_kontekst(chunks)
            messages = build_messages(
                history=st.session_state.messages[:-1],
                kontekst=kontekst,
                query=query,
            )
            answer = llm_chat(messages)
            kilder = parse_citations(answer, chunks)
            full = answer if not kilder else f"{answer}\n\n{kilder}"
        st.markdown(full)

    st.session_state.messages.append({"role": "assistant", "content": full})

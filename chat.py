import os

import streamlit as st

# Streamlit Cloud puts secrets in st.secrets, but tannhelse.config reads
# os.environ at import time. Bridge before the tannhelse imports below.
_required = ("OPENAI_API_KEY", "DEEPSEEK_API_KEY")
_visible_secrets: list[str] = []
try:
    _visible_secrets = list(st.secrets.keys())
except Exception:
    pass

for _key in _required:
    if os.environ.get(_key):
        continue
    try:
        os.environ[_key] = str(st.secrets[_key])
    except Exception:
        pass

_missing = [k for k in _required if not os.environ.get(k)]
if _missing:
    st.set_page_config(page_title="Tannhelse RAG", page_icon=None)
    st.error(
        f"Mangler API-nøkler: {', '.join(_missing)}.\n\n"
        f"Synlige secrets-nøkler: {_visible_secrets or '(ingen — st.secrets er tom)'}\n\n"
        "Legg dem inn under Settings → Secrets i Streamlit Cloud (TOML-format, "
        "én nøkkel per linje, anførselstegn rundt verdien)."
    )
    st.stop()

from tannhelse.config import DB_PATH
from tannhelse.llm import stream_chat
from tannhelse.prompts import build_messages, parse_citations
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
        with st.spinner("Henter kontekst…"):
            chunks = retrieve(query, store)
            messages = build_messages(
                history=st.session_state.messages[:-1],
                kontekst_chunks=chunks,
                query=query,
            )

        # Lazy: only pay the ~12s `import openai` cost when the user actually
        # submits a query, not on page load.
        import openai

        try:
            answer = st.write_stream(stream_chat(messages))
        except openai.APIError as exc:
            st.error(f"Feil under svar fra modellen: {exc}")
            # Drop the user turn we appended so chat input stays usable
            # without polluting history with a half-finished exchange.
            st.session_state.messages.pop()
            st.stop()

        kilder = parse_citations(answer, chunks)
        full = answer if not kilder else f"{answer}\n\n{kilder}"
        if kilder:
            st.markdown(kilder)

    st.session_state.messages.append({"role": "assistant", "content": full})

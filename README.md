# Tannhelse RAG

Local Python RAG system for Norwegian dental-sector regulatory research.
See issue #1 (PRD) for scope; this is the tracer-bullet end-to-end pipeline (issue #2).

## First-run

```bash
uv sync
cp .env.example .env  # fill in DEEPSEEK_API_KEY and OPENAI_API_KEY
uv run python ingest.py
uv run streamlit run chat.py
```

PDFs go in `docs/corpus/`. The chat UI opens at `http://localhost:8501`.

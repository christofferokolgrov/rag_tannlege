from tannhelse.config import EMBEDDING_MODEL, OPENAI_API_KEY

_BATCH_SIZE = 100


def _client():
    # Lazy import: see tannhelse/llm.py for the rationale.
    from openai import OpenAI

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env.")
    return OpenAI(api_key=OPENAI_API_KEY)


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = _client()
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        out.extend(d.embedding for d in resp.data)
    return out

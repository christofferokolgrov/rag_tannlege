from tannhelse.config import TOP_K_GLOBAL
from tannhelse.embedding import embed_texts
from tannhelse.store import Store


def retrieve(query: str, store: Store) -> list:
    """Tracer-bullet: dense-only top-15. Hybrid + doc routing arrive in #5/#6."""
    [query_vec] = embed_texts([query])
    return store.dense_search(query_vec, k=TOP_K_GLOBAL)

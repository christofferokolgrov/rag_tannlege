import sys

from tannhelse.config import RRF_K, TOP_K_GLOBAL, TOP_K_PER_DOC, TOP_K_PER_RETRIEVER
from tannhelse.embedding import embed_texts
from tannhelse.store import Store


def rrf_merge(rankings, k: int = RRF_K, top: int = TOP_K_GLOBAL):
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    counter = 0
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            if chunk_id not in first_seen:
                first_seen[chunk_id] = counter
                counter += 1
    ordered = sorted(
        scores,
        key=lambda cid: (-scores[cid], first_seen[cid]),
    )
    return ordered[:top]


def detect_documents(query: str, known_documents: list[str]) -> list[str]:
    query_lower = query.lower()
    return [doc for doc in known_documents if doc.lower() in query_lower]


def _hybrid_search(query: str, query_vec, store, k_per_retriever, top, documents=None):
    dense_hits = store.dense_search(query_vec, k=k_per_retriever, documents=documents)

    if store.fts_count() == 0:
        print(
            "warning: chunks_fts is empty; falling back to dense-only retrieval. "
            "Run `uv run python ingest.py` to populate the BM25 index.",
            file=sys.stderr,
        )
        return dense_hits[:top]

    bm25_hits = store.bm25_search(query, k=k_per_retriever, documents=documents)

    by_id = {c.chunk_id: c for c in dense_hits}
    by_id.update({c.chunk_id: c for c in bm25_hits})

    merged_ids = rrf_merge(
        [[c.chunk_id for c in dense_hits], [c.chunk_id for c in bm25_hits]],
        k=RRF_K,
        top=top,
    )
    return [by_id[cid] for cid in merged_ids]


def retrieve(query: str, store: Store) -> list:
    [query_vec] = embed_texts([query])

    known_documents = [doc for doc, _ in store.list_documents()]
    matched = detect_documents(query, known_documents)

    if matched:
        results = []
        for doc in matched:
            results.extend(
                _hybrid_search(
                    query,
                    query_vec,
                    store,
                    k_per_retriever=TOP_K_PER_RETRIEVER,
                    top=TOP_K_PER_DOC,
                    documents=[doc],
                )
            )
        return results

    return _hybrid_search(
        query,
        query_vec,
        store,
        k_per_retriever=TOP_K_PER_RETRIEVER,
        top=TOP_K_GLOBAL,
    )

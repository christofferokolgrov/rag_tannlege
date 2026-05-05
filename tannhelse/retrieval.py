import sys

from tannhelse.config import RRF_K, TOP_K_GLOBAL, TOP_K_PER_RETRIEVER
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


def retrieve(query: str, store: Store) -> list:
    [query_vec] = embed_texts([query])
    dense_hits = store.dense_search(query_vec, k=TOP_K_PER_RETRIEVER)

    if store.fts_count() == 0:
        print(
            "warning: chunks_fts is empty; falling back to dense-only retrieval. "
            "Run `uv run python ingest.py` to populate the BM25 index.",
            file=sys.stderr,
        )
        return dense_hits[:TOP_K_GLOBAL]

    bm25_hits = store.bm25_search(query, k=TOP_K_PER_RETRIEVER)

    by_id = {c.chunk_id: c for c in dense_hits}
    by_id.update({c.chunk_id: c for c in bm25_hits})

    merged_ids = rrf_merge(
        [[c.chunk_id for c in dense_hits], [c.chunk_id for c in bm25_hits]],
        k=RRF_K,
        top=TOP_K_GLOBAL,
    )
    return [by_id[cid] for cid in merged_ids]

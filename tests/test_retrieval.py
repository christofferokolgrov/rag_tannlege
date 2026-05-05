import pytest

from tannhelse.chunking import Chunk
from tannhelse.config import EMBEDDING_DIM, TOP_K_GLOBAL, TOP_K_PER_DOC
from tannhelse.retrieval import detect_documents, retrieve, rrf_merge
from tannhelse.store import Store


def test_empty_input_returns_empty_list():
    assert rrf_merge([]) == []


def test_single_ranking_returned_in_order_truncated_to_top():
    assert rrf_merge([["a", "b", "c", "d"]], top=2) == ["a", "b"]


def test_two_disjoint_rankings_both_contribute_with_rank_aligned_pairs():
    result = rrf_merge([["a", "b"], ["c", "d"]])
    # Rank-0 chunks (a, c) outrank rank-1 chunks (b, d)
    assert set(result[:2]) == {"a", "c"}
    assert set(result[2:]) == {"b", "d"}


def test_identical_rankings_produce_doubled_score_in_same_order():
    assert rrf_merge([["a", "b", "c"], ["a", "b", "c"]]) == ["a", "b", "c"]


def test_partial_overlap_shared_chunk_ranks_highest():
    # "b" appears in both lists; should outrank chunks that appear in only one
    result = rrf_merge([["a", "b", "c"], ["b", "x"]])
    assert result[0] == "b"


def test_truncation_respects_top_parameter():
    rankings = [list("abcdefghij"), list("klmnopqrst")]
    assert len(rrf_merge(rankings, top=5)) == 5


def test_detect_documents_returns_empty_when_no_short_title_in_query():
    assert detect_documents("Hvilke aktører har uttalt seg?", ["SV", "Rødt"]) == []


def test_detect_documents_matches_single_short_title():
    assert detect_documents(
        "Hva foreslår NOU 2024-18 om finansiering?",
        ["NOU 2024-18", "SV"],
    ) == ["NOU 2024-18"]


def test_detect_documents_matches_multiple_short_titles():
    matches = detect_documents(
        "Hva skiller SV og Rødts forslag?",
        ["SV", "Rødt", "NOU 2024-18"],
    )
    assert set(matches) == {"SV", "Rødt"}


def test_detect_documents_is_case_insensitive():
    assert detect_documents("snakk om sv her", ["SV"]) == ["SV"]
    assert detect_documents("snakk om Sv her", ["SV"]) == ["SV"]
    assert detect_documents("snakk om SV her", ["sv"]) == ["sv"]


def test_detect_documents_preserves_known_document_order():
    # Stable order regardless of where each name appears in the query.
    result = detect_documents(
        "Rødt og SV begge nevnt",
        ["SV", "Rødt"],
    )
    assert result == ["SV", "Rødt"]


# ---------------------------------------------------------------------------
# Integration tests for retrieve(): hybrid search, RRF fusion, doc routing.
#
# Each test seeds a fresh sqlite-vec store with hand-crafted chunks and
# one-hot embedding vectors so dense kNN is deterministic. The OpenAI
# embedder is monkeypatched per-test via tannhelse.retrieval.embed_texts.
# ---------------------------------------------------------------------------


def _one_hot(index: int) -> list[float]:
    """A 1536-dim vector with a single 1.0 at `index`. Orthogonal one-hots
    have squared-L2 distance 2; identical one-hots distance 0."""
    vec = [0.0] * EMBEDDING_DIM
    vec[index] = 1.0
    return vec


def _make_chunk(
    chunk_id: str,
    document: str,
    text: str,
    *,
    chunk_index: int = 0,
    section_label: str = "Section",
    section_path: str = "1",
    page_start: int = 1,
    page_end: int = 1,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document=document,
        source_path=f"/fake/{document}.pdf",
        content_hash="hash-" + chunk_id,
        chunk_index=chunk_index,
        section_path=section_path,
        section_label=section_label,
        page_start=page_start,
        page_end=page_end,
        text=text,
    )


def _seeded_store(tmp_path, chunks_with_vectors: list[tuple[Chunk, list[float]]]) -> Store:
    """Build a Store on a temp-file DB and upsert the given (chunk, vec) pairs."""
    db_path = tmp_path / "store.db"
    store = Store(db_path)
    chunks = [c for c, _ in chunks_with_vectors]
    vecs = [v for _, v in chunks_with_vectors]
    store.upsert_chunks(chunks, vecs)
    return store


def _patch_query_vec(monkeypatch, vec: list[float]) -> None:
    """Replace tannhelse.retrieval.embed_texts so retrieve() returns `vec`
    for any query, with no network call."""
    monkeypatch.setattr(
        "tannhelse.retrieval.embed_texts",
        lambda texts: [vec for _ in texts],
    )


def test_retrieve_routes_to_single_document_when_query_mentions_short_title(
    tmp_path, monkeypatch
):
    # Seed: 5 chunks in "SV", 5 in "Rødt". Each chunk text mentions a unique
    # token "topicfoo" so BM25 has something to find. Vectors orthogonal to
    # the query vector so dense returns deterministic order by chunk_id-tie.
    chunks = []
    for i in range(5):
        chunks.append(
            (
                _make_chunk(f"sv-{i}", "SV", f"SV chunk {i} topicfoo content"),
                _one_hot(i % 10 + 100),
            )
        )
    for i in range(5):
        chunks.append(
            (
                _make_chunk(f"rodt-{i}", "Rødt", f"Rødt chunk {i} topicfoo content"),
                _one_hot(i % 10 + 200),
            )
        )
    store = _seeded_store(tmp_path, chunks)
    _patch_query_vec(monkeypatch, _one_hot(0))

    results = retrieve("Hva sier SV om topicfoo?", store)

    assert len(results) > 0
    assert len(results) <= TOP_K_PER_DOC
    assert all(c.document == "SV" for c in results), [c.document for c in results]
    store.close()


def test_retrieve_routes_to_multiple_documents_when_query_mentions_two_short_titles(
    tmp_path, monkeypatch
):
    # Seed three docs; query mentions two of them. Each doc gets enough
    # chunks that the per-doc cap (TOP_K_PER_DOC=8) could be reached.
    chunks = []
    for i in range(10):
        chunks.append(
            (
                _make_chunk(f"sv-{i}", "SV", f"SV chunk {i} alphaword"),
                _one_hot(100 + i),
            )
        )
    for i in range(10):
        chunks.append(
            (
                _make_chunk(f"rodt-{i}", "Rødt", f"Rødt chunk {i} alphaword"),
                _one_hot(200 + i),
            )
        )
    for i in range(5):
        chunks.append(
            (
                _make_chunk(f"nou-{i}", "NOU", f"NOU chunk {i} alphaword"),
                _one_hot(300 + i),
            )
        )
    store = _seeded_store(tmp_path, chunks)
    _patch_query_vec(monkeypatch, _one_hot(0))

    results = retrieve("Sammenlign SV og Rødt om alphaword", store)

    docs = [c.document for c in results]
    # Multi-doc routing concatenates per-doc results (up to TOP_K_PER_DOC each).
    assert "SV" in docs
    assert "Rødt" in docs
    assert "NOU" not in docs
    assert docs.count("SV") <= TOP_K_PER_DOC
    assert docs.count("Rødt") <= TOP_K_PER_DOC
    store.close()


def test_retrieve_falls_back_to_global_top_k_when_no_document_mentioned(
    tmp_path, monkeypatch
):
    # Seed 12 chunks across 2 docs (less than TOP_K_GLOBAL=15) so we can
    # assert the fallback path returned chunks from any document.
    chunks = []
    for i in range(6):
        chunks.append(
            (
                _make_chunk(f"sv-{i}", "SV", f"SV chunk {i} sharedtoken"),
                _one_hot(100 + i),
            )
        )
    for i in range(6):
        chunks.append(
            (
                _make_chunk(f"rodt-{i}", "Rødt", f"Rødt chunk {i} sharedtoken"),
                _one_hot(200 + i),
            )
        )
    store = _seeded_store(tmp_path, chunks)
    _patch_query_vec(monkeypatch, _one_hot(0))

    # Query mentions no known short_title so routing falls back to global.
    results = retrieve("Hvilke aktører nevner sharedtoken?", store)

    assert len(results) <= TOP_K_GLOBAL
    # Fallback path: chunks may come from any document.
    docs_seen = {c.document for c in results}
    assert docs_seen.issubset({"SV", "Rødt"})
    # The seeded corpus has 12 chunks and TOP_K_GLOBAL=15, so the global
    # fallback should surface every chunk that matched at all (BM25 returns
    # all chunks containing "sharedtoken").
    assert len(results) == 12
    store.close()


@pytest.mark.parametrize("query_form", ["sv", "SV", "Sv", "sV"])
def test_retrieve_document_routing_is_case_insensitive(
    tmp_path, monkeypatch, query_form
):
    chunks = [
        (_make_chunk("sv-0", "SV", "SV chunk zero topic"), _one_hot(100)),
        (_make_chunk("sv-1", "SV", "SV chunk one topic"), _one_hot(101)),
        (_make_chunk("rodt-0", "Rødt", "Rødt chunk zero topic"), _one_hot(200)),
        (_make_chunk("rodt-1", "Rødt", "Rødt chunk one topic"), _one_hot(201)),
    ]
    store = _seeded_store(tmp_path, chunks)
    _patch_query_vec(monkeypatch, _one_hot(0))

    results = retrieve(f"Hva mener {query_form} om topic?", store)

    assert len(results) > 0
    assert all(c.document == "SV" for c in results), (
        f"Query form {query_form!r} routed to {[c.document for c in results]}"
    )
    store.close()


def test_rrf_fusion_merges_disjoint_dense_and_bm25_top_results(
    tmp_path, monkeypatch
):
    # Construct a single-document corpus where dense top-1 and BM25 top-1
    # are disjoint chunks. The fused result must include BOTH.
    #
    # Plan:
    #   - Query embedding = one_hot(0).
    #   - "dense-winner" chunk has vector one_hot(0) (distance 0). Its text
    #     contains NONE of the query tokens, so BM25 ignores it.
    #   - "bm25-winner" chunk has vector one_hot(500) (orthogonal to query)
    #     and its text contains the unique query token "uniquequeryword".
    #   - Filler chunks orthogonal to query and missing the query token.
    chunks = [
        (
            _make_chunk("dense-winner", "DOC", "lorem ipsum dolor"),
            _one_hot(0),
        ),
        (
            _make_chunk(
                "bm25-winner", "DOC", "alpha beta uniquequeryword gamma"
            ),
            _one_hot(500),
        ),
    ]
    for i in range(8):
        chunks.append(
            (
                _make_chunk(f"filler-{i}", "DOC", f"filler text {i} nothing"),
                _one_hot(700 + i),
            )
        )
    store = _seeded_store(tmp_path, chunks)
    _patch_query_vec(monkeypatch, _one_hot(0))

    # Query mentions no short_title → global path; query token only found
    # in the BM25-winner via FTS.
    results = retrieve("uniquequeryword", store)

    result_ids = {c.chunk_id for c in results}
    assert "dense-winner" in result_ids, (
        "dense top-1 should appear in fused results"
    )
    assert "bm25-winner" in result_ids, (
        "bm25 top-1 should appear in fused results"
    )
    store.close()


def test_retrieve_filter_respected_by_both_dense_and_bm25_retrievers(
    tmp_path, monkeypatch
):
    # Two docs. The query routes to "SV" only. The "Rødt" doc contains
    # both:
    #   (a) a chunk whose vector is the dense top match (one_hot(0)), and
    #   (b) a chunk whose text contains the unique BM25 disambiguator.
    # Neither should leak into the routed-to-SV result.
    chunks = [
        # SV — the only document that should appear in results.
        (_make_chunk("sv-0", "SV", "SV alpha beta"), _one_hot(100)),
        (_make_chunk("sv-1", "SV", "SV gamma delta"), _one_hot(101)),
        (_make_chunk("sv-2", "SV", "SV epsilon zeta"), _one_hot(102)),
        # Rødt — must NOT leak in despite winning both dense and BM25.
        (
            _make_chunk("rodt-densewin", "Rødt", "Rødt unrelated body text"),
            _one_hot(0),  # exact match for query vector
        ),
        (
            _make_chunk(
                "rodt-bm25win", "Rødt", "Rødt body bm25marker bm25marker"
            ),
            _one_hot(900),
        ),
    ]
    store = _seeded_store(tmp_path, chunks)
    _patch_query_vec(monkeypatch, _one_hot(0))

    results = retrieve("Hva sier SV om bm25marker?", store)

    docs = [c.document for c in results]
    assert docs, "expected at least one result"
    assert all(d == "SV" for d in docs), (
        f"non-SV chunks leaked into routed result: {docs}"
    )
    result_ids = {c.chunk_id for c in results}
    assert "rodt-densewin" not in result_ids
    assert "rodt-bm25win" not in result_ids
    store.close()

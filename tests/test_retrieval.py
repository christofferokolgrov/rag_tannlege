from tannhelse.retrieval import rrf_merge


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

from tannhelse.retrieval import detect_documents, rrf_merge


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

from types import SimpleNamespace

from tannhelse.prompts import parse_citations


def _chunk(document: str, section_label: str) -> SimpleNamespace:
    return SimpleNamespace(document=document, section_label=section_label)


def test_single_marker_renders_one_source_in_kilder_block():
    chunks = [_chunk(document="NOU 2024-18", section_label="s. 142")]
    answer = "Tannhelsereformen foreslår universell dekning [1]."

    assert parse_citations(answer, chunks) == "Kilder:\n[1] NOU 2024-18, s. 142"


def test_multiple_distinct_markers_listed_in_numeric_order_only_when_cited():
    chunks = [
        _chunk(document="A", section_label="s. 1"),
        _chunk(document="B", section_label="s. 2"),
        _chunk(document="C", section_label="s. 3"),
    ]
    answer = "Først [3]. Så [1]."

    assert parse_citations(answer, chunks) == "Kilder:\n[1] A, s. 1\n[3] C, s. 3"


def test_repeated_marker_listed_once():
    chunks = [_chunk(document="A", section_label="s. 1")]
    answer = "Påstand [1]. En annen påstand [1]."

    assert parse_citations(answer, chunks) == "Kilder:\n[1] A, s. 1"


def test_marker_referencing_unknown_chunk_is_silently_dropped():
    chunks = [_chunk(document="A", section_label="s. 1")]
    answer = "Gyldig [1]. Ugyldig [7]."

    assert parse_citations(answer, chunks) == "Kilder:\n[1] A, s. 1"


def test_no_markers_returns_empty_string():
    chunks: list = []
    answer = "Dette finner jeg ikke i de tilgjengelige dokumentene."

    assert parse_citations(answer, chunks) == ""

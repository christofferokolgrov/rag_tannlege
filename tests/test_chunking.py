from tannhelse.chunking import (
    chunk_spans,
    count_tokens,
    group_spans_by_section,
    split_sentences,
    window_section,
)
from tannhelse.parsing import ParsedSpan


def test_two_sentences_split_on_period_and_capital():
    assert split_sentences("Hei. Hvordan går det.") == ["Hei.", "Hvordan går det."]


def test_text_without_sentence_terminator_returns_single_sentence():
    assert split_sentences("Hei verden") == ["Hei verden"]


def test_ordinal_followed_by_lowercase_word_does_not_split():
    text = "Møtet er 12. mars 2024. Vi treffes der."
    assert split_sentences(text) == [
        "Møtet er 12. mars 2024.",
        "Vi treffes der.",
    ]


def test_question_and_exclamation_split_into_sentences():
    assert split_sentences("Er det sant? Ja!") == ["Er det sant?", "Ja!"]


import pytest


@pytest.mark.parametrize(
    "abbrev",
    ["f.eks.", "bl.a.", "pkt.", "dvs.", "mv."],
)
def test_abbreviation_followed_by_capitalized_noun_does_not_split(abbrev):
    text = f"Vi bruker {abbrev} Tannlegeforeningen som rådgiver."
    assert split_sentences(text) == [text]


def test_short_text_returns_single_chunk_equal_to_input():
    text = "Hei verden. Hvordan går det."
    assert window_section(text, target=100, max_=200, overlap=20) == [text]


def test_long_text_produces_multiple_chunks_each_under_max():
    sentences = [f"Setning nummer {i} her er litt tekst." for i in range(20)]
    text = " ".join(sentences)
    assert count_tokens(text) > 80  # sanity: input must exceed our target

    chunks = window_section(text, target=50, max_=80, overlap=15)

    assert len(chunks) > 1
    for chunk in chunks:
        assert count_tokens(chunk) <= 80


def test_consecutive_chunks_share_at_least_one_sentence():
    sentences = [f"Setning nummer {i} her er litt tekst." for i in range(20)]
    text = " ".join(sentences)

    chunks = window_section(text, target=50, max_=80, overlap=15)

    for prev, nxt in zip(chunks, chunks[1:]):
        prev_sents = set(split_sentences(prev))
        next_sents = set(split_sentences(nxt))
        assert prev_sents & next_sents, "consecutive chunks must share at least one sentence"


def test_consecutive_same_section_spans_concatenate_into_one_group():
    spans = [
        ParsedSpan(text="Første del.", page=1, section_path="8/8.3", section_label="Kap. 8.3 X"),
        ParsedSpan(text="Andre del.", page=2, section_path="8/8.3", section_label="Kap. 8.3 X"),
    ]

    groups = group_spans_by_section(spans)

    assert len(groups) == 1
    g = groups[0]
    assert g.section_path == "8/8.3"
    assert g.section_label == "Kap. 8.3 X"
    assert g.text == "Første del.\nAndre del."
    assert g.page_start == 1
    assert g.page_end == 2


def test_alternating_section_spans_produce_separate_groups_in_order():
    spans = [
        ParsedSpan(text="A1.", page=1, section_path="A", section_label="A"),
        ParsedSpan(text="B1.", page=1, section_path="B", section_label="B"),
        ParsedSpan(text="A2.", page=2, section_path="A", section_label="A"),
    ]

    groups = group_spans_by_section(spans)

    assert [g.section_path for g in groups] == ["A", "B", "A"]
    assert [g.text for g in groups] == ["A1.", "B1.", "A2."]


def test_chunk_spans_short_single_section_yields_one_chunk_with_section_text():
    spans = [
        ParsedSpan(text="Hei verden.", page=1, section_path="A", section_label="Kap. A"),
    ]

    chunks = list(chunk_spans(spans, document="doc", source_path="d.pdf", content_hash="h"))

    assert len(chunks) == 1
    assert chunks[0].text == "Hei verden."
    assert chunks[0].section_path == "A"
    assert chunks[0].section_label == "Kap. A"
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1


def test_chunk_spans_two_adjacent_short_sections_yield_two_chunks_not_merged():
    spans = [
        ParsedSpan(text="Først.", page=1, section_path="A", section_label="A"),
        ParsedSpan(text="Så.", page=1, section_path="B", section_label="B"),
    ]

    chunks = list(chunk_spans(spans, document="doc", source_path="d.pdf", content_hash="h"))

    assert len(chunks) == 2
    assert chunks[0].section_path == "A"
    assert chunks[1].section_path == "B"
    assert chunks[0].text == "Først."
    assert chunks[1].text == "Så."


def test_chunk_spans_long_section_yields_multiple_chunks_each_under_max():
    long_text = " ".join(f"Setning nummer {i} her er litt tekst." for i in range(60))
    spans = [
        ParsedSpan(text=long_text, page=1, section_path="A", section_label="Kap. A"),
    ]

    chunks = list(chunk_spans(spans, document="d", source_path="d.pdf", content_hash="h"))

    assert len(chunks) > 1
    for chunk in chunks:
        assert count_tokens(chunk.text) <= 900
        assert chunk.section_path == "A"
        assert chunk.section_label == "Kap. A"


def test_chunk_spans_chunk_id_is_deterministic_across_calls():
    spans = [
        ParsedSpan(text="Hei.", page=1, section_path="A", section_label="A"),
        ParsedSpan(text="Hei B.", page=1, section_path="B", section_label="B"),
    ]

    first = list(chunk_spans(spans, document="d", source_path="d.pdf", content_hash="h"))
    second = list(chunk_spans(spans, document="d", source_path="d.pdf", content_hash="h"))

    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]
    assert len({c.chunk_id for c in first}) == len(first)  # all distinct

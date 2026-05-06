from types import SimpleNamespace

from tannhelse.prompts import SYSTEM_PROMPT, build_messages, parse_citations


def _chunk(
    document: str,
    section_label: str,
    text: str = "",
    source_path: str | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        document=document,
        section_label=section_label,
        text=text,
        source_path=source_path,
        page_start=page_start,
        page_end=page_end,
    )


def test_single_marker_renders_one_source_in_kilder_block():
    chunks = [_chunk(document="NOU 2024-18", section_label="Kap. 13")]
    answer = "Tannhelsereformen foreslår universell dekning [1]."

    assert parse_citations(answer, chunks) == "**Kilder:**\n[1] NOU 2024-18 — Kap. 13"


def test_multiple_distinct_markers_listed_in_numeric_order_only_when_cited():
    chunks = [
        _chunk(document="A", section_label="s. 1"),
        _chunk(document="B", section_label="s. 2"),
        _chunk(document="C", section_label="s. 3"),
    ]
    answer = "Først [3]. Så [1]."

    assert parse_citations(answer, chunks) == (
        "**Kilder:**\n[1] A — s. 1\n[3] C — s. 3"
    )


def test_repeated_marker_listed_once():
    chunks = [_chunk(document="A", section_label="s. 1")]
    answer = "Påstand [1]. En annen påstand [1]."

    assert parse_citations(answer, chunks) == "**Kilder:**\n[1] A — s. 1"


def test_marker_referencing_unknown_chunk_is_silently_dropped():
    chunks = [_chunk(document="A", section_label="s. 1")]
    answer = "Gyldig [1]. Ugyldig [7]."

    assert parse_citations(answer, chunks) == "**Kilder:**\n[1] A — s. 1"


def test_pages_appended_when_page_range_known():
    chunks = [
        _chunk(
            document="NOU 2024:18",
            section_label="Kap. 13.5",
            source_path="/x/nou.pdf",
            page_start=142,
            page_end=145,
        )
    ]
    answer = "Påstand [1]."

    assert parse_citations(answer, chunks) == (
        "**Kilder:**\n[1] NOU 2024:18 — Kap. 13.5 (s. 142–145)"
    )


def test_single_page_collapses_to_no_dash():
    chunks = [
        _chunk(
            document="NOU 2024:18",
            section_label="Kap. 13.5",
            source_path="/x/nou.pdf",
            page_start=142,
            page_end=142,
        )
    ]
    answer = "Påstand [1]."

    assert parse_citations(answer, chunks) == (
        "**Kilder:**\n[1] NOU 2024:18 — Kap. 13.5 (s. 142)"
    )


def test_url_renders_document_as_markdown_link():
    chunks = [
        _chunk(
            document="NOU 2024:18",
            section_label="Kap. 13",
            source_path="/abs/path/nou.pdf",
            page_start=10,
            page_end=10,
        )
    ]
    answer = "Påstand [1]."
    urls = {"nou.pdf": "https://example.com/nou"}

    assert parse_citations(answer, chunks, urls=urls) == (
        "**Kilder:**\n[1] [NOU 2024:18](https://example.com/nou) — Kap. 13 (s. 10)"
    )


def test_url_lookup_misses_filename_falls_back_to_plain_title():
    chunks = [
        _chunk(
            document="A",
            section_label="s. 1",
            source_path="/x/unknown.pdf",
            page_start=1,
            page_end=1,
        )
    ]
    answer = "[1]."
    urls = {"other.pdf": "https://example.com"}

    assert parse_citations(answer, chunks, urls=urls) == (
        "**Kilder:**\n[1] A — s. 1 (s. 1)"
    )


def test_no_markers_returns_empty_string():
    chunks: list = []
    answer = "Dette finner jeg ikke i de tilgjengelige dokumentene."

    assert parse_citations(answer, chunks) == ""


def test_build_messages_system_prompt_is_always_first():
    chunks = [_chunk(document="A", section_label="s. 1", text="alpha")]

    msgs = build_messages(history=[], kontekst_chunks=chunks, query="Hva?")

    assert msgs[0] == {"role": "system", "content": SYSTEM_PROMPT}


def test_build_messages_empty_history_yields_system_plus_user():
    chunks = [_chunk(document="A", section_label="s. 1", text="alpha")]

    msgs = build_messages(history=[], kontekst_chunks=chunks, query="Hva er X?")

    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert "SPØRSMÅL: Hva er X?" in msgs[1]["content"]


def test_build_messages_kontekst_block_uses_numbered_markers():
    chunks = [
        _chunk(document="A", section_label="s. 1", text="første"),
        _chunk(document="B", section_label="s. 2", text="andre"),
        _chunk(document="C", section_label="s. 3", text="tredje"),
    ]

    msgs = build_messages(history=[], kontekst_chunks=chunks, query="Q")
    user_content = msgs[-1]["content"]

    assert "[1] første" in user_content
    assert "[2] andre" in user_content
    assert "[3] tredje" in user_content
    assert user_content.startswith("KONTEKST:")
    assert "SPØRSMÅL: Q" in user_content


def test_build_messages_truncates_history_to_last_six():
    history = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "u3"},
        {"role": "assistant", "content": "a3"},
        {"role": "user", "content": "u4"},
        {"role": "assistant", "content": "a4"},
    ]

    msgs = build_messages(history=history, kontekst_chunks=[], query="now")

    # system + last 6 history + new user
    assert len(msgs) == 1 + 6 + 1
    assert msgs[0]["role"] == "system"
    middle = msgs[1:-1]
    assert [m["content"] for m in middle] == ["u2", "a2", "u3", "a3", "u4", "a4"]
    assert msgs[-1]["role"] == "user"
    assert "SPØRSMÅL: now" in msgs[-1]["content"]


def test_build_messages_short_history_passes_through():
    history = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
    ]

    msgs = build_messages(history=history, kontekst_chunks=[], query="next")

    assert len(msgs) == 1 + 2 + 1
    assert msgs[1]["content"] == "u1"
    assert msgs[2]["content"] == "a1"

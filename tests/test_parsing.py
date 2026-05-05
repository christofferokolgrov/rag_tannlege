from tannhelse.parsing import is_heading, numeric_heading_path, section_for_heading


def test_single_digit_numeric_heading_returns_single_element_path():
    assert numeric_heading_path("8 Finansiering") == ["8"]


def test_dotted_numeric_heading_returns_hierarchical_path():
    assert numeric_heading_path("8.3 Finansieringsmodell") == ["8", "8.3"]


def test_three_level_numeric_heading_returns_three_element_path():
    assert numeric_heading_path("8.3.1 Detaljbestemmelser") == ["8", "8.3", "8.3.1"]


def test_plain_text_returns_none():
    assert numeric_heading_path("Dette er en setning.") is None


def test_bare_number_without_following_text_returns_none():
    assert numeric_heading_path("8.") is None
    assert numeric_heading_path("8") is None
    assert numeric_heading_path("8 ") is None


def test_numeric_pattern_is_heading_regardless_of_font():
    assert is_heading("8.3 Finansieringsmodell", font_size=10.0, bold=False, page_median=10.0)


def test_oversized_font_is_heading_even_without_numeric_or_bold():
    assert is_heading("Bakgrunn", font_size=12.0, bold=False, page_median=10.0)


def test_font_at_threshold_is_not_heading():
    assert not is_heading("Bakgrunn", font_size=11.4, bold=False, page_median=10.0)


def test_bold_and_short_is_heading():
    assert is_heading("Forslag", font_size=10.0, bold=True, page_median=10.0)


def test_bold_but_long_paragraph_is_not_heading():
    long_text = "Dette er en betydelig lengre tekst som ikke skal regnes som en overskrift selv om den er fet."
    assert not is_heading(long_text, font_size=10.0, bold=True, page_median=10.0)


def test_plain_body_text_is_not_heading():
    assert not is_heading("Vanlig brødtekst.", font_size=10.0, bold=False, page_median=10.0)


def test_toc_entry_with_dot_leaders_is_not_heading_even_if_numeric_prefix():
    text = "8.3 Finansieringsmodell .................................. 142"
    assert not is_heading(text, font_size=10.0, bold=False, page_median=10.0)


def test_bold_short_sentence_ending_with_period_is_not_heading():
    text = "NTF er svært kritisk til den harmoniserte modellen."
    assert not is_heading(text, font_size=10.0, bold=True, page_median=10.0)


def test_pure_numeric_or_punctuation_line_is_not_heading_even_with_oversize_font():
    assert not is_heading("12", font_size=14.0, bold=False, page_median=10.0)
    assert not is_heading("8.3", font_size=14.0, bold=False, page_median=10.0)
    assert not is_heading("1.", font_size=14.0, bold=True, page_median=10.0)


def test_dotted_numeric_heading_renders_path_and_kap_label():
    path, label = section_for_heading("8.3 Finansieringsmodell")
    assert path == "8/8.3"
    assert label == "Kap. 8.3 Finansieringsmodell"


def test_single_level_numeric_heading_uses_single_segment_path():
    path, label = section_for_heading("8 Finansiering")
    assert path == "8"
    assert label == "Kap. 8 Finansiering"


def test_non_numeric_heading_uses_text_as_both_path_and_label():
    path, label = section_for_heading("Bakgrunn")
    assert path == "Bakgrunn"
    assert label == "Bakgrunn"

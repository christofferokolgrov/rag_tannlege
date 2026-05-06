from pathlib import Path

import pytest

from tannhelse.docs_yaml import load_overrides


def test_missing_file_returns_empty_dict(tmp_path):
    assert load_overrides(tmp_path / "does_not_exist.yaml") == {}


def test_valid_file_with_one_entry_returns_parsed_dict(tmp_path):
    yaml_path = tmp_path / "docs.yaml"
    yaml_path.write_text(
        'somefile.pdf:\n'
        '  title: "Den norske tannlegeforening – høringssvar"\n'
        '  short_title: "Tannlegeforeningen"\n',
        encoding="utf-8",
    )
    overrides = load_overrides(yaml_path)
    assert overrides == {
        "somefile.pdf": {
            "title": "Den norske tannlegeforening – høringssvar",
            "short_title": "Tannlegeforeningen",
        }
    }


def test_override_with_url_is_valid(tmp_path):
    yaml_path = tmp_path / "docs.yaml"
    yaml_path.write_text(
        'somefile.pdf:\n'
        '  short_title: "Kort"\n'
        '  url: "https://example.com/doc"\n',
        encoding="utf-8",
    )
    assert load_overrides(yaml_path) == {
        "somefile.pdf": {
            "short_title": "Kort",
            "url": "https://example.com/doc",
        }
    }


def test_override_with_only_short_title_is_valid(tmp_path):
    yaml_path = tmp_path / "docs.yaml"
    yaml_path.write_text(
        'somefile.pdf:\n  short_title: "Kortnavn"\n',
        encoding="utf-8",
    )
    assert load_overrides(yaml_path) == {
        "somefile.pdf": {"short_title": "Kortnavn"}
    }


def test_invalid_yaml_raises_value_error(tmp_path):
    yaml_path = tmp_path / "docs.yaml"
    yaml_path.write_text("a: b: c:\n  - bad: [unclosed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid docs.yaml"):
        load_overrides(yaml_path)


def test_top_level_not_a_dict_raises_value_error(tmp_path):
    yaml_path = tmp_path / "docs.yaml"
    yaml_path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid docs.yaml"):
        load_overrides(yaml_path)


def test_entry_value_not_a_dict_raises_value_error(tmp_path):
    yaml_path = tmp_path / "docs.yaml"
    yaml_path.write_text('somefile.pdf: "just a string"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid docs.yaml"):
        load_overrides(yaml_path)


def test_entry_with_unknown_key_raises_value_error(tmp_path):
    yaml_path = tmp_path / "docs.yaml"
    yaml_path.write_text(
        'somefile.pdf:\n'
        '  short_title: "ok"\n'
        '  unexpected_key: "boom"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid docs.yaml"):
        load_overrides(yaml_path)


def test_empty_file_returns_empty_dict(tmp_path):
    yaml_path = tmp_path / "docs.yaml"
    yaml_path.write_text("", encoding="utf-8")
    assert load_overrides(yaml_path) == {}

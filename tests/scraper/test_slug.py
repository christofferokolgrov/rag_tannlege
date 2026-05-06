import pytest

from scraper.slug import (
    find_id_collisions,
    make_klinikk_id,
    parse_klinikk_id,
    to_slug,
)


def test_to_slug_lowercases_and_underscores_words():
    assert to_slug("Oslo Sentrum") == "oslo_sentrum"


def test_to_slug_norwegian_letters_use_two_letter_form():
    assert to_slug("Hønefoss") == "hoenefoss"
    assert to_slug("Tåsen") == "taasen"
    assert to_slug("Ærlig") == "aerlig"


def test_to_slug_strips_other_diacritics():
    assert to_slug("Café") == "cafe"
    assert to_slug("Müller") == "muller"


def test_to_slug_collapses_hyphens_and_whitespace_to_single_underscore():
    assert to_slug("Linde-rud  AS") == "linde_rud_as"


def test_to_slug_drops_non_alphanumeric():
    assert to_slug("Tannhelse & Co!") == "tannhelse_co"


def test_make_klinikk_id_joins_kjede_and_slug_with_double_underscore():
    assert make_klinikk_id("odontia", "Oslo Sentrum") == "odontia__oslo_sentrum"
    assert make_klinikk_id("oc", "Tåsen") == "oc__taasen"


def test_make_klinikk_id_rejects_unknown_kjede():
    with pytest.raises(ValueError):
        make_klinikk_id("not-a-kjede", "Oslo")


def test_parse_klinikk_id_splits_kjede_and_slug():
    assert parse_klinikk_id("odontia__oslo_sentrum") == ("odontia", "oslo_sentrum")
    assert parse_klinikk_id("oris__central") == ("oris", "central")


def test_parse_klinikk_id_rejects_bad_format():
    with pytest.raises(ValueError):
        parse_klinikk_id("odontia-oslo")
    with pytest.raises(ValueError):
        parse_klinikk_id("tannlegen__oslo")
    with pytest.raises(ValueError):
        parse_klinikk_id("odontia__Oslo")  # uppercase in slug


def test_make_and_parse_klinikk_id_roundtrip():
    name = "Hønefoss Tannklinikk"
    kid = make_klinikk_id("odontia", name)
    assert parse_klinikk_id(kid) == ("odontia", to_slug(name))


def test_find_id_collisions_detects_slugs_that_collapse_to_same_id():
    collisions = find_id_collisions(
        {"odontia": ["Oslo Sentrum", "Oslo-Sentrum", "Bergen"]}
    )
    assert collisions == {"odontia__oslo_sentrum": ["Oslo Sentrum", "Oslo-Sentrum"]}


def test_find_id_collisions_returns_empty_when_unique():
    assert find_id_collisions({"odontia": ["Oslo", "Bergen", "Trondheim"]}) == {}

from pathlib import Path

from scraper.parsers import PriceRow
from scraper.parsers.odontia import parse_clinic, parse_prisliste
from scraper.prisformat import Prisformat

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "html_cache" / "odontia"


def _read(name: str) -> str:
    return (CACHE_DIR / name).read_text(encoding="utf-8")


def test_parse_prisliste_emits_aarlig_kontroll_fixture_row():
    rows = parse_prisliste(_read("oslo_sentrum_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Årlig kontroll hos tannlege"]
    assert len(matches) == 1, [r.behandling_navn_raw for r in rows[:5]]
    row = matches[0]
    assert (row.pris_min, row.pris_max, row.prisformat) == (1595, 1595, Prisformat.FAST)


def test_parse_prisliste_emits_tannfarget_fylling_liten_fixture_row():
    rows = parse_prisliste(_read("oslo_sentrum_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Tannfarget fylling, liten"]
    assert len(matches) == 1
    row = matches[0]
    assert (row.pris_min, row.pris_max, row.prisformat) == (950, 1545, Prisformat.SPREAD)


def test_parse_prisliste_returns_PriceRow_instances():
    rows = parse_prisliste(_read("oslo_sentrum_prisliste.html"))
    assert rows
    assert all(isinstance(r, PriceRow) for r in rows)


def test_parse_clinic_extracts_address_postnummer_by():
    info = parse_clinic(_read("oslo_sentrum_klinikk.html"))
    assert info["adresse"] == "Skippergata 33"
    assert info["postnummer"] == "0154"
    assert info["by"] == "Oslo"


def test_parse_prisliste_extracts_footnote_into_ekskluderer_raw():
    rows = parse_prisliste(_read("oslo_sentrum_prisliste.html"))
    aarlig = next(r for r in rows if r.behandling_navn_raw == "Årlig kontroll hos tannlege")
    # Page has <div class="small-text">Ved behov for utvidet røntgen eller
    # videre behandling vil dette tilkomme prisen.</div> in cell 0.
    assert "tilkomme prisen" in aarlig.ekskluderer_raw
    assert aarlig.inkluderer_raw == ""


def test_parse_prisliste_for_molde_emits_aarlig_kontroll_fixture():
    rows = parse_prisliste(_read("molde_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Årlig kontroll hos tannlege"]
    assert len(matches) == 1


def test_parse_prisliste_for_honefoss_emits_aarlig_kontroll_fixture():
    rows = parse_prisliste(_read("hoenefoss_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Årlig kontroll hos tannlege"]
    assert len(matches) == 1

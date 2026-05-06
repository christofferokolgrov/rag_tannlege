from pathlib import Path

from scraper.parsers import PriceRow
from scraper.parsers.oc import parse_clinic, parse_prisliste
from scraper.prisformat import Prisformat

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "html_cache" / "oc"


def _read(name: str) -> str:
    return (CACHE_DIR / name).read_text(encoding="utf-8")


def test_parse_prisliste_emits_tannlegesenteret_taasen_fixture_row():
    rows = parse_prisliste(_read("tannlegesenteret_taasen_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Tannundersøkelse hos tannlege"]
    assert len(matches) == 1, [r.behandling_navn_raw for r in rows[:5]]
    row = matches[0]
    assert (row.pris_min, row.pris_max, row.prisformat) == (2125, 2125, Prisformat.FAST)


def test_parse_prisliste_emits_bergen_nord_fixture_row():
    rows = parse_prisliste(_read("bergen_nord_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Tannundersøkelse hos tannlege"]
    assert len(matches) == 1, [r.behandling_navn_raw for r in rows[:5]]
    row = matches[0]
    assert (row.pris_min, row.pris_max, row.prisformat) == (1730, 1730, Prisformat.FAST)


def test_parse_prisliste_emits_festningen_fixture_row():
    """Festningen uses the shorter terminology `Tannundersøkelse` (no
    `hos tannlege`). Per design §11 we capture verbatim — no normalization."""
    rows = parse_prisliste(_read("festningen_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Tannundersøkelse"]
    assert len(matches) == 1, [r.behandling_navn_raw for r in rows[:5]]
    row = matches[0]
    assert (row.pris_min, row.pris_max, row.prisformat) == (1630, 1630, Prisformat.FAST)


def test_parse_prisliste_returns_PriceRow_instances():
    rows = parse_prisliste(_read("tannlegesenteret_taasen_prisliste.html"))
    assert rows
    assert all(isinstance(r, PriceRow) for r in rows)


def test_parse_clinic_extracts_address_postnummer_by():
    info = parse_clinic(_read("tannlegesenteret_taasen_klinikk.html"))
    assert info["adresse"] == "Bergrådveien 13"
    assert info["postnummer"] == "0873"
    assert info["by"] == "Oslo"

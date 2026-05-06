from pathlib import Path

from scraper.parsers import PriceRow
from scraper.parsers.colosseum import parse_clinic, parse_prisliste
from scraper.prisformat import Prisformat

CACHE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "html_cache" / "colosseum"
)


def _read(name: str) -> str:
    return (CACHE_DIR / name).read_text(encoding="utf-8")


def test_parse_central_emits_undersokelse_fixture_row():
    rows = parse_prisliste(_read("central_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Undersøkelse"]
    assert len(matches) == 1, [r.behandling_navn_raw for r in rows[:10]]
    row = matches[0]
    # Page actually says "Undersøkelse – fra kr 1.332" — fra with no upper bound.
    # Spec fixture (1332, 1332, fra) is reconciled to (1332, None, fra) per page reality.
    assert (row.pris_min, row.pris_max, row.prisformat) == (1332, None, Prisformat.FRA)


def test_parse_central_emits_krone_fixture_row():
    rows = parse_prisliste(_read("central_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Krone"]
    assert len(matches) == 1
    row = matches[0]
    # Page says "Krone - fra kr.8.076" — fra not fast (spec was incorrect on prisformat).
    assert (row.pris_min, row.pris_max, row.prisformat) == (8076, None, Prisformat.FRA)


def test_parse_central_returns_PriceRow_instances():
    rows = parse_prisliste(_read("central_prisliste.html"), klinikk_id="colosseum__central")
    assert rows
    assert all(isinstance(r, PriceRow) for r in rows)
    assert all(r.klinikk_id == "colosseum__central" for r in rows)
    assert all(r.pris_kilde == "sentral" for r in rows)


def test_parse_clinic_extracts_majorstuen_address():
    info = parse_clinic(_read("majorstuen_klinikk.html"))
    assert info["postnummer"]
    assert info["by"]
    assert info["adresse"]

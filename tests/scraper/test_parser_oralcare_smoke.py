from pathlib import Path

from scraper.parsers import PriceRow
from scraper.parsers.oralcare import parse_clinic, parse_prisliste
from scraper.prisformat import Prisformat

CACHE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "html_cache" / "oralcare"
)


def _read(name: str) -> str:
    return (CACHE_DIR / name).read_text(encoding="utf-8")


def test_parse_prisliste_emits_forste_undersokelse_fixture_row():
    rows = parse_prisliste(_read("linderud_prisliste.html"))
    # The page heading is the longer form. Per raw-scrape policy
    # (design §11 / slice spec), the page wins over the spec's shorthand.
    target = "Første undersøkelse inkl. nødvendig 2D-røntgen"
    matches = [r for r in rows if r.behandling_navn_raw == target]
    assert len(matches) == 1, [r.behandling_navn_raw for r in rows[:10]]
    row = matches[0]
    assert (row.pris_min, row.pris_max, row.prisformat) == (990, 990, Prisformat.FAST)


def test_parse_prisliste_emits_komposittfylling_1_flate_fixture_row():
    rows = parse_prisliste(_read("linderud_prisliste.html"))
    # Page bullet reads "Komposittfylling, 1 flate, pris fra : 1 365 kr".
    # Splitting on the trailing colon keeps the "pris fra" hint inside the
    # name (raw scrape) and parses the price as a plain integer → fast/1365.
    target = "Komposittfylling, 1 flate, pris fra"
    matches = [r for r in rows if r.behandling_navn_raw == target]
    assert len(matches) == 1, [r.behandling_navn_raw for r in rows[:20]]
    row = matches[0]
    assert (row.pris_min, row.pris_max, row.prisformat) == (1365, 1365, Prisformat.FAST)


def test_parse_prisliste_returns_PriceRow_instances():
    rows = parse_prisliste(
        _read("linderud_prisliste.html"), klinikk_id="oralcare__linderud"
    )
    assert rows
    assert all(isinstance(r, PriceRow) for r in rows)
    assert all(r.klinikk_id == "oralcare__linderud" for r in rows)
    assert all(r.pris_kilde == "klinikk_egen" for r in rows)


def test_parse_clinic_extracts_linderud_street_address():
    info = parse_clinic(_read("linderud_klinikk.html"))
    # Linderud page shows the street but no postnummer/by; parser must
    # degrade gracefully and return what it can.
    assert info.get("adresse") == "Erich Mogensøns vei 38"

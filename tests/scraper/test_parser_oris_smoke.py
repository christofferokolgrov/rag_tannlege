from pathlib import Path

from scraper.parsers import PriceRow
from scraper.parsers.oris import parse_clinic, parse_prisliste
from scraper.prisformat import Prisformat

CACHE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "html_cache" / "oris"
)


def _read(name: str) -> str:
    return (CACHE_DIR / name).read_text(encoding="utf-8")


def test_parse_central_emits_tannundersokelse_fixture_row():
    rows = parse_prisliste(_read("central_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Tannundersøkelse"]
    assert len(matches) == 1, [r.behandling_navn_raw for r in rows[:10]]
    row = matches[0]
    # Page text: "fra 1.423,-" → fra with no upper bound. Spec fixture (1423) only
    # specifies pris_min; we resolve to (1423, None, fra) per page reality.
    assert (row.pris_min, row.pris_max, row.prisformat) == (1423, None, Prisformat.FRA)


def test_parse_central_emits_fyllinger_fixture_row():
    rows = parse_prisliste(_read("central_prisliste.html"))
    matches = [r for r in rows if r.behandling_navn_raw == "Fyllinger, én tannflate (kompositt)"]
    assert len(matches) == 1
    row = matches[0]
    assert (row.pris_min, row.pris_max, row.prisformat) == (1312, None, Prisformat.FRA)


def test_parse_central_emits_implantat_fixture_row():
    rows = parse_prisliste(_read("central_prisliste.html"))
    matches = [
        r for r in rows
        if r.behandling_navn_raw == "Implantat behandling - én tann inkl. krone"
    ]
    assert len(matches) == 1
    row = matches[0]
    assert (row.pris_min, row.pris_max, row.prisformat) == (33075, None, Prisformat.FRA)


def test_parse_central_returns_PriceRow_instances():
    rows = parse_prisliste(_read("central_prisliste.html"), klinikk_id="oris__central")
    assert rows
    assert all(isinstance(r, PriceRow) for r in rows)
    assert all(r.klinikk_id == "oris__central" for r in rows)
    assert all(r.pris_kilde == "sentral" for r in rows)

from pathlib import Path

from scraper.parsers import PriceRow
from scraper.parsers.helsesmart import parse_helsesmart_clinic
from scraper.prisformat import Prisformat

CACHE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "html_cache" / "helsesmart"
)


def _read(name: str) -> str:
    return (CACHE_DIR / name).read_text(encoding="utf-8")


def test_parse_helsesmart_clinic_emits_implantat_fixture_row():
    rows = parse_helsesmart_clinic(
        _read("colosseum_majorstuen.html"),
        klinikk_id="colosseum__majorstuen",
        filter_treatments=["implantat"],
    )
    matches = [r for r in rows if r.behandling_navn_raw == "IMPLANTAT"]
    assert len(matches) == 1, [r.behandling_navn_raw for r in rows]
    row = matches[0]
    # Page renders "PRIS (11,900-32,000,-) FASTSLÅS VED KONSULTASJON".
    # Spec fixture said etter_konsultasjon; design §2 reconciles to spread when
    # both pris_min and pris_max are present.
    assert (row.pris_min, row.pris_max, row.prisformat) == (11900, 32000, Prisformat.SPREAD)
    assert row.pris_kilde == "helsesmart"
    assert "FASTSLÅS VED KONSULTASJON" in row.kommentar


def test_parse_helsesmart_clinic_filter_drops_non_matching_treatments():
    rows = parse_helsesmart_clinic(
        _read("colosseum_majorstuen.html"),
        klinikk_id="colosseum__majorstuen",
        filter_treatments=["implantat"],
    )
    # Filter is "implantat" — HELPROTESE rows must NOT come through.
    assert all("HELPROTESE" not in r.behandling_navn_raw for r in rows)


def test_parse_helsesmart_clinic_no_filter_returns_all_priced_rows():
    rows = parse_helsesmart_clinic(
        _read("colosseum_majorstuen.html"),
        klinikk_id="colosseum__majorstuen",
    )
    assert all(isinstance(r, PriceRow) for r in rows)
    assert all(r.pris_kilde == "helsesmart" for r in rows)
    # The Protese og implantat section alone has 4 priced items.
    assert len(rows) >= 4

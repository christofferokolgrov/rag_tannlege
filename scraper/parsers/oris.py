import re

from selectolax.parser import HTMLParser

from scraper.parsers import PriceRow
from scraper.prisformat import PrisformatError, parse_price

PRIS_KILDE = "sentral"

# Oris treatment names carry a trailing "*" or " *" footnote marker.
_FOOTNOTE_MARKER_RE = re.compile(r"\s*\*+\s*$")
_ADDRESS_RE = re.compile(
    r"([^,\n]+?),\s*(\d{4})[\s\xa0]+([A-Za-zÆØÅæøå]+)"
)


def _treatment_name(item) -> str:
    h3 = item.css_first("h3")
    if not h3:
        return ""
    raw = h3.text(strip=True)
    return _FOOTNOTE_MARKER_RE.sub("", raw)


def parse_prisliste(
    html: str, *, klinikk_id: str = "oris__central", hentet_dato: str = ""
) -> list[PriceRow]:
    rows: list[PriceRow] = []
    h = HTMLParser(html)
    for item in h.css(".Price-list__item"):
        name = _treatment_name(item)
        if not name:
            continue
        price_el = item.css_first(".Price-list__item-price")
        if not price_el:
            continue
        price_text = price_el.text(strip=True)
        try:
            parsed = parse_price(price_text)
        except PrisformatError:
            continue
        rows.append(
            PriceRow(
                klinikk_id=klinikk_id,
                behandling_navn_raw=name,
                pris_min=parsed.pris_min,
                pris_max=parsed.pris_max,
                prisformat=parsed.prisformat,
                pris_kilde=PRIS_KILDE,
                kommentar="",
                hentet_dato=hentet_dato,
            )
        )
    return rows


def parse_clinic(html: str) -> dict[str, str]:
    h = HTMLParser(html)
    text = h.text(separator="\n", strip=True)
    m = _ADDRESS_RE.search(text)
    if not m:
        return {}
    return {
        "adresse": m.group(1).strip(),
        "postnummer": m.group(2),
        "by": m.group(3),
    }

import re

from selectolax.parser import HTMLParser

from scraper.parsers import PriceRow
from scraper.prisformat import PrisformatError, parse_price

PRIS_KILDE = "sentral"

_LEADING_SEP_RE = re.compile(r"^[-–—]\s*")
_ADDRESS_RE = re.compile(
    r"([^,\n]+?),\s*(\d{4})[\s\xa0]+([A-Za-zÆØÅæøå]+)"
)


def parse_prisliste(
    html: str, *, klinikk_id: str = "colosseum__central", hentet_dato: str = ""
) -> list[PriceRow]:
    rows: list[PriceRow] = []
    h = HTMLParser(html)
    for p in h.css("p"):
        strong = p.css_first("strong")
        if not strong:
            continue
        name = strong.text(strip=True)
        if not name:
            continue
        # The treatment name is in <strong>; the price is the text node that
        # follows it before the <br> separator. text(separator='|') gives us
        # the visible text segments split by element boundaries.
        full_text = p.text(separator="|", strip=True)
        parts = full_text.split("|")
        if len(parts) < 2:
            continue
        price_text = _LEADING_SEP_RE.sub("", parts[1].strip())
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

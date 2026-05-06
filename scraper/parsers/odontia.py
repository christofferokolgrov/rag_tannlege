import re

from selectolax.parser import HTMLParser

from scraper.parsers import PriceRow
from scraper.prisformat import PrisformatError, parse_price

PRIS_KILDE = "klinikk_egen"

_FOOTNOTE_SELECTOR = ".small-text"
_ADDRESS_RE = re.compile(
    r"([^,\n]+?),\s*(\d{4})[\s\xa0]+([A-Za-zÆØÅæøå]+)"
)


def _treatment_name(cell) -> str:
    for footnote in cell.css(_FOOTNOTE_SELECTOR):
        footnote.decompose()
    return cell.text(strip=True)


def parse_prisliste(
    html: str, *, klinikk_id: str = "", hentet_dato: str = ""
) -> list[PriceRow]:
    rows: list[PriceRow] = []
    h = HTMLParser(html)
    for tbl in h.css("table"):
        for tr in tbl.css("tr"):
            cells = tr.css("td")
            if len(cells) != 2:
                continue
            name = _treatment_name(cells[0])
            if not name:
                continue
            raw_price = cells[1].text(strip=True)
            try:
                parsed = parse_price(raw_price)
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
        raise ValueError("could not extract address from clinic page")
    return {
        "adresse": m.group(1).strip(),
        "postnummer": m.group(2),
        "by": m.group(3),
    }

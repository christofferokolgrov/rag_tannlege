"""Parser for kjede=single — reads pre-extracted JSON instead of HTML.

The single-clinic price data is extracted once via
tools/extract_single_clinics.py (DeepSeek over each clinic's HTML) and
committed under data/single_clinics_extracted/<slug>.json. This parser
just deserializes those files and converts to PriceRow instances.

Idempotent and deterministic: every `python -m scraper run` produces
byte-identical output without any LLM calls. Refresh of the JSON files
is an explicit manual step (run extract_single_clinics.py).
"""
from __future__ import annotations

import json
from pathlib import Path

from scraper.parsers import PriceRow
from scraper.prisformat import Prisformat

PRIS_KILDE = "single_extracted"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXTRACTED_DIR = REPO_ROOT / "data" / "single_clinics_extracted"


def parse_prisliste(
    html: str = "",
    *,
    klinikk_id: str = "",
    hentet_dato: str = "",
) -> list[PriceRow]:
    """Read data/single_clinics_extracted/<slug>.json for this klinikk_id
    and return PriceRow instances. The `html` argument is accepted for
    interface symmetry with other parsers but ignored — the actual data
    source is the cached JSON file.
    """
    if not klinikk_id.startswith("single__"):
        return []
    slug = klinikk_id.removeprefix("single__")
    path = EXTRACTED_DIR / f"{slug}.json"
    if not path.exists():
        return []

    doc = json.loads(path.read_text(encoding="utf-8"))
    rows: list[PriceRow] = []
    for entry in doc.get("rows", []):
        prisformat_str = entry.get("prisformat", "")
        try:
            prisformat = Prisformat(prisformat_str)
        except ValueError:
            continue
        rows.append(
            PriceRow(
                klinikk_id=klinikk_id,
                behandling_navn_raw=entry.get("behandling_navn_raw", ""),
                pris_min=entry.get("pris_min"),
                pris_max=entry.get("pris_max"),
                prisformat=prisformat,
                pris_kilde=PRIS_KILDE,
                kommentar="",
                hentet_dato=hentet_dato,
            )
        )
    return rows


def parse_clinic(html: str = "") -> dict:
    """Independent clinics scraped via DeepSeek don't have parsed address
    data (HTML structure varies wildly). clinics.csv ends up with empty
    adresse for kjede=single rows — same convention as the helsesmart
    parser (#22 / #32)."""
    return {}

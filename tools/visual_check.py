"""Per-fixture-clinic HTML-vs-CSV diff.

Goal: take the burden of "manually compare HTML to CSV" off the human by
extracting every price-shape pattern from each fixture clinic's HTML cache
and asking: does CSV cover all of them? Surfaces only the diffs.

Designed for HITL #24 task 1 (visual sign-off): if a clinic's diff is
clean, that's a 1-second sign-off. If it shows 3 unexplained matches in
HTML that aren't in CSV, that's where to look manually.

Usage:
    uv run python tools/visual_check.py
    # (returns 0 if all clinics clean; 1 if any flagged)
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import yaml
from selectolax.parser import HTMLParser

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = REPO_ROOT / "tests" / "scraper" / "parser_validation.yaml"
PRICES_RAW_PATH = REPO_ROOT / "data" / "prices_raw.csv"
HTML_CACHE_DIR = REPO_ROOT / "data" / "html_cache"

# Price-shape patterns we expect to see somewhere in the HTML for each row.
# Norwegian formats: "1.595 kr", "1 595 kr", "fra kr 1.500,-", "950 - 1.545",
# "NOK 11 900 - 32 000", "Etter konsultasjon", etc.
PRICE_SHAPE_RE = re.compile(
    r"\b(?:NOK|kr|Kr)?\s*\.?\s*\d{2,3}(?:[.\s\xa0]\d{3})*(?:\s*-\s*\d{2,3}(?:[.\s\xa0]\d{3})*)?",
    re.IGNORECASE,
)


def _csv_rows_by_klinikk() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    with PRICES_RAW_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.setdefault(row["klinikk_id"], []).append(row)
    return out


def _csv_price_strings(rows: list[dict]) -> set[str]:
    """Return the set of integer values present in CSV (pris_min and pris_max)."""
    values: set[str] = set()
    for r in rows:
        for col in ("pris_min", "pris_max"):
            v = r.get(col, "")
            if v:
                values.add(v)
    return values


def _html_price_integers(html: str) -> list[int]:
    """Pull integers only from text segments that look like Norwegian price
    notation: have a currency token (kr/NOK), trailing ,-, or a "fra"
    prefix. This filters out CSS values, line-heights, transition durations,
    and other non-price integers that bleed into a generic page-text scan.
    """
    h = HTMLParser(html)
    text = h.text(separator=" ", strip=True).replace("\xa0", " ")

    # Match either a number with thousands separators (e.g. "1.595", "11 900")
    # or a bare 3-6 digit integer (e.g. "990", "33075"). Avoids the trap
    # `\d{2,3}` had of partially matching long runs ("1500" → "150").
    NUM = r"(?:\d{1,3}(?:[.\s]\d{3})+|\d{3,6})"
    PRICE_CONTEXT_RES = [
        re.compile(rf"\b(?:kr|NOK)\.?\s*({NUM})", re.IGNORECASE),  # "kr 1.595"
        re.compile(rf"({NUM})\s*kr\b", re.IGNORECASE),             # "1.595 kr"
        re.compile(rf"({NUM})\s*,-"),                              # "1.500,-"
        re.compile(rf"\bfra\s+(?:kr\.?\s*)?({NUM})", re.IGNORECASE), # "fra 1.500" / "fra kr 1.500"
    ]

    integers: list[int] = []
    for pat in PRICE_CONTEXT_RES:
        for m in pat.finditer(text):
            cleaned = m.group(1).replace(".", "").replace(" ", "")
            try:
                n = int(cleaned)
            except ValueError:
                continue
            if 50 <= n <= 999_999:
                integers.append(n)
    return integers


def _cache_paths(klinikk_id: str) -> list[Path]:
    """Return the prisliste cache file(s) we expect to inspect for this clinic."""
    if "__" not in klinikk_id:
        return []
    kjede, slug = klinikk_id.split("__", 1)
    candidates = [
        HTML_CACHE_DIR / kjede / f"{slug}_prisliste.html",
    ]
    if klinikk_id == "colosseum__majorstuen":
        candidates.append(HTML_CACHE_DIR / "helsesmart" / "colosseum_majorstuen.html")
    return [p for p in candidates if p.exists()]


def main() -> int:
    fixtures_doc = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8")) or {}
    fixture_klinikk_ids: list[str] = []
    for f in fixtures_doc.get("fixtures") or []:
        if f["klinikk_id"] not in fixture_klinikk_ids:
            fixture_klinikk_ids.append(f["klinikk_id"])

    csv_rows = _csv_rows_by_klinikk()
    flagged = 0
    print("Visual diff per fixture clinic (HTML integers not present as CSV pris_min/pris_max):\n")

    for klinikk_id in fixture_klinikk_ids:
        caches = _cache_paths(klinikk_id)
        if not caches:
            print(f"  {klinikk_id}: NO CACHE FILE (sentral pseudo or peker_på_sentral with no committed cache)")
            continue

        csv_values = {int(v) for v in _csv_price_strings(csv_rows.get(klinikk_id, []))}
        html_integers: list[int] = []
        for cache in caches:
            html_integers.extend(_html_price_integers(cache.read_text(encoding="utf-8")))

        # Filter HTML integers to those that look like prices (>=100) and
        # subtract anything already in CSV. Multiple occurrences are OK —
        # we just need to know if a price-shaped int is missing entirely.
        missing = sorted({n for n in html_integers if n not in csv_values})
        # Remove obvious non-prices: 4-digit postal codes mostly fall in the
        # range 0000-9999; we already filter <100. Some real prices are in
        # this range (low fees). Keep them.

        n_csv = len(csv_values)
        if not missing:
            print(f"  {klinikk_id}: clean ({n_csv} CSV values, all HTML ints accounted for)")
            continue

        flagged += 1
        # Truncate the missing list — too long to be useful
        sample = missing[:30]
        print(f"  {klinikk_id}: FLAGGED  ({n_csv} CSV values; {len(missing)} HTML ints not in CSV)")
        print(f"    sample missing: {sample}")
        print(f"    cache: {caches[0].relative_to(REPO_ROOT)}")

    print(f"\n{len(fixture_klinikk_ids)} clinics inspected, {flagged} flagged for review.")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())

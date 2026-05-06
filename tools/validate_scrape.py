"""Validate prices_raw.csv against the parser_validation.yaml fixtures.

Per design §8:
  EKSAKT MATCH → ok
  AVVIK        → print diff + html cache path; exit 2
  MANGLER      → fixture row absent from output; exit 3

Run after `python -m scraper run`:
    uv run python tools/validate_scrape.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = REPO_ROOT / "tests" / "scraper" / "parser_validation.yaml"
PRICES_RAW_PATH = REPO_ROOT / "data" / "prices_raw.csv"
HTML_CACHE_DIR = REPO_ROOT / "data" / "html_cache"

EXIT_OK = 0
EXIT_AVVIK = 2
EXIT_MANGLER = 3


def _load_fixtures() -> list[dict]:
    with FIXTURE_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return list(data.get("fixtures") or [])


def _load_prices() -> dict[tuple[str, str], dict]:
    if not PRICES_RAW_PATH.exists():
        sys.exit(f"prices_raw.csv missing at {PRICES_RAW_PATH}")
    by_key: dict[tuple[str, str], dict] = {}
    with PRICES_RAW_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            by_key[(row["klinikk_id"], row["behandling_navn_raw"])] = row
    return by_key


def _coerce_int(value: str) -> Optional[int]:
    if value == "" or value is None:
        return None
    return int(value)


def _row_to_actual(row: dict) -> dict:
    return {
        "pris_min": _coerce_int(row.get("pris_min", "")),
        "pris_max": _coerce_int(row.get("pris_max", "")),
        "prisformat": row.get("prisformat") or None,
        "pris_kilde": row.get("pris_kilde") or None,
    }


def _diff(forventet: dict, actual: dict) -> list[str]:
    diffs = []
    for key, expected in forventet.items():
        got = actual.get(key)
        if got != expected:
            diffs.append(f"  {key}: expected {expected!r}, got {got!r}")
    return diffs


def _html_cache_hint(klinikk_id: str) -> Path:
    if "__" not in klinikk_id:
        return HTML_CACHE_DIR
    kjede, slug = klinikk_id.split("__", 1)
    return HTML_CACHE_DIR / kjede / f"{slug}_prisliste.html"


def main() -> int:
    fixtures = _load_fixtures()
    prices = _load_prices()

    avvik: list[tuple[dict, list[str]]] = []
    mangler: list[dict] = []
    matched = 0

    for fixture in fixtures:
        key = (fixture["klinikk_id"], fixture["behandling_navn_raw"])
        actual_row = prices.get(key)
        if actual_row is None:
            mangler.append(fixture)
            continue
        actual = _row_to_actual(actual_row)
        diffs = _diff(fixture["forventet"], actual)
        if diffs:
            avvik.append((fixture, diffs))
        else:
            matched += 1

    print(f"Validated {len(fixtures)} fixture rows: {matched} EKSAKT MATCH, "
          f"{len(avvik)} AVVIK, {len(mangler)} MANGLER")

    for fixture, diffs in avvik:
        print(f"\nAVVIK: {fixture['klinikk_id']} / {fixture['behandling_navn_raw']}")
        for d in diffs:
            print(d)
        print(f"  HTML cache: {_html_cache_hint(fixture['klinikk_id'])}")

    for fixture in mangler:
        print(f"\nMANGLER: {fixture['klinikk_id']} / {fixture['behandling_navn_raw']}")
        print(f"  HTML cache: {_html_cache_hint(fixture['klinikk_id'])}")

    if mangler:
        return EXIT_MANGLER
    if avvik:
        return EXIT_AVVIK
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

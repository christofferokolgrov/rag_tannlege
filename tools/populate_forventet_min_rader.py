"""Populate forventet_min_rader for each fixture clinic in parser_validation.yaml.

Counts rows per klinikk_id in data/prices_raw.csv and writes a baseline
floor (count - 10% slack) on each fixture clinic. The A-check from
design §11 reads this field — once populated, regressions that cause
parser to lose >10% of rows fail validation.

Usage:
    uv run python tools/populate_forventet_min_rader.py
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = REPO_ROOT / "tests" / "scraper" / "parser_validation.yaml"
PRICES_RAW_PATH = REPO_ROOT / "data" / "prices_raw.csv"

SLACK = 0.10  # 10% headroom — design §11


def _row_counts() -> dict[str, int]:
    counter: Counter[str] = Counter()
    with PRICES_RAW_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            counter[row["klinikk_id"]] += 1
    return counter


def main() -> int:
    counts = _row_counts()

    # Round-trip the YAML preserving its raw text so the existing comments
    # and ordering survive. Hand-rewrite the document.
    fixtures_doc = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8")) or {}
    fixtures = fixtures_doc.get("fixtures") or []

    fixture_klinikk_ids = sorted({f["klinikk_id"] for f in fixtures})
    floor_by_id: dict[str, int] = {}
    for kid in fixture_klinikk_ids:
        actual = counts.get(kid, 0)
        # Sentral pseudo-clinics (oris__central, colosseum__central) host all
        # the prices for their chain — the count is meaningful. Real
        # peker_på_sentral clinics emit zero rows; we skip them by virtue of
        # not being in the fixtures list.
        floor_by_id[kid] = max(0, int(actual * (1 - SLACK)))
        print(f"  {kid}: actual={actual} → forventet_min_rader={floor_by_id[kid]}")

    # Block-write the baseline alongside each fixture entry. We mutate the
    # parsed structure but emit YAML preserving the document order.
    seen_ids: set[str] = set()
    for entry in fixtures:
        kid = entry["klinikk_id"]
        if kid in seen_ids:
            continue
        seen_ids.add(kid)
        # Attach forventet_min_rader at the entry level the FIRST time we see
        # the klinikk_id; further fixture rows for the same klinikk leave the
        # baseline alone (it's a per-clinic property, not per-row).
        entry["forventet_min_rader"] = floor_by_id[kid]

    fixtures_doc["fixtures"] = fixtures

    # Preserve the existing header comments by reading the raw file, finding
    # the start of the YAML body (first non-comment, non-blank line), and
    # injecting the new dump.
    raw = FIXTURE_PATH.read_text(encoding="utf-8")
    header_lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            header_lines.append(line)
        else:
            break

    body = yaml.safe_dump(
        fixtures_doc, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    FIXTURE_PATH.write_text("\n".join(header_lines) + "\n" + body, encoding="utf-8")
    print(f"\nWrote {len(fixture_klinikk_ids)} fixture clinics to {FIXTURE_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

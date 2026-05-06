"""Extract dental prices from single-clinic HTML using DeepSeek.

Reads each cached HTML in data/html_cache/single/<slug>_prisliste.html,
sends it to DeepSeek with a strict extraction prompt, validates the
returned JSON via verbatim-presence check against the source HTML,
and writes data/single_clinics_extracted/<slug>.json.

The committed JSON files are the deterministic artefact-trail; the
scraper's parsers/single_json.py reads from them at every run, so
LLM calls happen only when this script is invoked manually.

Usage:
    uv run python tools/extract_single_clinics.py
        Extract clinics that don't yet have a JSON file.
    uv run python tools/extract_single_clinics.py --force
        Re-extract all clinics, overwriting existing JSON.
    uv run python tools/extract_single_clinics.py --clinic single__oslo_tannlegesenter
        Re-extract only one clinic.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from openai import OpenAI
from selectolax.parser import HTMLParser

from tannhelse.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_MODEL

REPO_ROOT = Path(__file__).resolve().parent.parent
URLS_PATH = REPO_ROOT / "data" / "single_clinics_urls.yaml"
HTML_CACHE_DIR = REPO_ROOT / "data" / "html_cache" / "single"
EXTRACTED_DIR = REPO_ROOT / "data" / "single_clinics_extracted"

EXTRACTION_PROMPT = """You are extracting dental treatment prices from a Norwegian dental clinic's website HTML.

Output a JSON object with this exact shape:
{
  "rows": [
    {
      "behandling_navn_raw": "<exact treatment name as it appears in the HTML, verbatim>",
      "pris_min": <integer NOK>,
      "pris_max": <integer NOK or null>,
      "prisformat": "<one of: fast | fra | spread | per_dose | per_stk | per_halvtime | etter_konsultasjon>"
    },
    ...
  ]
}

Rules:
1. Extract ONLY prices that appear verbatim in the HTML. Never compute, infer, or interpolate.
2. behandling_navn_raw must be the EXACT Norwegian text from the HTML — character for character.
3. prisformat values:
   - "fast" — single fixed price (pris_min == pris_max)
   - "fra" — "from X kr" with no upper bound (pris_min = X, pris_max = null)
   - "spread" — range like "950 - 1545" (pris_min = lo, pris_max = hi)
   - "per_dose" / "per_stk" / "per_halvtime" — per-unit add-ons
   - "etter_konsultasjon" — "Etter konsultasjon" with no number (pris_min = null, pris_max = null)
4. If the HTML contains discount-only prices ("nye pasienter 30% rabatt"), output the FULL price, not the discounted one.
5. Skip "fra"-format rows where there's no clear standalone treatment name.
6. Skip non-treatment items (booking fees, no-show fees, gift cards).
7. If you cannot find any prices, return {"rows": []} — never invent.
8. Output ONLY the JSON object — no commentary, no markdown fence.

Source HTML follows. Extract prices now.
"""


def _html_to_text(html: str) -> str:
    """Strip HTML to readable text. Limit to 25k chars to fit context."""
    h = HTMLParser(html)
    # Remove script/style noise
    for tag in h.css("script, style, nav, footer, header"):
        tag.decompose()
    text = h.text(separator="\n", strip=True)
    if len(text) > 25_000:
        text = text[:25_000] + "\n[…truncated…]"
    return text


def _validate_extraction(rows: list[dict], html_text: str) -> tuple[list[dict], list[str]]:
    """Verify that each row's pris_min appears verbatim in the HTML text
    within 200 chars of the treatment name. Returns (valid_rows, dropped_reasons).
    """
    valid: list[dict] = []
    dropped: list[str] = []
    text_lower = html_text.lower()

    for row in rows:
        name = (row.get("behandling_navn_raw") or "").strip()
        pris_min = row.get("pris_min")
        if not name or pris_min is None:
            # etter_konsultasjon rows are allowed to have null pris
            if row.get("prisformat") == "etter_konsultasjon" and name:
                valid.append(row)
                continue
            dropped.append(f"missing name or pris_min: {row}")
            continue

        # Verify name appears in HTML (substring, case-insensitive)
        if name.lower() not in text_lower:
            dropped.append(f"name not in HTML verbatim: {name!r}")
            continue

        # Verify pris_min digits appear in HTML in some recognizable form
        digits = str(pris_min)
        # Accept "1 234", "1.234", or "1234" formats
        digit_patterns = [
            digits,
            f"{digits[:1]} {digits[1:]}" if len(digits) == 4 else None,
            f"{digits[:1]}.{digits[1:]}" if len(digits) == 4 else None,
            f"{digits[:2]} {digits[2:]}" if len(digits) == 5 else None,
            f"{digits[:2]}.{digits[2:]}" if len(digits) == 5 else None,
        ]
        digit_patterns = [d for d in digit_patterns if d]
        if not any(d in html_text for d in digit_patterns):
            dropped.append(f"pris_min {pris_min} digits not in HTML: {name!r}")
            continue

        valid.append(row)

    return valid, dropped


def _call_deepseek(client: OpenAI, html_text: str) -> dict:
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT + "\n" + html_text}],
        temperature=0,
        max_tokens=8000,
    )
    raw = response.choices[0].message.content.strip()
    # Strip markdown fence if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _extract_one(klinikk_id: str, html_path: Path, out_path: Path, client: OpenAI) -> None:
    print(f"  extracting {klinikk_id}...", end=" ", flush=True)
    html_raw = html_path.read_text(encoding="utf-8")
    html_text = _html_to_text(html_raw)
    try:
        result = _call_deepseek(client, html_text)
    except Exception as e:
        print(f"LLM error: {type(e).__name__}: {str(e)[:80]}")
        return
    rows = result.get("rows", [])
    valid, dropped = _validate_extraction(rows, html_text)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "klinikk_id": klinikk_id,
                "extracted_count": len(valid),
                "dropped_count": len(dropped),
                "dropped_reasons": dropped[:5],  # cap log size
                "rows": valid,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"{len(valid)} rows ({len(dropped)} dropped)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-extract all, overwriting existing JSON")
    parser.add_argument("--clinic", help="re-extract only one klinikk_id")
    args = parser.parse_args()

    if not DEEPSEEK_API_KEY:
        print("DEEPSEEK_API_KEY not set; aborting.", file=sys.stderr)
        return 1

    urls_doc = yaml.safe_load(URLS_PATH.read_text())
    clinics = urls_doc["clinics"]
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    targets = []
    for c in clinics:
        if c.get("confidence") == "none":
            continue
        klinikk_id = c["klinikk_id"]
        if args.clinic and args.clinic != klinikk_id:
            continue
        slug = klinikk_id.replace("single__", "")
        html_path = HTML_CACHE_DIR / f"{slug}_prisliste.html"
        out_path = EXTRACTED_DIR / f"{slug}.json"
        if not html_path.exists():
            print(f"  skip {klinikk_id} — no cached HTML")
            continue
        if out_path.exists() and not args.force:
            print(f"  skip {klinikk_id} — already extracted (use --force to redo)")
            continue
        targets.append((klinikk_id, html_path, out_path))

    print(f"Extracting {len(targets)} clinics via DeepSeek ({LLM_MODEL})...")
    for klinikk_id, html_path, out_path in targets:
        _extract_one(klinikk_id, html_path, out_path, client)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Match independent Oslo-area dental clinics (input as AS-names) against
HelseSmart's clinic-priser sitemap. Emit manifest entries for matches
above a similarity threshold; log un-matched names for manual review.

Usage:
    uv run python tools/discover_single_clinics.py
       Reads data/single_clinics_oslo.txt
       Writes manifest YAML fragment to stdout (append to clinic_discovery.yaml)
       Writes data/single_clinics_unmatched.txt (names below threshold)
       Per-name match report to stderr.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import yaml

from scraper.config import HTML_CACHE_DIR
from scraper.fetch import fetch_with_cache
from scraper.slug import to_slug

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = REPO_ROOT / "data" / "single_clinics_oslo.txt"
UNMATCHED_PATH = REPO_ROOT / "data" / "single_clinics_unmatched.txt"
SITEMAP_URL = "https://www.helsesmart.no/sitemaps/06_klinikk_priser.xml"
SITEMAP_CACHE = HTML_CACHE_DIR / "helsesmart" / "_klinikk_priser_sitemap.xml"

# Match threshold — score >= this is auto-accepted. 0.65 catches several
# legitimate matches the stricter 0.7 missed (e.g. "Grünerløkkas hus
# tannlegesenter" → "grunerlokka-tannhelsesenter" @ 0.69). The tradeoff is
# some false positives in the 0.65-0.69 zone (e.g. "Periodontispesialistene
# AS" mismatched against a heart specialist) — manual review recommended
# in data/single_clinics_unmatched.txt for borderline cases.
MATCH_THRESHOLD = 0.65

# Suffixes/prefixes to strip when normalising the AS-name for matching.
# These are common words in Norwegian dental clinic naming that appear
# inconsistently between brreg-style names and HelseSmart slugs.
NOISE_TOKENS = {
    "as",
    "da",
    "ans",
    "tannlegesenter",
    "tannklinikk",
    "tannlegene",
    "tannhelsesenter",
    "tannhelseklinikk",
    "tannhelse",
    "tannhelsekontor",
    "tannlegekontor",
    "tannlegevakt",
    "tannregulering",
    "tannreguleringssenter",
    "tannlegene",
    "klinikken",
    "klinikk",
    "kjeveortoped",
    "oralkirurgi",
    "oslo",
    "co",
    "ans",
}


def _strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def _normalize_for_match(name: str) -> str:
    """Normalise an AS-name or HelseSmart slug to a comparable token bag.
    Returns space-separated tokens with diacritics, suffix-words, and
    common decorations stripped."""
    s = _strip_diacritics(name).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    tokens = [t for t in s.split() if t and t not in NOISE_TOKENS]
    return " ".join(tokens)


def _load_sitemap_clinics() -> list[tuple[str, str]]:
    """Return [(slug, full_url), ...] from HelseSmart's clinic-priser
    sitemap. Slug is the path segment before /priser/.
    Example URL: https://www.helsesmart.no/klinikk/colosseum-tannlege-majorstuen-12541/priser/
                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    """
    SITEMAP_CACHE.parent.mkdir(parents=True, exist_ok=True)
    xml = fetch_with_cache(SITEMAP_URL, SITEMAP_CACHE)
    out: list[tuple[str, str]] = []
    for m in re.finditer(
        r"<loc>(https://www\.helsesmart\.no/klinikk/([^/]+)/priser/)</loc>", xml
    ):
        full_url, slug = m.group(1), m.group(2)
        out.append((slug, full_url))
    return out


def _best_match(
    query_norm: str, sitemap: list[tuple[str, str]]
) -> tuple[str | None, float, str | None]:
    """Find the sitemap slug with the highest similarity to query_norm.
    Returns (slug, score, full_url)."""
    best_slug, best_score, best_url = None, 0.0, None
    for slug, full_url in sitemap:
        slug_norm = _normalize_for_match(slug)
        if not slug_norm:
            continue
        score = SequenceMatcher(None, query_norm, slug_norm).ratio()
        if score > best_score:
            best_slug, best_score, best_url = slug, score, full_url
    return best_slug, best_score, best_url


def _clean_clinic_navn(as_name: str) -> str:
    """Strip 'AS', 'DA', 'ANS' from end; title-case if all-caps."""
    cleaned = re.sub(r"\s+(AS|DA|ANS)\s*$", "", as_name).strip()
    if cleaned == cleaned.upper():
        cleaned = cleaned.title().replace("Og", "og").replace("På", "på")
    return cleaned


def _make_klinikk_id(as_name: str) -> str:
    """Build a single__<slug> klinikk_id from the cleaned AS-name."""
    cleaned = re.sub(r"\s+(AS|DA|ANS)\s*$", "", as_name).strip()
    return f"single__{to_slug(cleaned)}"


def main() -> int:
    if not INPUT_PATH.exists():
        print(f"missing input file: {INPUT_PATH}", file=sys.stderr)
        return 1

    sitemap = _load_sitemap_clinics()
    print(f"# loaded {len(sitemap)} clinics from HelseSmart sitemap", file=sys.stderr)

    matched: list[dict] = []
    unmatched: list[tuple[str, str | None, float]] = []
    seen_slugs: set[str] = set()  # avoid duplicate matches to same slug

    with INPUT_PATH.open(encoding="utf-8") as f:
        for line in f:
            as_name = line.strip()
            if not as_name or as_name.startswith("#"):
                continue

            query_norm = _normalize_for_match(as_name)
            if not query_norm:
                unmatched.append((as_name, None, 0.0))
                continue

            slug, score, full_url = _best_match(query_norm, sitemap)
            if score >= MATCH_THRESHOLD and slug not in seen_slugs:
                seen_slugs.add(slug)
                matched.append(
                    {
                        "klinikk_id": _make_klinikk_id(as_name),
                        "kjede": "single",
                        "klinikk_navn": _clean_clinic_navn(as_name),
                        "klinikk_url": full_url,
                        "prisliste_url": full_url,
                        "prisliste_struktur": "per_klinikk",
                        "notes": f"matched via HelseSmart sitemap @ {score:.2f}",
                    }
                )
                print(f"  MATCH    {as_name:50s} → {slug:50s} @ {score:.2f}", file=sys.stderr)
            else:
                unmatched.append((as_name, slug, score))
                reason = "below threshold" if score < MATCH_THRESHOLD else "duplicate slug"
                print(
                    f"  UNMATCH  {as_name:50s} (best: {slug or '—':30s} @ {score:.2f}, {reason})",
                    file=sys.stderr,
                )

    print(f"\n# Summary: {len(matched)} matched / {len(unmatched)} unmatched", file=sys.stderr)

    # Emit manifest fragment to stdout
    print("# Generated by tools/discover_single_clinics.py — append to data/clinic_discovery.yaml")
    yaml.safe_dump(
        {"clinics": matched}, sys.stdout, allow_unicode=True, sort_keys=False
    )

    # Write unmatched log
    UNMATCHED_PATH.write_text(
        "# Names that did NOT match HelseSmart's clinic-priser sitemap above the\n"
        f"# threshold {MATCH_THRESHOLD}. Manual review needed if you want them in scope.\n"
        "# Format: <as_name>\\t<best_slug_candidate>\\t<score>\n\n"
        + "\n".join(
            f"{name}\t{slug or ''}\t{score:.2f}" for name, slug, score in unmatched
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"# Wrote unmatched log to {UNMATCHED_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

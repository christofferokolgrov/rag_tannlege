from collections import Counter
from pathlib import Path

import yaml

from scraper.slug import KLINIKK_ID_PATTERN

REQUIRED_ENTRY_FIELDS = (
    "klinikk_id",
    "kjede",
    "klinikk_navn",
    "klinikk_url",
    "prisliste_url",
)

PRISLISTE_STRUKTUR_VALUES = frozenset({"per_klinikk", "sentral", "peker_på_sentral"})

# Sentral pseudo-klinikker carry no info page; klinikk_url is omitted.
SENTRAL_REQUIRED_FIELDS = tuple(
    f for f in REQUIRED_ENTRY_FIELDS if f != "klinikk_url"
)


class ManifestError(ValueError):
    pass


def load_clinic_manifest(path: Path) -> list[dict]:
    if not path.exists():
        raise ManifestError(f"manifest not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return list(data.get("clinics") or [])


def validate_manifest(entries):
    ids = [e["klinikk_id"] for e in entries]

    invalid = [i for i in ids if not KLINIKK_ID_PATTERN.match(i)]
    if invalid:
        raise ManifestError(f"invalid klinikk_id format: {invalid}")

    duplicates = sorted({i for i, n in Counter(ids).items() if n > 1})
    if duplicates:
        raise ManifestError(f"duplicate klinikk_id in manifest: {duplicates}")

    for entry in entries:
        struktur = entry.get("prisliste_struktur", "per_klinikk")
        if struktur not in PRISLISTE_STRUKTUR_VALUES:
            raise ManifestError(
                f"entry {entry.get('klinikk_id', '?')} has invalid prisliste_struktur "
                f"{struktur!r}; expected one of {sorted(PRISLISTE_STRUKTUR_VALUES)}"
            )
        required = SENTRAL_REQUIRED_FIELDS if struktur == "sentral" else REQUIRED_ENTRY_FIELDS
        missing = [f for f in required if not entry.get(f)]
        if missing:
            raise ManifestError(
                f"entry {entry.get('klinikk_id', '?')} is missing required fields: {missing}"
            )

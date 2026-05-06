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
        missing = [f for f in REQUIRED_ENTRY_FIELDS if not entry.get(f)]
        if missing:
            raise ManifestError(
                f"entry {entry.get('klinikk_id', '?')} is missing required fields: {missing}"
            )

"""Suggest canonical-mapping additions by comparing observed treatment
names to the canonical YAML.

Output a structured proposal table:
  - HIGH (similarity ≥ 0.85)  → strong-confidence synonym for an existing canonical
  - MAYBE (0.60 ≤ s < 0.85)   → borderline; human judgment
  - UNMAPPED (< 0.60 or none) → no plausible canonical match; either new
                                 canonical or whitelist as ikke_kanonisk_men_scrapes

Usage:
    uv run python tools/canonical_diff.py
"""
from __future__ import annotations

import sys
from difflib import SequenceMatcher
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
OBSERVED_PATH = REPO_ROOT / "data" / "treatments_observed.yaml"
CANONICAL_PATH = REPO_ROOT / "data" / "treatments_canonical.yaml"


def _norm(s: str) -> str:
    return s.lower().strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _load() -> tuple[dict, dict]:
    observed = yaml.safe_load(OBSERVED_PATH.read_text(encoding="utf-8")) or {}
    canonical = yaml.safe_load(CANONICAL_PATH.read_text(encoding="utf-8")) or {}
    return observed, canonical


def _already_mapped(name: str, kjede: str, canonical: dict) -> str | None:
    for entry in canonical.get("canonical") or []:
        synonyms = (entry.get("kjede_terminologi") or {}).get(kjede) or []
        if name in synonyms:
            return entry["id"]
    return None


def _whitelisted(name: str, canonical: dict) -> bool:
    whitelist = (canonical.get("meta") or {}).get("ikke_kanonisk_men_scrapes") or []
    return any(_norm(name) in _norm(w) or _norm(w) in _norm(name) for w in whitelist)


def _best_match(name: str, canonical: dict) -> tuple[str | None, float]:
    best_id, best_score = None, 0.0
    for entry in canonical.get("canonical") or []:
        # Compare against canonical's own "navn" and against every existing
        # synonym across all chains (so e.g. "Tannrens" in colosseum scores
        # high against odontia's existing "Tannrens med airflow").
        candidates = [entry.get("navn", "")]
        for syns in (entry.get("kjede_terminologi") or {}).values():
            candidates.extend(syns)
        for candidate in candidates:
            if not candidate:
                continue
            score = _similarity(name, candidate)
            if score > best_score:
                best_id, best_score = entry["id"], score
    return best_id, best_score


def main() -> int:
    observed, canonical = _load()

    high: list[tuple[str, str, str, float]] = []
    maybe: list[tuple[str, str, str, float]] = []
    unmapped: list[tuple[str, str, float, str | None]] = []
    skipped_existing = 0
    skipped_whitelisted = 0

    for kjede, names in (observed or {}).items():
        for entry in names or []:
            name = entry.get("name") if isinstance(entry, dict) else entry
            if not name:
                continue
            if _already_mapped(name, kjede, canonical):
                skipped_existing += 1
                continue
            if _whitelisted(name, canonical):
                skipped_whitelisted += 1
                continue
            best_id, score = _best_match(name, canonical)
            row = (kjede, name, best_id, score)
            if score >= 0.85:
                high.append(row)
            elif score >= 0.60:
                maybe.append(row)
            else:
                unmapped.append((kjede, name, score, best_id))

    print(f"Skipped: {skipped_existing} already mapped, {skipped_whitelisted} whitelisted.\n")

    print(f"=== HIGH confidence ({len(high)}) — propose adding to existing canonical ===")
    for kjede, name, cid, score in sorted(high, key=lambda r: -r[3]):
        print(f"  {kjede:10s} {score:.2f}  {cid:30s}  ← {name!r}")

    print(f"\n=== MAYBE ({len(maybe)}) — borderline, human judgment ===")
    for kjede, name, cid, score in sorted(maybe, key=lambda r: -r[3]):
        print(f"  {kjede:10s} {score:.2f}  {cid:30s}  ← {name!r}")

    print(f"\n=== UNMAPPED ({len(unmapped)}) — either new canonical or whitelist ===")
    for kjede, name, score, cid in sorted(unmapped, key=lambda r: r[1].lower()):
        hint = f"(closest: {cid} @ {score:.2f})" if cid else ""
        print(f"  {kjede:10s}  {name!r}  {hint}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Join data/prices_raw.csv with data/treatments_canonical.yaml using
data/clinic_discovery.yaml for sentral propagation. Emit:

  data/prices_canonical_long.csv      — long-format canonical-mapped table
  data/transform_coverage_report.md   — markdown coverage matrix + audit list

Filter rules at transform time:
  - Drop rows with pris_kilde=helsesmart
  - Drop rows whose behandling_navn_raw is in ikke_kanonisk_men_scrapes
  - Drop rows whose klinikk_id ends in __central (after sentral propagation)

Sentral propagation:
  - For each row in raw with klinikk_id matching a sentral pseudo
    (colosseum__central / oris__central), look up all clinics in
    clinic_discovery.yaml with prisliste_struktur=peker_på_sentral for that
    kjede; emit one canonical_long row per (real_clinic, canonical_id, raw_name).

Usage:
    uv run python tools/transform_to_canonical.py
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PRICES_RAW_PATH = REPO_ROOT / "data" / "prices_raw.csv"
CANONICAL_PATH = REPO_ROOT / "data" / "treatments_canonical.yaml"
MANIFEST_PATH = REPO_ROOT / "data" / "clinic_discovery.yaml"
CANONICAL_LONG_PATH = REPO_ROOT / "data" / "prices_canonical_long.csv"
COVERAGE_REPORT_PATH = REPO_ROOT / "data" / "transform_coverage_report.md"

OUTPUT_COLUMNS = [
    "canonical_id",
    "canonical_navn",
    "kjede",
    "klinikk_id",
    "behandling_navn_raw",
    "pris_min",
    "pris_max",
    "prisformat",
    "pris_kilde",
    "hentet_dato",
    "inkluderer_raw",
    "ekskluderer_raw",
]

KJEDER = ["odontia", "colosseum", "oc", "oris", "oralcare"]


def _kjede_of(klinikk_id: str) -> str:
    return klinikk_id.split("__", 1)[0]


def _build_canonical_index(canonical_doc: dict) -> tuple[dict, dict, set[str]]:
    """Return (name_to_canonical_id, canonical_id_to_navn, whitelist)."""
    name_to_id: dict[tuple[str, str], str] = {}
    id_to_navn: dict[str, str] = {}
    for entry in canonical_doc.get("canonical") or []:
        cid = entry["id"]
        id_to_navn[cid] = entry.get("navn", cid)
        for kjede, synonyms in (entry.get("kjede_terminologi") or {}).items():
            for synonym in synonyms or []:
                name_to_id[(kjede, synonym)] = cid

    whitelist = set((canonical_doc.get("meta") or {}).get("ikke_kanonisk_men_scrapes") or [])
    return name_to_id, id_to_navn, whitelist


def _peker_pa_sentral_clinics(manifest_doc: dict) -> dict[str, list[str]]:
    """kjede → list of klinikk_ids whose prisliste_struktur = peker_på_sentral."""
    out: dict[str, list[str]] = defaultdict(list)
    for entry in manifest_doc.get("clinics") or []:
        if entry.get("prisliste_struktur") == "peker_på_sentral":
            out[entry["kjede"]].append(entry["klinikk_id"])
    return out


def _expand_sentral(
    rows: list[dict], peker_clinics: dict[str, list[str]]
) -> list[dict]:
    """For each sentral row (klinikk_id ends in __central), emit copies for each
    real clinic in that kjede that has prisliste_struktur=peker_på_sentral.
    Drop the original sentral row."""
    expanded: list[dict] = []
    for row in rows:
        if not row["klinikk_id"].endswith("__central"):
            expanded.append(row)
            continue
        kjede = _kjede_of(row["klinikk_id"])
        for real_klinikk_id in peker_clinics.get(kjede, []):
            new_row = dict(row)
            new_row["klinikk_id"] = real_klinikk_id
            expanded.append(new_row)
        # original sentral row is intentionally NOT carried forward
    return expanded


def _load_raw() -> list[dict]:
    with PRICES_RAW_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _emit_canonical_long(
    raw_rows: list[dict], name_to_id: dict, id_to_navn: dict, whitelist: set[str],
    peker_clinics: dict[str, list[str]],
) -> list[dict]:
    # Step 1: filter helsesmart + whitelisted from raw, attach canonical_id.
    mapped: list[dict] = []
    for row in raw_rows:
        if row.get("pris_kilde") == "helsesmart":
            continue
        if row["behandling_navn_raw"] in whitelist:
            continue
        kjede = _kjede_of(row["klinikk_id"])
        canonical_id = name_to_id.get((kjede, row["behandling_navn_raw"]))
        if canonical_id is None:
            # Should not happen post-#24 (100% mapped). Skip silently.
            continue
        mapped.append({**row, "canonical_id": canonical_id})

    # Step 2: propagate sentral pseudo-klinikk rows to real clinics.
    expanded = _expand_sentral(mapped, peker_clinics)

    # Step 3: build the output schema, sort deterministically.
    output_rows: list[dict] = []
    for row in expanded:
        cid = row["canonical_id"]
        output_rows.append({
            "canonical_id": cid,
            "canonical_navn": id_to_navn.get(cid, cid),
            "kjede": _kjede_of(row["klinikk_id"]),
            "klinikk_id": row["klinikk_id"],
            "behandling_navn_raw": row["behandling_navn_raw"],
            "pris_min": row.get("pris_min", ""),
            "pris_max": row.get("pris_max", ""),
            "prisformat": row.get("prisformat", ""),
            "pris_kilde": row.get("pris_kilde", ""),
            "hentet_dato": row.get("hentet_dato", ""),
            "inkluderer_raw": row.get("inkluderer_raw", ""),
            "ekskluderer_raw": row.get("ekskluderer_raw", ""),
        })

    output_rows.sort(key=lambda r: (
        r["canonical_id"], r["kjede"], r["klinikk_id"], r["behandling_navn_raw"]
    ))
    return output_rows


def _write_canonical_long(rows: list[dict]) -> None:
    CANONICAL_LONG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CANONICAL_LONG_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def _coverage_matrix(rows: list[dict], canonical_ids: list[str]) -> dict[tuple[str, str], int]:
    """{(canonical_id, kjede) → row_count} so we can ✓/✗ + show counts."""
    matrix: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        matrix[(row["canonical_id"], row["kjede"])] += 1
    return matrix


def _per_clinic_counts(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["klinikk_id"]] += 1
    return counts


def _write_coverage_report(
    rows: list[dict], canonical_doc: dict, manifest_doc: dict
) -> None:
    canonical_entries = canonical_doc.get("canonical") or []
    canonical_ids = [e["id"] for e in canonical_entries]
    matrix = _coverage_matrix(rows, canonical_ids)
    per_clinic = _per_clinic_counts(rows)

    real_clinics_by_kjede: dict[str, int] = defaultdict(int)
    for entry in manifest_doc.get("clinics") or []:
        struktur = entry.get("prisliste_struktur", "per_klinikk")
        if struktur == "sentral":
            continue  # pseudo-klinikker don't count toward real-clinic totals
        real_clinics_by_kjede[entry["kjede"]] += 1

    lines: list[str] = []
    lines.append(f"# Transform coverage report")
    lines.append("")
    lines.append(f"- Total canonical_long rows: {len(rows)}")
    lines.append(f"- Canonical IDs in YAML: {len(canonical_ids)}")
    lines.append(f"- Real clinics in manifest: {sum(real_clinics_by_kjede.values())}")
    lines.append("")

    # Coverage matrix
    lines.append("## Coverage matrix (canonical × kjede)")
    lines.append("")
    header = "| canonical_id | " + " | ".join(KJEDER) + " |"
    sep = "|" + "|".join(["---"] * (len(KJEDER) + 1)) + "|"
    lines.append(header)
    lines.append(sep)
    for cid in canonical_ids:
        cells = []
        for kjede in KJEDER:
            count = matrix.get((cid, kjede), 0)
            cells.append(f"✓ ({count})" if count else "—")
        lines.append(f"| {cid} | " + " | ".join(cells) + " |")
    lines.append("")

    # Per-canonical totals
    lines.append("## Per-canonical chain coverage")
    lines.append("")
    for cid in canonical_ids:
        chains_with_data = sum(1 for kjede in KJEDER if matrix.get((cid, kjede), 0))
        lines.append(f"- `{cid}`: {chains_with_data}/{len(KJEDER)} chains covered")
    lines.append("")

    # Empty cells
    lines.append("## Empty cells (synonym-round TODO)")
    lines.append("")
    empty_cells = [
        (cid, kjede)
        for cid in canonical_ids
        for kjede in KJEDER
        if not matrix.get((cid, kjede), 0)
    ]
    if not empty_cells:
        lines.append("_None — every canonical has data from every chain._")
    else:
        for cid, kjede in empty_cells:
            lines.append(f"- `{cid}` × `{kjede}`")
    lines.append("")

    # Per-clinic row count summary (sentral propagation sanity)
    lines.append("## Per-clinic row counts")
    lines.append("")
    lines.append("Sentral propagation sanity: every real clinic in a sentral chain ")
    lines.append("(Colosseum, Oris) should have an identical row count.")
    lines.append("")
    for kjede in KJEDER:
        clinics_in_kjede = sorted(k for k in per_clinic if _kjede_of(k) == kjede)
        if not clinics_in_kjede:
            lines.append(f"- **{kjede}**: 0 clinics with data")
            continue
        counts = [per_clinic[k] for k in clinics_in_kjede]
        unique = sorted(set(counts))
        if len(unique) == 1:
            lines.append(
                f"- **{kjede}**: {len(clinics_in_kjede)} clinic(s), "
                f"all with {unique[0]} rows ✓"
            )
        else:
            lines.append(
                f"- **{kjede}**: {len(clinics_in_kjede)} clinic(s), "
                f"variable row counts {unique} ⚠"
            )
    lines.append("")

    COVERAGE_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    canonical_doc = yaml.safe_load(CANONICAL_PATH.read_text(encoding="utf-8")) or {}
    manifest_doc = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}

    name_to_id, id_to_navn, whitelist = _build_canonical_index(canonical_doc)
    peker_clinics = _peker_pa_sentral_clinics(manifest_doc)

    raw_rows = _load_raw()
    canonical_long = _emit_canonical_long(
        raw_rows, name_to_id, id_to_navn, whitelist, peker_clinics
    )

    _write_canonical_long(canonical_long)
    _write_coverage_report(canonical_long, canonical_doc, manifest_doc)

    print(
        f"wrote {len(canonical_long)} canonical_long rows to "
        f"{CANONICAL_LONG_PATH.name} + coverage report"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

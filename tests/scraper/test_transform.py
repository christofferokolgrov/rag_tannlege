"""Smoke test for tools/transform_to_canonical.py.

Per #28 AC + project memory (TDD pure helpers, smoke-test integration),
this is one end-to-end test that runs the script against committed
prices_raw.csv and asserts the output contract.
"""
import csv
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "tools" / "transform_to_canonical.py"
CANONICAL_LONG = REPO_ROOT / "data" / "prices_canonical_long.csv"
COVERAGE_REPORT = REPO_ROOT / "data" / "transform_coverage_report.md"

EXPECTED_COLUMNS = [
    "canonical_id",
    "canonical_navn",
    "lag",
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


def _run_transform() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"transform failed: {result.stderr}"


def _read_canonical_long() -> list[dict]:
    with CANONICAL_LONG.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    _run_transform()
    return _read_canonical_long()


def test_canonical_long_has_expected_columns(rows):
    assert rows, "transform produced no rows"
    assert list(rows[0].keys()) == EXPECTED_COLUMNS


def test_canonical_index_falls_back_to_global_for_unknown_kjede():
    """Per PRD #31 — kjede=single rows look up canonicals via the global
    name index (any-kjede match), so independent clinics scraped from
    HelseSmart get auto-mapped to canonicals like tooth_cleaning without
    needing a `single:` synonym list in the YAML."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "transform_module",
        str(REPO_ROOT / "tools" / "transform_to_canonical.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    canonical_doc = {
        "canonical": [
            {
                "id": "tooth_cleaning",
                "navn": "Tannrens",
                "lag": 2,
                "kjede_terminologi": {
                    "odontia": ["Tannrens", "Tannrens med airflow"],
                    "colosseum": ["Tannrens"],
                    # No "single:" entry intentionally
                },
            },
        ],
        "meta": {"ikke_kanonisk_men_scrapes": []},
    }
    name_to_id, name_to_id_global, _, _, _ = mod._build_canonical_index(canonical_doc)
    # Direct hit — odontia has it
    assert name_to_id.get(("odontia", "Tannrens")) == "tooth_cleaning"
    # Single not directly mapped; global fallback works
    assert ("single", "Tannrens") not in name_to_id
    assert name_to_id_global.get("Tannrens") == "tooth_cleaning"


def test_canonical_long_includes_helsesmart_rows(rows):
    """Per PRD #31, helsesmart-sourced rows are now included (reverses the
    exclusion from slice #28). The Colosseum Majorstuen IMPLANTAT row is the
    canonical example."""
    helsesmart_rows = [r for r in rows if r["pris_kilde"] == "helsesmart"]
    assert helsesmart_rows, "expected at least one helsesmart-sourced row"


def test_canonical_long_excludes_pseudo_klinikk_rows(rows):
    assert all(not r["klinikk_id"].endswith("__central") for r in rows)


def test_canonical_long_includes_all_four_chains(rows):
    assert {r["kjede"] for r in rows} == {"odontia", "colosseum", "oc", "oris"}


def test_canonical_long_sentral_propagation_uniform_for_colosseum(rows):
    """Every real Colosseum clinic should have the same number of
    propagated rows from the central prisliste. Colosseum Majorstuen is
    expected to have ONE extra row (the HelseSmart-sourced IMPLANTAT) per
    PRD #31 — exclude it from the uniformity check."""
    counts_per_clinic: dict[str, int] = {}
    for r in rows:
        if r["kjede"] != "colosseum":
            continue
        # Skip helsesmart-sourced rows; only count sentral-propagated ones
        if r["pris_kilde"] == "helsesmart":
            continue
        counts_per_clinic[r["klinikk_id"]] = counts_per_clinic.get(r["klinikk_id"], 0) + 1
    assert counts_per_clinic, "no Colosseum rows after propagation"
    distinct_counts = set(counts_per_clinic.values())
    assert len(distinct_counts) == 1, (
        f"Colosseum row counts vary across real clinics, expected uniform "
        f"propagation: {sorted(counts_per_clinic.items())[:5]}..."
    )


def test_canonical_long_annual_checkup_covers_all_chains(rows):
    chains = {r["kjede"] for r in rows if r["canonical_id"] == "annual_checkup"}
    assert chains == {"odontia", "colosseum", "oc", "oris"}


def test_canonical_long_is_sorted_deterministically(rows):
    keys = [
        (r["canonical_id"], r["kjede"], r["klinikk_id"], r["behandling_navn_raw"])
        for r in rows
    ]
    assert keys == sorted(keys), "rows are not sorted by (canonical_id, kjede, klinikk_id, raw_name)"


def test_transform_is_idempotent():
    _run_transform()
    first = CANONICAL_LONG.read_bytes()
    _run_transform()
    second = CANONICAL_LONG.read_bytes()
    assert first == second, "transform output differs across runs (not idempotent)"


def test_coverage_report_contains_expected_sections():
    assert COVERAGE_REPORT.exists(), "coverage report not written"
    content = COVERAGE_REPORT.read_text(encoding="utf-8")
    # Headers / sections that should always appear
    assert "Coverage matrix" in content or "coverage matrix" in content.lower()
    # The 4 kjeder should be named columns or rows somewhere
    for kjede in ("odontia", "colosseum", "oc", "oris"):
        assert kjede in content, f"coverage report missing reference to {kjede}"

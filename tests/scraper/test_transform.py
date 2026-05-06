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


def test_canonical_long_excludes_helsesmart_rows(rows):
    assert all(r["pris_kilde"] != "helsesmart" for r in rows)


def test_canonical_long_excludes_pseudo_klinikk_rows(rows):
    assert all(not r["klinikk_id"].endswith("__central") for r in rows)


def test_canonical_long_includes_all_four_chains(rows):
    assert {r["kjede"] for r in rows} == {"odontia", "colosseum", "oc", "oris"}


def test_canonical_long_sentral_propagation_uniform_for_colosseum(rows):
    """Every real Colosseum clinic should have the same number of
    propagated rows (since they all inherit from colosseum__central)."""
    counts_per_clinic: dict[str, int] = {}
    for r in rows:
        if r["kjede"] != "colosseum":
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

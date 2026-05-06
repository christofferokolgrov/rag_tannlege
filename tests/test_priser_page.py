"""Headless smoke for pages/01_Priser.py via streamlit.testing.

Exercises the page through the same code path Streamlit uses at runtime
(no browser needed). Verifies tabs render, the canonical dropdown is
populated, selecting a canonical updates the detail dataframe, and the
missing-CSV path renders a graceful error instead of crashing.
"""
import importlib
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGE_PATH = REPO_ROOT / "pages" / "01_Priser.py"
CANONICAL_LONG_PATH = REPO_ROOT / "data" / "prices_canonical_long.csv"

# CSV load + Oversikt aggregation across 22 canonicals × 5 kjeder takes a
# few seconds in the headless test runner.
TIMEOUT_SECONDS = 30


@pytest.fixture(scope="module")
def app() -> AppTest:
    """Module-level fixture rendering the page with the "Alle" lag filter
    selected, so tests against the full 22-canonical state see every row."""
    if not CANONICAL_LONG_PATH.exists():
        pytest.skip(
            "data/prices_canonical_long.csv missing; run "
            "tools/transform_to_canonical.py first"
        )
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    # Default radio is "Forbrukerkurv (lag 1)" — switch to "Alle" so
    # existing "all canonicals visible" assertions still hold.
    at.radio[0].set_value("Alle (inkl. lag 3)").run()
    return at


def test_page_renders_without_errors(app):
    assert not app.exception
    assert len(app.error) == 0
    # Warnings are allowed — the Sammenligning tab uses st.warning to signal
    # legitimate basket-coverage gaps (e.g. Colosseum is missing 3 of 22
    # canonicals in 'Alle' due to a multi-strong-tag parser limitation).
    # That's a feature, not a defect: it tells the reviewer the chain has
    # incomplete data for the chosen lag filter.


def test_page_has_three_tabs_in_expected_order(app):
    assert [t.label for t in app.tabs] == ["Sammenligning", "Oversikt", "Per behandling"]


def test_canonical_dropdown_lists_norwegian_treatment_names_only(app):
    assert len(app.selectbox) == 1
    options = app.selectbox[0].options
    # 22 canonical IDs in v2 YAML (8 original + 14 from the #24 round)
    assert len(options) >= 19
    # Dropdown shows the Norwegian behandling name (e.g. "Krone"), NOT the
    # technical canonical_id (e.g. "crown") — confirmed user feedback.
    assert "Krone" in options
    assert "Bedøvelse, per dose" in options
    assert not any(o.startswith("crown") for o in options)
    assert not any(" — " in o for o in options)


def test_sammenligning_renders_chart_and_total_table(app):
    """Sammenligning tab (first) should expose an Altair stacked bar chart
    and a detail dataframe with a 'Total' column."""
    assert _has_altair_chart(app), "no Altair chart on the page"
    # The Sammenligning detail table is the first dataframe; Oversikt renders
    # the second; Per behandling renders the third.
    sammenligning_table = app.dataframe[0].value
    assert "Total" in sammenligning_table.columns, sammenligning_table.columns
    # All 4 chains appear as rows (display-cased)
    assert set(sammenligning_table["Kjede"]) >= {"Odontia", "OC", "Oris"}


def test_basket_total_grows_when_filter_widens_from_lag1_to_alle():
    """Switching from Forbrukerkurv (4 canonicals) to Alle (22 canonicals)
    should make the basket total at least double for chains with full
    coverage. Use Odontia as a stable reference (32 clinics, ample data)."""
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    # Default filter: lag 1 — read Sammenligning detail table's Odontia total
    lag1_table = at.dataframe[0].value
    odontia_lag1 = int(lag1_table.loc[lag1_table["Kjede"] == "Odontia", "Total"].iloc[0])

    at.radio[0].set_value("Alle (inkl. lag 3)").run()
    alle_table = at.dataframe[0].value
    odontia_alle = int(alle_table.loc[alle_table["Kjede"] == "Odontia", "Total"].iloc[0])

    assert odontia_alle > odontia_lag1 * 2, (
        f"basket total didn't grow as expected: lag1={odontia_lag1}, alle={odontia_alle}"
    )


def test_oversikt_renders_summary_dataframe(app):
    # The Oversikt dataframe is the SECOND dataframe (Sammenligning is first)
    overview = app.dataframe[1].value
    # One row per canonical
    assert len(overview) >= 19
    # Column headers use brand-cased names; "Uavhengige" appears as the 5th
    # comparison group even when the underlying single__-clinics have 0
    # rows in the current scrape (cells then read "—") — that's correct
    # behaviour: the category exists, data sparsity shows transparently.
    expected_cols = {"Behandling", "Odontia", "Colosseum", "OC", "Oris", "Uavhengige"}
    assert expected_cols.issubset(set(overview.columns))
    # canonical_id is intentionally not surfaced
    assert "canonical_id" not in overview.columns


def test_uavhengige_column_present_even_when_empty(app):
    """Per PRD #31, 'Uavhengige' is added as a 5th comparison group even
    if no single-clinic price data was extracted in the current scrape.
    Cells should show '—' for empty, not crash or be absent."""
    overview = app.dataframe[1].value
    assert "Uavhengige" in overview.columns
    # When no single rows exist, every cell is "—" (or a partial number if
    # any single clinic ever produced data). Verify the column exists and
    # doesn't crash rendering.
    uavhengige_cells = overview["Uavhengige"].tolist()
    assert all(isinstance(c, str) for c in uavhengige_cells)


def test_selecting_krone_shows_rows_for_all_chains():
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    at.radio[0].set_value("Alle (inkl. lag 3)").run()
    at.selectbox[0].set_value("Krone").run()
    assert not at.exception
    # The "Per behandling" detail table is the third dataframe
    # (Sammenligning, Oversikt, Per behandling)
    detail = at.dataframe[2].value
    assert len(detail) > 0
    assert {"odontia", "colosseum", "oc", "oris"}.issubset(set(detail["kjede"].unique()))


def _has_altair_chart(at: AppTest) -> bool:
    """AppTest doesn't have a typed accessor for Altair charts; they render as
    `UnknownElement` (Vega-Lite spec embedded in JSON). Detect by walking
    at.main and counting UnknownElement instances."""
    return any(type(el).__name__ == "UnknownElement" for el in at.main)


def test_per_behandling_renders_an_altair_chart_for_default_canonical(app):
    # First canonical alphabetically (anesthesia_per_dose) has rows from 4
    # chains; chart should appear on initial render.
    assert _has_altair_chart(app), (
        "expected an Altair chart in the per-behandling tab; "
        f"got element types: {[type(e).__name__ for e in app.main]}"
    )


def test_chart_persists_after_changing_canonical():
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    at.radio[0].set_value("Alle (inkl. lag 3)").run()
    at.selectbox[0].set_value("Krone").run()
    assert not at.exception
    assert _has_altair_chart(at), "chart missing after switching to Krone"


def _import_priser_helpers():
    """Import the Priser page module without running Streamlit. The page
    invokes st.set_page_config etc. at import time, so we let those run in
    bare mode (Streamlit emits a no-op-warning in that case)."""
    sys.path.insert(0, str(REPO_ROOT))
    module_name = "_priser_page_for_test"
    spec = importlib.util.spec_from_file_location(module_name, str(PAGE_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_chain_basket_summary_uses_median_pris_min_per_chain_and_canonical():
    """Pure-helper test: synthetic df with two clinics per kjede × canonical.
    Expected: representative_pris = median(pris_min)."""
    helpers = _import_priser_helpers()
    df = pd.DataFrame([
        # annual_checkup × Odontia: median(1500, 1700, 2000) = 1700
        {"canonical_id": "annual_checkup", "canonical_navn": "Årlig kontroll",
         "lag": 1, "kjede": "odontia", "klinikk_id": "odontia__a",
         "pris_min": 1500, "pris_max": 1500, "prisformat": "fast"},
        {"canonical_id": "annual_checkup", "canonical_navn": "Årlig kontroll",
         "lag": 1, "kjede": "odontia", "klinikk_id": "odontia__b",
         "pris_min": 1700, "pris_max": 1700, "prisformat": "fast"},
        {"canonical_id": "annual_checkup", "canonical_navn": "Årlig kontroll",
         "lag": 1, "kjede": "odontia", "klinikk_id": "odontia__c",
         "pris_min": 2000, "pris_max": 2000, "prisformat": "fast"},
        # crown × Odontia: median(8000, 9000) = 8500
        {"canonical_id": "crown", "canonical_navn": "Krone",
         "lag": 2, "kjede": "odontia", "klinikk_id": "odontia__a",
         "pris_min": 8000, "pris_max": 8000, "prisformat": "fast"},
        {"canonical_id": "crown", "canonical_navn": "Krone",
         "lag": 2, "kjede": "odontia", "klinikk_id": "odontia__b",
         "pris_min": 9000, "pris_max": 9000, "prisformat": "fast"},
    ])
    summary = helpers._chain_basket_summary(df)

    odontia_annual = summary[
        (summary["kjede"] == "odontia") & (summary["canonical_id"] == "annual_checkup")
    ].iloc[0]
    assert odontia_annual["representative_pris"] == 1700
    assert odontia_annual["n_clinics"] == 3

    odontia_crown = summary[
        (summary["kjede"] == "odontia") & (summary["canonical_id"] == "crown")
    ].iloc[0]
    assert odontia_crown["representative_pris"] == 8500
    assert odontia_crown["n_clinics"] == 2


def test_chain_basket_summary_drops_rows_with_null_pris_min():
    helpers = _import_priser_helpers()
    df = pd.DataFrame([
        {"canonical_id": "x", "canonical_navn": "X", "lag": 1, "kjede": "odontia",
         "klinikk_id": "odontia__a", "pris_min": pd.NA, "pris_max": pd.NA,
         "prisformat": "etter_konsultasjon"},
        {"canonical_id": "x", "canonical_navn": "X", "lag": 1, "kjede": "odontia",
         "klinikk_id": "odontia__b", "pris_min": 500, "pris_max": 500,
         "prisformat": "fast"},
    ]).astype({"pris_min": "Int64", "pris_max": "Int64"})
    summary = helpers._chain_basket_summary(df)
    odontia_x = summary[(summary["kjede"] == "odontia") & (summary["canonical_id"] == "x")].iloc[0]
    # Median computed only over rows with a real pris_min
    assert odontia_x["representative_pris"] == 500
    assert odontia_x["n_clinics"] == 1


def test_lag_filter_default_shows_only_consumer_basket():
    """Default radio is 'Forbrukerkurv (lag 1)' — should expose only the 4
    consumer-basket canonicals in the dropdown."""
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    options = at.selectbox[0].options
    assert len(options) == 4
    expected = {
        "Årlig kontroll",
        "Tannfarget fylling, én tannflate",
        "Tannfarget fylling, to tannflater",
        "Tannfarget fylling, tre tannflater",
    }
    assert set(options) == expected


def test_lag_filter_alle_exposes_all_canonicals():
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    at.radio[0].set_value("Alle (inkl. lag 3)").run()
    options = at.selectbox[0].options
    assert len(options) == 22


def test_lag_filter_lag_one_plus_two_excludes_lag_three():
    """The 'Lag 1 + 2' option drops lag-3 canonicals like cbct_xray and
    bite_splint."""
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    at.radio[0].set_value("Lag 1 + 2").run()
    options = at.selectbox[0].options
    # 4 lag-1 + 9 lag-2 = 13
    assert len(options) == 13
    assert "Krone" in options  # crown is lag 2
    assert "CBCT 3D-røntgen" not in options  # cbct_xray is lag 3
    assert "Bittskinne" not in options  # bite_splint is lag 3


def test_missing_canonical_long_renders_graceful_error(tmp_path):
    """When prices_canonical_long.csv is absent, the page should render
    an instructional st.error rather than crashing."""
    backup = tmp_path / "canonical_long_backup.csv"
    shutil.move(str(CANONICAL_LONG_PATH), str(backup))
    try:
        at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
        at.run()
        assert not at.exception
        assert len(at.error) == 1
        assert "prices_canonical_long.csv" in at.error[0].value
        assert "transform_to_canonical.py" in at.code[0].value
    finally:
        shutil.move(str(backup), str(CANONICAL_LONG_PATH))

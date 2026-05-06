"""Headless smoke for pages/01_Priser.py via streamlit.testing.

Exercises the page through the same code path Streamlit uses at runtime
(no browser needed). Verifies tabs render, the canonical dropdown is
populated, selecting a canonical updates the detail dataframe, and the
missing-CSV path renders a graceful error instead of crashing.
"""
import shutil
from pathlib import Path

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
    assert len(app.warning) == 0


def test_page_has_oversikt_and_per_behandling_tabs(app):
    assert [t.label for t in app.tabs] == ["Oversikt", "Per behandling"]


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


def test_oversikt_renders_summary_dataframe(app):
    overview = app.dataframe[0].value
    # One row per canonical
    assert len(overview) >= 19
    # Column headers use the chains' real brand-cased names, not the
    # lowercase klinikk_id slugs.
    expected_cols = {"Behandling", "Odontia", "Colosseum", "OC", "Oris"}
    assert expected_cols.issubset(set(overview.columns))
    # canonical_id is intentionally not surfaced
    assert "canonical_id" not in overview.columns


def test_selecting_krone_shows_rows_for_all_chains():
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    at.radio[0].set_value("Alle (inkl. lag 3)").run()
    at.selectbox[0].set_value("Krone").run()
    assert not at.exception
    detail = at.dataframe[1].value
    assert len(detail) > 0
    assert set(detail["kjede"].unique()) == {"odontia", "colosseum", "oc", "oris"}


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

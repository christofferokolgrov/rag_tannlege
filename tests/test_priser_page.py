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
    if not CANONICAL_LONG_PATH.exists():
        pytest.skip(
            "data/prices_canonical_long.csv missing; run "
            "tools/transform_to_canonical.py first"
        )
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    return at


def test_page_renders_without_errors(app):
    assert not app.exception
    assert len(app.error) == 0
    assert len(app.warning) == 0


def test_page_has_oversikt_and_per_behandling_tabs(app):
    assert [t.label for t in app.tabs] == ["Oversikt", "Per behandling"]


def test_canonical_dropdown_lists_all_canonical_ids(app):
    assert len(app.selectbox) == 1
    options = app.selectbox[0].options
    # 22 canonical IDs in v2 YAML (8 original + 14 from the #24 round)
    assert len(options) >= 19
    # Each option follows "<id> — <navn>" format
    assert all(" — " in o for o in options)


def test_oversikt_renders_summary_dataframe(app):
    overview = app.dataframe[0].value
    # One row per canonical, columns: canonical_id, navn, 5 chains
    assert len(overview) >= 19
    expected_cols = {"canonical_id", "navn", "odontia", "colosseum", "oc", "oris", "oralcare"}
    assert expected_cols.issubset(set(overview.columns))


def test_selecting_crown_shows_rows_for_all_five_chains():
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=TIMEOUT_SECONDS)
    at.run()
    crown_label = next(o for o in at.selectbox[0].options if o.startswith("crown"))
    at.selectbox[0].set_value(crown_label).run()
    assert not at.exception
    detail = at.dataframe[1].value
    assert len(detail) > 0
    assert set(detail["kjede"].unique()) == {"odontia", "colosseum", "oc", "oris", "oralcare"}


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

"""Cross-chain price comparison page.

Reads data/prices_canonical_long.csv (produced by
tools/transform_to_canonical.py) and renders two tabs:
  - Oversikt: canonical × kjede summary table with price-range strings
  - Per behandling: dropdown selecting a canonical, filterable table below
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_LONG_PATH = REPO_ROOT / "data" / "prices_canonical_long.csv"

st.set_page_config(page_title="Tannhelse — Priser", page_icon=None)
st.title("Pris-sammenligning på tvers av kjeder")


@st.cache_data
def _load(path_str: str, mtime: float) -> pd.DataFrame:
    """Load canonical_long CSV. mtime is part of the cache key so
    re-running the transform refreshes the page on next interaction."""
    df = pd.read_csv(
        path_str,
        dtype={"pris_min": "Int64", "pris_max": "Int64"},
    )
    return df


def _maybe_load() -> pd.DataFrame | None:
    if not CANONICAL_LONG_PATH.exists():
        st.error(
            "Finner ikke `data/prices_canonical_long.csv`. "
            "Kjør transform-skriptet først:"
        )
        st.code("uv run python tools/transform_to_canonical.py", language="bash")
        return None
    mtime = CANONICAL_LONG_PATH.stat().st_mtime
    return _load(str(CANONICAL_LONG_PATH), mtime)


def _format_price_range(group: pd.DataFrame) -> str:
    """Compact price-range string for the Oversikt cell."""
    mins = group["pris_min"].dropna()
    maxs = group["pris_max"].dropna()
    if mins.empty and maxs.empty:
        return "—"
    lo = int(mins.min()) if not mins.empty else None
    hi = int(maxs.max()) if not maxs.empty else None
    # If any row is "fra", surface that
    has_fra = (group["prisformat"] == "fra").any()
    if has_fra and (hi is None or hi == lo):
        return f"fra {lo}"
    if lo == hi or hi is None:
        return f"{lo}"
    return f"{lo}–{hi}"


def _render_oversikt(df: pd.DataFrame) -> None:
    st.subheader("Pris-spenn per kanonisk behandling × kjede")
    st.caption(
        "Tomme celler = kjeden publiserer ikke denne behandlingen "
        "(eller den er ikke kanonisk-mappet ennå). Tall i parentes = "
        "antall klinikker bak spennet."
    )

    # Group on (canonical_id, canonical_navn, kjede); aggregate via the helper.
    canonical_order = df["canonical_id"].drop_duplicates().tolist()
    rows: list[dict] = []
    for cid in canonical_order:
        navn = df.loc[df["canonical_id"] == cid, "canonical_navn"].iloc[0]
        row: dict[str, str] = {"canonical_id": cid, "navn": navn}
        for kjede in ("odontia", "colosseum", "oc", "oris", "oralcare"):
            cell = df[(df["canonical_id"] == cid) & (df["kjede"] == kjede)]
            if cell.empty:
                row[kjede] = "—"
            else:
                n_clinics = cell["klinikk_id"].nunique()
                row[kjede] = f"{_format_price_range(cell)} ({n_clinics})"
        rows.append(row)

    overview = pd.DataFrame(rows)
    st.dataframe(
        overview,
        use_container_width=True,
        hide_index=True,
        column_config={
            "canonical_id": st.column_config.TextColumn("ID", width="medium"),
            "navn": st.column_config.TextColumn("Behandling", width="large"),
            "odontia": st.column_config.TextColumn("Odontia"),
            "colosseum": st.column_config.TextColumn("Colosseum"),
            "oc": st.column_config.TextColumn("OC"),
            "oris": st.column_config.TextColumn("Oris"),
            "oralcare": st.column_config.TextColumn("OralCare"),
        },
    )


def _render_per_behandling(df: pd.DataFrame) -> None:
    st.subheader("Detaljert sammenligning per behandling")
    canonicals = (
        df[["canonical_id", "canonical_navn"]]
        .drop_duplicates()
        .sort_values("canonical_id")
    )
    if canonicals.empty:
        st.info("Ingen kanoniske behandlinger funnet i datasettet.")
        return

    options = canonicals.apply(
        lambda r: f"{r['canonical_id']} — {r['canonical_navn']}", axis=1
    ).tolist()
    selected_label = st.selectbox("Velg kanonisk behandling:", options=options)
    if not selected_label:
        return

    selected_id = selected_label.split(" — ", 1)[0]
    detail = df[df["canonical_id"] == selected_id].copy()
    detail = detail[
        [
            "kjede",
            "klinikk_id",
            "behandling_navn_raw",
            "pris_min",
            "pris_max",
            "prisformat",
            "pris_kilde",
            "hentet_dato",
        ]
    ].sort_values(["kjede", "pris_min", "klinikk_id"])

    st.caption(
        f"{len(detail)} rader for `{selected_id}` på tvers av "
        f"{detail['klinikk_id'].nunique()} klinikker."
    )
    st.dataframe(
        detail,
        use_container_width=True,
        hide_index=True,
    )


df = _maybe_load()
if df is None:
    st.stop()

oversikt_tab, detail_tab = st.tabs(["Oversikt", "Per behandling"])
with oversikt_tab:
    _render_oversikt(df)
with detail_tab:
    _render_per_behandling(df)

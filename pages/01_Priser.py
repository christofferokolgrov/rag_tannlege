"""Cross-chain price comparison page.

Reads data/prices_canonical_long.csv (produced by
tools/transform_to_canonical.py) and renders two tabs:
  - Oversikt: canonical × kjede summary table with price-range strings
  - Per behandling: dropdown selecting a canonical, filterable table below
"""
from __future__ import annotations

from pathlib import Path

import altair as alt
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
        width="stretch",
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
    _render_per_behandling_chart(detail)
    st.dataframe(
        detail,
        width="stretch",
        hide_index=True,
    )


def _render_per_behandling_chart(detail: pd.DataFrame) -> None:
    """Horizontal range bars per (kjede, behandling_navn_raw). Bars span
    pris_min → pris_max for fast/spread, or pris_min → pris_min × 1.5
    (with a "fra" badge) for fra-format rows where pris_max is null.
    """
    if detail.empty or detail["pris_min"].dropna().empty:
        st.info("Ingen tallpriser å vise i diagrammet for denne behandlingen.")
        return

    # Aggregate to one bar per (kjede, raw_name): min(pris_min), max(pris_max),
    # n_clinics. Sentral propagation otherwise renders 91 identical bars per
    # Colosseum row, which is visual noise.
    agg = (
        detail.dropna(subset=["pris_min"])
        .groupby(["kjede", "behandling_navn_raw"], dropna=False)
        .agg(
            pris_min=("pris_min", "min"),
            pris_max=("pris_max", "max"),
            n_clinics=("klinikk_id", "nunique"),
            prisformat=("prisformat", "first"),
        )
        .reset_index()
    )
    fra_extension = (agg["pris_min"].astype("Int64") * 3 // 2).astype("Int64")
    agg["pris_max_filled"] = agg["pris_max"].fillna(fra_extension)
    agg["label"] = (
        agg["kjede"] + " · " + agg["behandling_navn_raw"].apply(_wrap_label)
    )
    agg["range_text"] = agg.apply(_format_bar_text, axis=1)

    # Sort labels by kjede then pris_min so chains group visually.
    sort_order = (
        agg.sort_values(["kjede", "pris_min"])["label"].tolist()
    )

    color = alt.Color("kjede:N", legend=alt.Legend(title="Kjede"))
    # labelLimit=400 + multi-line labels (\n inside the string) keeps long
    # treatment names readable instead of truncating to "Tannkrone met…".
    common_y = alt.Y(
        "label:N",
        sort=sort_order,
        title=None,
        axis=alt.Axis(labelLimit=400, labelFontSize=11, labelLineHeight=12),
    )
    tooltip = [
        alt.Tooltip("kjede:N", title="Kjede"),
        alt.Tooltip("behandling_navn_raw:N", title="Navn på prisliste"),
        alt.Tooltip("pris_min:Q", title="Pris min"),
        alt.Tooltip("pris_max:Q", title="Pris max"),
        alt.Tooltip("prisformat:N", title="Prisformat"),
        alt.Tooltip("n_clinics:Q", title="Antall klinikker"),
    ]

    # Dumbbell chart — works equally well for fast (single value), spread
    # (range), and fra (open right end) rows. A pure mark_bar gave zero-width
    # invisible bars for fast rows where pris_min == pris_max.
    rule = (
        alt.Chart(agg)
        .mark_rule(strokeWidth=3, opacity=0.8)
        .encode(
            x=alt.X("pris_min:Q", title="NOK"),
            x2="pris_max_filled:Q",
            y=common_y,
            color=color,
            tooltip=tooltip,
        )
    )

    min_dot = (
        alt.Chart(agg)
        .mark_circle(size=120)
        .encode(x="pris_min:Q", y=common_y, color=color, tooltip=tooltip)
    )

    # Second dot only when pris_max is a real value distinct from pris_min
    # (i.e. true spread) — fra-format rows show a single dot + extending rule
    # + the "fra X" text label rather than a misleading second dot.
    spread_only = agg[
        agg["pris_max"].notna() & (agg["pris_max"] != agg["pris_min"])
    ]
    max_dot = (
        alt.Chart(spread_only)
        .mark_circle(size=120)
        .encode(x="pris_max:Q", y=common_y, color=color, tooltip=tooltip)
    )

    text = (
        alt.Chart(agg)
        .mark_text(align="left", baseline="middle", dx=8, fontSize=11)
        .encode(
            x="pris_max_filled:Q",
            y=common_y,
            text="range_text:N",
        )
    )

    chart = (rule + min_dot + max_dot + text).properties(height=alt.Step(24))
    st.altair_chart(chart, width="stretch")


def _wrap_label(text: str, width: int = 35) -> str:
    """Insert newlines so long behandling names wrap rather than truncate.
    Vega-Lite axis labels respect '\\n' as a line break (and Streamlit's
    Altair embed renders them as multi-line)."""
    if len(text) <= width:
        return text
    import textwrap
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def _format_bar_text(row: pd.Series) -> str:
    if row["prisformat"] == "fra":
        return f"fra {int(row['pris_min'])}"
    if pd.isna(row["pris_max"]) or row["pris_max"] == row["pris_min"]:
        return f"{int(row['pris_min'])}"
    return f"{int(row['pris_min'])}–{int(row['pris_max'])}"


df = _maybe_load()
if df is None:
    st.stop()

oversikt_tab, detail_tab = st.tabs(["Oversikt", "Per behandling"])
with oversikt_tab:
    _render_oversikt(df)
with detail_tab:
    _render_per_behandling(df)

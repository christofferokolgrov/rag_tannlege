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

KJEDE_DISPLAY = {
    "odontia": "Odontia",
    "colosseum": "Colosseum",
    "oc": "OC",
    "oris": "Oris",
    "single": "Uavhengige",
}
KJEDE_ORDER = ["odontia", "colosseum", "oc", "oris", "single"]

st.set_page_config(page_title="Tannhelse — Priser", page_icon=None)
st.title("Pris-sammenligning på tvers av kjeder")


@st.cache_data
def _load(path_str: str, mtime: float) -> pd.DataFrame:
    """Load canonical_long CSV. mtime is part of the cache key so
    re-running the transform refreshes the page on next interaction."""
    df = pd.read_csv(
        path_str,
        dtype={"pris_min": "Int64", "pris_max": "Int64", "lag": "Int64"},
    )
    return df


LAG_FILTERS = {
    "Forbrukerkurv (lag 1)": {1},
    "Lag 1 + 2": {1, 2},
    "Alle (inkl. lag 3)": {1, 2, 3},
}


def _apply_lag_filter(df: pd.DataFrame) -> pd.DataFrame:
    choice = st.radio(
        "Vis behandlingsnivå:",
        options=list(LAG_FILTERS),
        horizontal=True,
        help=(
            "Lag 1 = de 4 ofte-bestilte behandlingene som alle 4 store kjeder "
            "publiserer pris for (årlig kontroll + tannfarget fylling 1/2/3 flater). "
            "Lag 2 = øvrige behandlinger med full 4/4 dekning. "
            "Lag 3 = behandlinger der minst én kjede mangler pris."
        ),
    )
    return df[df["lag"].isin(LAG_FILTERS[choice])]


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


def _chain_basket_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate canonical_long rows to one summary row per (kjede,
    canonical_id), using the median of pris_min as the representative price.

    Rationale:
    - median is robust to outliers (e.g. Asker's anomalous 320 NOK Tannrens
      with airflow which the page legitimately publishes but which would
      otherwise skew the chain's basket total)
    - pris_min is consistent across prisformat values: it's the floor for
      fra-format rows (where pris_max is null), the cheap end for spread,
      and equals pris_max for fast.
    - Rows without a numeric pris_min (pure etter_konsultasjon) are dropped.

    Returns columns: canonical_id, canonical_navn, lag, kjede,
    representative_pris (Int), n_clinics (int).
    """
    priced = df.dropna(subset=["pris_min"]).copy()
    if priced.empty:
        return pd.DataFrame(columns=[
            "canonical_id", "canonical_navn", "lag", "kjede",
            "representative_pris", "n_clinics",
        ])
    grouped = (
        priced.groupby(["canonical_id", "canonical_navn", "lag", "kjede"], dropna=False)
        .agg(
            representative_pris=("pris_min", "median"),
            n_clinics=("klinikk_id", "nunique"),
        )
        .reset_index()
    )
    grouped["representative_pris"] = grouped["representative_pris"].round().astype("Int64")
    return grouped


def _render_sammenligning(df: pd.DataFrame) -> None:
    st.subheader("Total kurv-pris per kjede")
    summary = _chain_basket_summary(df)
    if summary.empty:
        st.info("Ingen tallpriser i valgt kurv.")
        return

    n_canonicals_total = df["canonical_id"].nunique()
    coverage = summary.groupby("kjede")["canonical_id"].nunique()
    incomplete = coverage[coverage < n_canonicals_total]

    st.caption(
        f"Sum av median pris-min per behandling i kurven ({n_canonicals_total} "
        f"kanoniske behandlinger). "
        "For 'fra'-priser er gulvverdien brukt — faktisk pris kan være høyere."
    )
    if not incomplete.empty:
        missing = ", ".join(
            f"{KJEDE_DISPLAY.get(k, k)} (mangler {n_canonicals_total - n} av "
            f"{n_canonicals_total})"
            for k, n in incomplete.items()
        )
        st.warning(f"Ufullstendig basket-dekning: {missing}")

    summary_for_chart = summary.copy()
    summary_for_chart["kjede_display"] = (
        summary_for_chart["kjede"].map(KJEDE_DISPLAY).fillna(summary_for_chart["kjede"])
    )

    kjede_order_display = [
        KJEDE_DISPLAY[k] for k in KJEDE_ORDER if k in summary["kjede"].values
    ]

    chart = (
        alt.Chart(summary_for_chart)
        .mark_bar()
        .encode(
            x=alt.X(
                "representative_pris:Q",
                stack="zero",
                title="Total NOK (median pris-min summert)",
            ),
            y=alt.Y(
                "kjede_display:N",
                sort=kjede_order_display,
                title=None,
                axis=alt.Axis(labelFontSize=12),
            ),
            color=alt.Color(
                "canonical_navn:N", legend=alt.Legend(title="Behandling"),
            ),
            tooltip=[
                alt.Tooltip("kjede_display:N", title="Kjede"),
                alt.Tooltip("canonical_navn:N", title="Behandling"),
                alt.Tooltip("representative_pris:Q", title="Median pris (NOK)"),
                alt.Tooltip("n_clinics:Q", title="Antall klinikker"),
                alt.Tooltip("lag:Q", title="Lag"),
            ],
        )
        .properties(height=alt.Step(38))
    )
    st.altair_chart(chart, width="stretch")

    # Detail table: pivot to rows=kjede, columns=canonical_navn + Total
    pivot = summary.pivot_table(
        index="kjede",
        columns="canonical_navn",
        values="representative_pris",
        aggfunc="first",
    )
    pivot.index = [KJEDE_DISPLAY.get(k, k) for k in pivot.index]
    pivot.index.name = "Kjede"
    # Only sum across canonicals the chain has data for (NaN cells excluded)
    pivot["Total"] = pivot.sum(axis=1, skipna=True).astype("Int64")
    pivot = pivot.reindex([KJEDE_DISPLAY[k] for k in KJEDE_ORDER if KJEDE_DISPLAY[k] in pivot.index])
    pivot = pivot.reset_index()
    st.caption("Detaljer — median pris per behandling, per kjede:")
    st.dataframe(pivot, width="stretch", hide_index=True)


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

    # Group on (canonical_navn, kjede); aggregate via the helper. canonical_id
    # is intentionally not surfaced — only the Norwegian behandling name.
    canonical_order = df["canonical_id"].drop_duplicates().tolist()
    rows: list[dict] = []
    for cid in canonical_order:
        navn = df.loc[df["canonical_id"] == cid, "canonical_navn"].iloc[0]
        row: dict[str, str] = {"Behandling": navn}
        for kjede in KJEDE_ORDER:
            display = KJEDE_DISPLAY[kjede]
            cell = df[(df["canonical_id"] == cid) & (df["kjede"] == kjede)]
            if cell.empty:
                row[display] = "—"
            else:
                n_clinics = cell["klinikk_id"].nunique()
                row[display] = f"{_format_price_range(cell)} ({n_clinics})"
        rows.append(row)

    overview = pd.DataFrame(rows)
    st.dataframe(overview, width="stretch", hide_index=True)


def _render_per_behandling(df: pd.DataFrame) -> None:
    st.subheader("Detaljert sammenligning per behandling")
    canonicals = (
        df[["canonical_id", "canonical_navn"]]
        .drop_duplicates()
        .sort_values("canonical_navn")
    )
    if canonicals.empty:
        st.info("Ingen kanoniske behandlinger funnet i datasettet.")
        return

    # Dropdown shows the Norwegian behandling name only; we look the
    # canonical_id back up via a navn → id index.
    navn_to_id = dict(zip(canonicals["canonical_navn"], canonicals["canonical_id"]))
    selected_navn = st.selectbox("Velg behandling:", options=list(navn_to_id))
    if not selected_navn:
        return

    selected_id = navn_to_id[selected_navn]
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
    agg["kjede_display"] = agg["kjede"].map(KJEDE_DISPLAY).fillna(agg["kjede"])
    agg["label"] = (
        agg["kjede_display"] + " · " + agg["behandling_navn_raw"].apply(_wrap_label)
    )
    agg["range_text"] = agg.apply(_format_bar_text, axis=1)

    # Sort labels by kjede then pris_min so chains group visually.
    sort_order = (
        agg.sort_values(["kjede", "pris_min"])["label"].tolist()
    )

    color = alt.Color(
        "kjede_display:N",
        legend=alt.Legend(title="Kjede"),
        sort=[KJEDE_DISPLAY[k] for k in KJEDE_ORDER if k in agg["kjede"].values],
    )
    # labelLimit=400 + multi-line labels (\n inside the string) keeps long
    # treatment names readable instead of truncating to "Tannkrone met…".
    common_y = alt.Y(
        "label:N",
        sort=sort_order,
        title=None,
        axis=alt.Axis(labelLimit=400, labelFontSize=11, labelLineHeight=12),
    )
    tooltip = [
        alt.Tooltip("kjede_display:N", title="Kjede"),
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

df = _apply_lag_filter(df)

sammenligning_tab, oversikt_tab, detail_tab = st.tabs(
    ["Sammenligning", "Oversikt", "Per behandling"]
)
with sammenligning_tab:
    _render_sammenligning(df)
with oversikt_tab:
    _render_oversikt(df)
with detail_tab:
    _render_per_behandling(df)

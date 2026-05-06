"""Per-clinic price detail for smaller players (Odontia median + uavhengige).

Where 01_Priser_-_Peers.py compares the 5 kjeder as monolithic units, this
page focuses on the small-player pool: 14 independent Oslo-area clinics as
individual rows, plus a single synthetic "Odontia (median)" row that
aggregates the 32 Odontia per-klinikk prices via median. Lets you compare
each independent against an Odontia benchmark on equal footing.

Reads data/prices_canonical_long.csv + data/clinics.csv.
"""
from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_LONG_PATH = REPO_ROOT / "data" / "prices_canonical_long.csv"
CLINICS_PATH = REPO_ROOT / "data" / "clinics.csv"

POOL = ["odontia", "single"]
KJEDE_DISPLAY = {"odontia": "Odontia", "single": "Uavhengige"}

st.set_page_config(page_title="Tannhelse — Priser uavhengige", page_icon=None)
st.title("Pris-detalj: mindre aktører (Odontia + uavhengige)")


ODONTIA_MEDIAN_ID = "odontia__median"


@st.cache_data
def _load(path_str: str, mtime: float) -> pd.DataFrame:
    df = pd.read_csv(
        path_str,
        dtype={"pris_min": "Int64", "pris_max": "Int64", "lag": "Int64"},
    )
    return df[df["kjede"].isin(POOL)].copy()


@st.cache_data
def _load_clinic_names(path_str: str, mtime: float) -> dict[str, str]:
    cdf = pd.read_csv(path_str)
    return dict(zip(cdf["klinikk_id"], cdf["klinikk_navn"]))


def _aggregate_odontia_to_median(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Replace all odontia rows with one synthetic median row per canonical.

    Single-clinic rows are passed through. Median is taken across both
    pris_min and pris_max (where defined). Returns (transformed_df,
    n_odontia_clinics) so the caller can label the synthetic row.
    """
    odontia = df[df["kjede"] == "odontia"]
    others = df[df["kjede"] != "odontia"]
    if odontia.empty:
        return df, 0
    n_clinics = odontia["klinikk_id"].nunique()
    agg = (
        odontia.groupby(
            ["canonical_id", "canonical_navn", "lag"], dropna=False
        )
        .agg(
            pris_min=("pris_min", "median"),
            pris_max=("pris_max", "median"),
            prisformat=(
                "prisformat",
                lambda s: s.mode().iloc[0] if not s.mode().empty else "fast",
            ),
            pris_kilde=("pris_kilde", "first"),
            hentet_dato=("hentet_dato", "max"),
            behandling_navn_raw=("behandling_navn_raw", "first"),
            inkluderer_raw=("inkluderer_raw", "first"),
            ekskluderer_raw=("ekskluderer_raw", "first"),
        )
        .reset_index()
    )
    agg["klinikk_id"] = ODONTIA_MEDIAN_ID
    agg["kjede"] = "odontia"
    agg["pris_min"] = agg["pris_min"].round().astype("Int64")
    agg["pris_max"] = agg["pris_max"].round().astype("Int64")
    return pd.concat([others, agg], ignore_index=True), n_clinics


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
            "publiserer pris for. Lag 2 = øvrige med full 4/4 dekning. "
            "Lag 3 = behandlinger der minst én kjede mangler pris (inkl. de "
            "single-spesifikke som tannbro, bleking, perio)."
        ),
    )
    return df[df["lag"].isin(LAG_FILTERS[choice])]


def _maybe_load() -> tuple[pd.DataFrame, dict[str, str]] | None:
    if not CANONICAL_LONG_PATH.exists():
        st.error("Finner ikke `data/prices_canonical_long.csv`.")
        st.code("uv run python tools/transform_to_canonical.py", language="bash")
        return None
    mtime = CANONICAL_LONG_PATH.stat().st_mtime
    df = _load(str(CANONICAL_LONG_PATH), mtime)
    names = _load_clinic_names(str(CLINICS_PATH), CLINICS_PATH.stat().st_mtime)
    return df, names


def _clinic_basket_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (klinikk_id, canonical_id): pris_min as the representative
    price for the basket sum. pris_min is the floor for fra-format and the
    cheap end for spread; consistent across formats.
    """
    priced = df.dropna(subset=["pris_min"]).copy()
    if priced.empty:
        return pd.DataFrame(columns=[
            "klinikk_id", "kjede", "canonical_id", "canonical_navn",
            "lag", "representative_pris",
        ])
    grouped = (
        priced.groupby(
            ["klinikk_id", "kjede", "canonical_id", "canonical_navn", "lag"],
            dropna=False,
        )
        .agg(representative_pris=("pris_min", "median"))
        .reset_index()
    )
    grouped["representative_pris"] = (
        grouped["representative_pris"].round().astype("Int64")
    )
    return grouped


def _render_sammenligning(df: pd.DataFrame, clinic_names: dict[str, str]) -> None:
    st.subheader("Total kurv-pris per klinikk")
    n_canonicals_total = df["canonical_id"].nunique()
    only_complete = st.toggle(
        "Vis kun klinikker med fullstendig data",
        value=False,
        help=(
            "På: skjul klinikker som mangler pris for én eller flere "
            "kanoniske behandlinger i valgt kurv. Lar deg sammenligne på "
            "likt grunnlag, men reduserer antall klinikker."
        ),
    )

    summary = _clinic_basket_summary(df)
    if summary.empty:
        st.info("Ingen tallpriser i valgt kurv.")
        return

    coverage = summary.groupby("klinikk_id")["canonical_id"].nunique()
    if only_complete:
        complete_ids = coverage[coverage == n_canonicals_total].index
        summary = summary[summary["klinikk_id"].isin(complete_ids)]
        if summary.empty:
            st.warning(
                f"Ingen klinikker har pris for alle {n_canonicals_total} "
                "behandlinger i valgt kurv. Skru av toggle eller velg "
                "smalere kurv (f.eks. Forbrukerkurv)."
            )
            return

    totals = (
        summary.groupby(["klinikk_id", "kjede"])
        .agg(
            total=("representative_pris", "sum"),
            n_canonicals=("canonical_id", "nunique"),
        )
        .reset_index()
        .sort_values("total")
    )
    totals["klinikk_navn"] = totals["klinikk_id"].map(clinic_names).fillna(totals["klinikk_id"])
    totals["kjede_display"] = totals["kjede"].map(KJEDE_DISPLAY)
    totals["mangler"] = n_canonicals_total - totals["n_canonicals"]

    st.caption(
        f"Sum av pris-min for {n_canonicals_total} behandlinger i valgt kurv. "
        "Klinikker er sortert fra billigst til dyrest. "
        "For 'fra'-priser brukes gulvverdien — faktisk pris kan være høyere."
    )
    has_partial = (totals["mangler"] > 0).any()
    if has_partial and not only_complete:
        st.caption(
            ":warning: Noen klinikker mangler én eller flere behandlinger og "
            "har dermed undervurdert total. Se 'mangler'-kolonnen i tabellen "
            "under, eller skru på toggle for full sammenlignbarhet."
        )

    chart = (
        alt.Chart(totals)
        .mark_bar()
        .encode(
            x=alt.X("total:Q", title="Total NOK (sum pris-min)"),
            y=alt.Y(
                "klinikk_navn:N",
                sort=totals["klinikk_navn"].tolist(),
                title=None,
                axis=alt.Axis(labelLimit=300, labelFontSize=11),
            ),
            color=alt.Color(
                "kjede_display:N",
                legend=alt.Legend(title="Kjede"),
                scale=alt.Scale(
                    domain=["Odontia", "Uavhengige"],
                    range=["#4c72b0", "#dd8452"],
                ),
            ),
            tooltip=[
                alt.Tooltip("klinikk_navn:N", title="Klinikk"),
                alt.Tooltip("kjede_display:N", title="Kjede"),
                alt.Tooltip("total:Q", title="Total NOK"),
                alt.Tooltip("n_canonicals:Q", title="Antall behandlinger med pris"),
                alt.Tooltip("mangler:Q", title="Mangler i kurv"),
            ],
        )
        .properties(height=alt.Step(22))
    )
    st.altair_chart(chart, width="stretch")

    st.caption("Detaljer:")
    detail = totals[["klinikk_navn", "kjede_display", "total", "n_canonicals", "mangler"]]
    detail = detail.rename(columns={
        "klinikk_navn": "Klinikk",
        "kjede_display": "Kjede",
        "total": "Total NOK",
        "n_canonicals": "Behandlinger med pris",
        "mangler": "Mangler",
    })
    st.dataframe(detail, width="stretch", hide_index=True)


def _render_per_klinikk_oversikt(df: pd.DataFrame, clinic_names: dict[str, str]) -> None:
    st.subheader("Pris per klinikk × behandling")
    st.caption(
        "Hver rad = klinikk, hver kolonne = kanonisk behandling. "
        "Tall i celler er pris-min (gulvverdien). '—' = ingen publisert pris. "
        "Sorter / filtrer ved å klikke på kolonneoverskrifter."
    )

    summary = _clinic_basket_summary(df)
    if summary.empty:
        st.info("Ingen tallpriser i valgt kurv.")
        return

    summary["klinikk_navn"] = (
        summary["klinikk_id"].map(clinic_names).fillna(summary["klinikk_id"])
    )
    summary["kjede_display"] = summary["kjede"].map(KJEDE_DISPLAY)

    pivot = summary.pivot_table(
        index=["klinikk_navn", "kjede_display"],
        columns="canonical_navn",
        values="representative_pris",
        aggfunc="first",
    ).reset_index()
    pivot = pivot.rename(columns={"klinikk_navn": "Klinikk", "kjede_display": "Kjede"})
    pivot = pivot.sort_values(["Kjede", "Klinikk"])
    st.dataframe(pivot, width="stretch", hide_index=True)


def _render_per_behandling(df: pd.DataFrame, clinic_names: dict[str, str]) -> None:
    st.subheader("Per behandling — pris-spenn på tvers av klinikker")
    canonicals = (
        df[["canonical_id", "canonical_navn"]].drop_duplicates().sort_values("canonical_navn")
    )
    if canonicals.empty:
        st.info("Ingen kanoniske behandlinger.")
        return

    navn_to_id = dict(zip(canonicals["canonical_navn"], canonicals["canonical_id"]))
    selected_navn = st.selectbox("Velg behandling:", options=list(navn_to_id))
    if not selected_navn:
        return

    selected_id = navn_to_id[selected_navn]
    detail = df[df["canonical_id"] == selected_id].copy()
    if detail.empty or detail["pris_min"].dropna().empty:
        st.info("Ingen tallpriser for denne behandlingen i klinikk-poolen.")
        return

    detail["klinikk_navn"] = detail["klinikk_id"].map(clinic_names).fillna(detail["klinikk_id"])
    detail["kjede_display"] = detail["kjede"].map(KJEDE_DISPLAY)

    # One row per (klinikk, raw_name): if a clinic has multiple raw rows
    # mapping to the same canonical, show min/max of the range.
    agg = (
        detail.dropna(subset=["pris_min"])
        .groupby(["klinikk_id", "klinikk_navn", "kjede", "kjede_display"], dropna=False)
        .agg(
            pris_min=("pris_min", "min"),
            pris_max=("pris_max", "max"),
            prisformat=("prisformat", "first"),
        )
        .reset_index()
        .sort_values("pris_min")
    )
    fra_extension = (agg["pris_min"].astype("Int64") * 3 // 2).astype("Int64")
    agg["pris_max_filled"] = agg["pris_max"].fillna(fra_extension)
    agg["range_text"] = agg.apply(_format_bar_text, axis=1)

    sort_order = agg["klinikk_navn"].tolist()
    color = alt.Color(
        "kjede_display:N",
        legend=alt.Legend(title="Kjede"),
        scale=alt.Scale(
            domain=["Odontia", "Uavhengige"],
            range=["#4c72b0", "#dd8452"],
        ),
    )
    common_y = alt.Y(
        "klinikk_navn:N",
        sort=sort_order,
        title=None,
        axis=alt.Axis(labelLimit=300, labelFontSize=11),
    )
    tooltip = [
        alt.Tooltip("klinikk_navn:N", title="Klinikk"),
        alt.Tooltip("kjede_display:N", title="Kjede"),
        alt.Tooltip("pris_min:Q", title="Pris min"),
        alt.Tooltip("pris_max:Q", title="Pris max"),
        alt.Tooltip("prisformat:N", title="Prisformat"),
    ]

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
        alt.Chart(agg).mark_circle(size=120)
        .encode(x="pris_min:Q", y=common_y, color=color, tooltip=tooltip)
    )
    spread_only = agg[agg["pris_max"].notna() & (agg["pris_max"] != agg["pris_min"])]
    max_dot = (
        alt.Chart(spread_only).mark_circle(size=120)
        .encode(x="pris_max:Q", y=common_y, color=color, tooltip=tooltip)
    )
    text = (
        alt.Chart(agg)
        .mark_text(align="left", baseline="middle", dx=8, fontSize=11)
        .encode(x="pris_max_filled:Q", y=common_y, text="range_text:N")
    )

    chart = (rule + min_dot + max_dot + text).properties(height=alt.Step(22))
    st.caption(
        f"{len(agg)} klinikker har pris for `{selected_id}`. "
        "Sortert billigst → dyrest."
    )
    st.altair_chart(chart, width="stretch")


def _format_bar_text(row: pd.Series) -> str:
    if row["prisformat"] == "fra":
        return f"fra {int(row['pris_min'])}"
    if pd.isna(row["pris_max"]) or row["pris_max"] == row["pris_min"]:
        return f"{int(row['pris_min'])}"
    return f"{int(row['pris_min'])}–{int(row['pris_max'])}"


loaded = _maybe_load()
if loaded is None:
    st.stop()

df, clinic_names = loaded
df, n_odontia = _aggregate_odontia_to_median(df)
if n_odontia:
    clinic_names = {
        **clinic_names,
        ODONTIA_MEDIAN_ID: f"Odontia (median, {n_odontia} klinikker)",
    }
df = _apply_lag_filter(df)

sammen_tab, oversikt_tab, behandling_tab = st.tabs(
    ["Sammenligning", "Per-klinikk oversikt", "Per behandling"]
)
with sammen_tab:
    _render_sammenligning(df, clinic_names)
with oversikt_tab:
    _render_per_klinikk_oversikt(df, clinic_names)
with behandling_tab:
    _render_per_behandling(df, clinic_names)

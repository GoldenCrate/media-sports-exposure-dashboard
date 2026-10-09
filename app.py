"""Media & Sports Brand-Exposure Analytics — Streamlit dashboard.

A portfolio demo built on SYNTHETIC sponsorship/broadcast data. It measures
how much on-screen exposure, audience impressions and equivalent media value
each sponsor brand earns across sports, leagues, events and time.

Chart design follows Cole Nussbaumer Knaflic's "Storytelling with Data":
takeaway titles instead of generic ones, decluttered axes, direct labels,
and restrained color (grey context + one highlight color for the point).

Author: Leo Chan — github.com/GoldenCrate
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

import analytics
from data_gen import brand_spend, generate_data

# --- Theme / color ---------------------------------------------------------
GREY = "#B8B8B8"
HIGHLIGHT = "#1F77B4"   # single restrained accent
POSITIVE = "#2E7D32"
NEGATIVE = "#C62828"

st.set_page_config(
    page_title="Media & Sports Brand-Exposure Analytics",
    page_icon="📺",
    layout="wide",
)


@st.cache_data
def load_data():
    return generate_data(), brand_spend()


def fmt_usd(x: float) -> str:
    if x >= 1_000_000:
        return f"${x/1_000_000:,.1f}M"
    if x >= 1_000:
        return f"${x/1_000:,.0f}K"
    return f"${x:,.0f}"


def fmt_num(x: float) -> str:
    if x >= 1_000_000_000:
        return f"{x/1_000_000_000:,.1f}B"
    if x >= 1_000_000:
        return f"{x/1_000_000:,.1f}M"
    if x >= 1_000:
        return f"{x/1_000:,.0f}K"
    return f"{x:,.0f}"


def sowhat(text: str) -> None:
    """Render a 'So what / recommendation' callout."""
    st.markdown(
        f"""<div style="background:#F3F6FA;border-left:4px solid {HIGHLIGHT};
        padding:0.75rem 1rem;border-radius:4px;margin-top:0.5rem;">
        <strong>So what →</strong> {text}</div>""",
        unsafe_allow_html=True,
    )


df, spend = load_data()

# --- Sidebar filters -------------------------------------------------------
st.sidebar.title("Filters")
st.sidebar.caption("All data is synthetic (fixed seed). See README.")

sports = sorted(df["sport"].unique())
sel_sports = st.sidebar.multiselect("Sport", sports, default=sports)

brands = sorted(df["brand"].unique())
sel_brands = st.sidebar.multiselect("Brand", brands, default=brands)

fdf = df[df["sport"].isin(sel_sports) & df["brand"].isin(sel_brands)]
if fdf.empty:
    st.warning("No data for the current filter selection. Widen the filters.")
    st.stop()

view = st.sidebar.radio(
    "View",
    ["Overview", "Share of Voice", "Sport & Event Breakdown",
     "Trend Over Time", "Sponsorship ROI"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Author:** Leo Chan  \n[github.com/GoldenCrate](https://github.com/GoldenCrate)")

# --- Header ----------------------------------------------------------------
st.title("Media & Sports Brand-Exposure Analytics")
st.caption(
    "SYNTHETIC DEMO DATA — reproducible from a fixed seed. "
    "Measures sponsor on-screen exposure, audience impressions and equivalent media value."
)


# ===========================================================================
# VIEW 1 — OVERVIEW / KPI TILES
# ===========================================================================
if view == "Overview":
    k = analytics.kpi_summary(fdf)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Brand impressions", fmt_num(k["total_impressions"]))
    c2.metric("Equivalent media value", fmt_usd(k["total_media_value"]))
    c3.metric("Broadcast hours analyzed", f"{k['broadcast_hours']:,.0f}")
    c4.metric(
        f"Top brand SOV — {k['top_brand']}",
        f"{k['top_brand_sov_pct']:.1f}%",
    )

    st.markdown("### Where the exposure is concentrated")
    left, right = st.columns(2)

    # Top brands by media value (highlight the leader).
    sov = analytics.share_of_voice(fdf).head(8)
    sov["is_top"] = sov["brand"] == k["top_brand"]
    bar = (
        alt.Chart(sov, title=f"{k['top_brand']} leads share of voice by media value")
        .mark_bar()
        .encode(
            x=alt.X("media_value_usd:Q", title=None, axis=alt.Axis(format="$,.0s")),
            y=alt.Y("brand:N", sort="-x", title=None),
            color=alt.condition(alt.datum.is_top, alt.value(HIGHLIGHT), alt.value(GREY)),
            tooltip=[
                alt.Tooltip("brand:N"),
                alt.Tooltip("media_value_usd:Q", format="$,.0f", title="Media value"),
                alt.Tooltip("sov_pct:Q", format=".1f", title="SOV %"),
            ],
        )
        .properties(height=300)
    )
    left.altair_chart(bar, use_container_width=True)

    # Media value by sport.
    by_sport = analytics.breakdown_by(fdf, "sport")
    top_sport = by_sport.iloc[0]["sport"]
    by_sport["is_top"] = by_sport["sport"] == top_sport
    sport_bar = (
        alt.Chart(by_sport, title=f"{top_sport} drives the most media value")
        .mark_bar()
        .encode(
            x=alt.X("media_value_usd:Q", title=None, axis=alt.Axis(format="$,.0s")),
            y=alt.Y("sport:N", sort="-x", title=None),
            color=alt.condition(alt.datum.is_top, alt.value(HIGHLIGHT), alt.value(GREY)),
            tooltip=[
                alt.Tooltip("sport:N"),
                alt.Tooltip("media_value_usd:Q", format="$,.0f", title="Media value"),
                alt.Tooltip("impressions:Q", format=",.0f"),
            ],
        )
        .properties(height=300)
    )
    right.altair_chart(sport_bar, use_container_width=True)

    sowhat(
        f"A small set of brands and sports carries most of the delivered value: "
        f"<strong>{k['top_brand']}</strong> alone holds "
        f"<strong>{k['top_brand_sov_pct']:.1f}%</strong> share of voice, and "
        f"<strong>{top_sport}</strong> is the single biggest value driver. "
        "Rights and sales conversations should start with these anchors."
    )


# ===========================================================================
# VIEW 2 — SHARE OF VOICE
# ===========================================================================
elif view == "Share of Voice":
    st.markdown("### Brand share of voice")
    metric_label = st.radio(
        "Measure share of voice by:",
        ["Media value", "Impressions", "Exposures"],
        horizontal=True,
    )
    metric_col = {
        "Media value": "media_value_usd",
        "Impressions": "impressions",
        "Exposures": "exposures",
    }[metric_label]

    sov = analytics.share_of_voice(fdf, metric=metric_col)
    leader = sov.iloc[0]
    sov["is_top"] = sov["brand"] == leader["brand"]

    chart = (
        alt.Chart(
            sov,
            title=f"{leader['brand']} owns {leader['sov_pct']:.0f}% of {metric_label.lower()}",
        )
        .mark_bar()
        .encode(
            x=alt.X("sov_pct:Q", title="Share of voice (%)"),
            y=alt.Y("brand:N", sort="-x", title=None),
            color=alt.condition(alt.datum.is_top, alt.value(HIGHLIGHT), alt.value(GREY)),
            tooltip=[
                alt.Tooltip("brand:N"),
                alt.Tooltip(f"{metric_col}:Q", format=",.0f", title=metric_label),
                alt.Tooltip("sov_pct:Q", format=".1f", title="SOV %"),
            ],
        )
        .properties(height=380)
    )
    labels = chart.mark_text(align="left", dx=3, color="#444").encode(
        text=alt.Text("sov_pct:Q", format=".1f")
    )
    st.altair_chart(chart + labels, use_container_width=True)

    # Concentration insight.
    top3 = sov.head(3)["sov_pct"].sum()
    sowhat(
        f"The top three brands capture <strong>{top3:.0f}%</strong> of all "
        f"{metric_label.lower()}. If a rights-holder wants to grow inventory value, "
        f"the opportunity is activating the long tail of brands below "
        f"<strong>{leader['brand']}</strong>, not over-serving the leader."
    )
    with st.expander("View full share-of-voice table"):
        show = sov[["brand", metric_col, "sov_pct"]].copy()
        show.columns = ["Brand", metric_label, "SOV %"]
        st.dataframe(show, use_container_width=True, hide_index=True)


# ===========================================================================
# VIEW 3 — SPORT & EVENT BREAKDOWN
# ===========================================================================
elif view == "Sport & Event Breakdown":
    st.markdown("### Exposure & media value by sport, league and event")
    dim_label = st.radio(
        "Break down by:", ["Sport", "League", "Event"], horizontal=True
    )
    dim = dim_label.lower()
    bd = analytics.breakdown_by(fdf, dim).head(12)
    top = bd.iloc[0]
    bd["is_top"] = bd[dim] == top[dim]

    chart = (
        alt.Chart(
            bd,
            title=f"{top[dim]} delivers the most media value ({fmt_usd(top['media_value_usd'])})",
        )
        .mark_bar()
        .encode(
            x=alt.X("media_value_usd:Q", title="Media value (USD)", axis=alt.Axis(format="$,.0s")),
            y=alt.Y(f"{dim}:N", sort="-x", title=None),
            color=alt.condition(alt.datum.is_top, alt.value(HIGHLIGHT), alt.value(GREY)),
            tooltip=[
                alt.Tooltip(f"{dim}:N", title=dim_label),
                alt.Tooltip("media_value_usd:Q", format="$,.0f", title="Media value"),
                alt.Tooltip("impressions:Q", format=",.0f"),
                alt.Tooltip("exposures:Q", format=",.0f"),
            ],
        )
        .properties(height=380)
    )
    st.altair_chart(chart, use_container_width=True)

    # Efficiency angle: value per exposure.
    bd_eff = bd.copy()
    bd_eff["value_per_exposure"] = bd_eff["media_value_usd"] / bd_eff["exposures"]
    best_eff = bd_eff.sort_values("value_per_exposure", ascending=False).iloc[0]
    sowhat(
        f"<strong>{top[dim]}</strong> produces the most total media value, but "
        f"<strong>{best_eff[dim]}</strong> is the most efficient placement at "
        f"<strong>{fmt_usd(best_eff['value_per_exposure'])}</strong> of value per "
        f"on-screen exposure — a better target when inventory, not reach, is the constraint."
    )
    with st.expander(f"View {dim_label.lower()} table"):
        st.dataframe(bd.drop(columns="is_top"), use_container_width=True, hide_index=True)


# ===========================================================================
# VIEW 4 — TREND OVER TIME
# ===========================================================================
elif view == "Trend Over Time":
    st.markdown("### Media value delivered per week")
    trend = analytics.trend_over_time(fdf, metric="media_value_usd", freq="W")
    mover = analytics.top_mover(trend, metric="media_value_usd")

    base = alt.Chart(trend).encode(
        x=alt.X("period:T", title=None, axis=alt.Axis(format="%b %d")),
        y=alt.Y("media_value_usd:Q", title="Media value (USD)", axis=alt.Axis(format="$,.0s")),
    )
    line = base.mark_line(color=GREY, strokeWidth=2)

    title = "Weekly media value trends upward into the season's back half"
    if mover["period"] is not None:
        # Highlight the single biggest mover week.
        hl = trend[trend["period"] == mover["period"]]
        point = (
            alt.Chart(hl)
            .mark_point(size=120, color=HIGHLIGHT, filled=True)
            .encode(x="period:T", y="media_value_usd:Q")
        )
        label = (
            alt.Chart(hl)
            .mark_text(dy=-14, color=HIGHLIGHT, fontWeight="bold")
            .encode(
                x="period:T",
                y="media_value_usd:Q",
                text=alt.value(f"{mover['pct_change']:+.0f}% WoW"),
            )
        )
        direction = "jump" if mover["delta"] > 0 else "drop"
        title = (
            f"Biggest weekly {direction}: {mover['pct_change']:+.0f}% "
            f"the week of {pd.to_datetime(mover['period']):%b %d}"
        )
        chart = (line + point + label).properties(
            height=380, title=title
        )
    else:
        chart = line.properties(height=380, title=title)

    st.altair_chart(chart, use_container_width=True)

    if mover["period"] is not None:
        sowhat(
            f"The largest single-week move is <strong>{mover['pct_change']:+.0f}%</strong> "
            f"the week of <strong>{pd.to_datetime(mover['period']):%b %d}</strong>, driven by "
            "high-prestige events (finals / playoffs) entering the schedule. Sponsor "
            "activation and premium ad inventory should be concentrated around these peak weeks."
        )


# ===========================================================================
# VIEW 5 — SPONSORSHIP ROI
# ===========================================================================
elif view == "Sponsorship ROI":
    st.markdown("### Delivered media value vs. sponsorship spend")
    table = analytics.roi_table(fdf, spend)

    chart = (
        alt.Chart(
            table,
            title="Brands above 1.0x over-deliver on their sponsorship spend",
        )
        .mark_bar()
        .encode(
            x=alt.X("roi:Q", title="ROI (media value ÷ spend)"),
            y=alt.Y("brand:N", sort="-x", title=None),
            color=alt.Color(
                "verdict:N",
                scale=alt.Scale(
                    domain=["Over-delivering", "Under-delivering"],
                    range=[POSITIVE, NEGATIVE],
                ),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("brand:N"),
                alt.Tooltip("roi:Q", format=".2f", title="ROI"),
                alt.Tooltip("media_value_usd:Q", format="$,.0f", title="Media value"),
                alt.Tooltip("spend_usd:Q", format="$,.0f", title="Spend"),
            ],
        )
        .properties(height=380)
    )
    rule = alt.Chart(pd.DataFrame({"x": [1.0]})).mark_rule(
        color="#333", strokeDash=[4, 4]
    ).encode(x="x:Q")
    st.altair_chart(chart + rule, use_container_width=True)

    sowhat(analytics.recommendation(fdf, spend))
    with st.expander("View ROI table"):
        show = table.copy()
        show.columns = ["Brand", "Media value", "Spend", "ROI", "Verdict"]
        st.dataframe(show, use_container_width=True, hide_index=True)

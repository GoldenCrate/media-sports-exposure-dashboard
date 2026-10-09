"""Framework-free analytics for brand-exposure data.

Pure pandas functions, no Streamlit imports, so everything here is unit
testable in isolation (see test_analytics.py). The Streamlit app (app.py)
calls these and only handles presentation.
"""

from __future__ import annotations

import pandas as pd

HOURS_PER_SECOND = 1.0 / 3600.0


# --- Headline KPIs --------------------------------------------------------

def kpi_summary(df: pd.DataFrame) -> dict:
    """Headline numbers for the KPI tiles.

    Returns total impressions, total media value, broadcast hours analyzed
    (sum of on-screen seconds converted to hours), the brand count, and the
    leading brand's share-of-voice by media value.
    """
    if df.empty:
        return {
            "total_impressions": 0,
            "total_media_value": 0.0,
            "broadcast_hours": 0.0,
            "brand_count": 0,
            "top_brand": None,
            "top_brand_sov_pct": 0.0,
        }

    total_impressions = int(df["impressions"].sum())
    total_media_value = float(df["media_value_usd"].sum())
    broadcast_hours = float(df["on_screen_sec"].sum()) * HOURS_PER_SECOND

    sov = share_of_voice(df)
    top = sov.iloc[0]

    return {
        "total_impressions": total_impressions,
        "total_media_value": total_media_value,
        "broadcast_hours": broadcast_hours,
        "brand_count": int(df["brand"].nunique()),
        "top_brand": str(top["brand"]),
        "top_brand_sov_pct": float(top["sov_pct"]),
    }


# --- Share of voice -------------------------------------------------------

def share_of_voice(df: pd.DataFrame, metric: str = "media_value_usd") -> pd.DataFrame:
    """Share of voice per brand on `metric`, descending.

    Adds a `sov_pct` column (percent of the total). Default metric is media
    value, the currency media buyers actually compare on.
    """
    if df.empty:
        return pd.DataFrame(columns=["brand", metric, "sov_pct"])

    grouped = (
        df.groupby("brand", as_index=False)[metric]
        .sum()
        .sort_values(metric, ascending=False)
        .reset_index(drop=True)
    )
    total = grouped[metric].sum()
    grouped["sov_pct"] = 0.0 if total == 0 else grouped[metric] / total * 100.0
    return grouped


# --- Dimensional breakdown ------------------------------------------------

def breakdown_by(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Aggregate exposures, impressions and media value by a dimension.

    `dimension` is a column such as "sport", "league" or "event".
    """
    if dimension not in df.columns:
        raise KeyError(f"Unknown dimension: {dimension!r}")
    if df.empty:
        return pd.DataFrame(
            columns=[dimension, "exposures", "impressions", "media_value_usd"]
        )

    grouped = (
        df.groupby(dimension, as_index=False)
        .agg(
            exposures=("exposures", "sum"),
            impressions=("impressions", "sum"),
            media_value_usd=("media_value_usd", "sum"),
        )
        .sort_values("media_value_usd", ascending=False)
        .reset_index(drop=True)
    )
    return grouped


# --- Trend over time ------------------------------------------------------

def trend_over_time(
    df: pd.DataFrame, metric: str = "media_value_usd", freq: str = "W"
) -> pd.DataFrame:
    """Total `metric` per period (default weekly).

    Returns a frame with columns ["period", metric] sorted chronologically.
    """
    if df.empty:
        return pd.DataFrame(columns=["period", metric])

    s = df.copy()
    s["week"] = pd.to_datetime(s["week"])
    grouped = (
        s.set_index("week")
        .resample(freq)[metric]
        .sum()
        .reset_index()
        .rename(columns={"week": "period"})
    )
    grouped = grouped[grouped[metric] > 0].reset_index(drop=True)
    return grouped


def top_mover(trend: pd.DataFrame, metric: str = "media_value_usd") -> dict:
    """Largest period-over-period change in a trend frame.

    Returns the period, absolute delta and percent delta of the single
    biggest mover. Empty / single-row frames yield a null result.
    """
    if trend.empty or len(trend) < 2:
        return {"period": None, "delta": 0.0, "pct_change": 0.0}

    t = trend.copy().reset_index(drop=True)
    t["delta"] = t[metric].diff()
    t["pct_change"] = t[metric].pct_change() * 100.0

    # Ignore the first NaN row, pick max absolute delta.
    movers = t.dropna(subset=["delta"])
    idx = movers["delta"].abs().idxmax()
    row = t.loc[idx]
    return {
        "period": row["period"],
        "value": float(row[metric]),
        "delta": float(row["delta"]),
        "pct_change": float(row["pct_change"]),
    }


# --- ROI / over- vs under-delivery ---------------------------------------

def roi_table(df: pd.DataFrame, spend: pd.DataFrame) -> pd.DataFrame:
    """Delivered media value vs. sponsorship spend, per brand.

    Returns per-brand media value, spend, ROI ratio (value / spend) and a
    `verdict` of "Over-delivering" (ROI >= 1) or "Under-delivering".
    Sorted best ROI first.
    """
    if df.empty or spend.empty:
        return pd.DataFrame(
            columns=["brand", "media_value_usd", "spend_usd", "roi", "verdict"]
        )

    value = df.groupby("brand", as_index=False)["media_value_usd"].sum()
    merged = value.merge(spend, on="brand", how="inner")
    merged["roi"] = merged["media_value_usd"] / merged["spend_usd"]
    merged["verdict"] = merged["roi"].apply(
        lambda r: "Over-delivering" if r >= 1.0 else "Under-delivering"
    )
    return merged.sort_values("roi", ascending=False).reset_index(drop=True)


def recommendation(df: pd.DataFrame, spend: pd.DataFrame) -> str:
    """One-line 'so what' naming the best over- and worst under-deliverer."""
    table = roi_table(df, spend)
    if table.empty:
        return "No data available for a recommendation."

    best = table.iloc[0]
    worst = table.iloc[-1]
    return (
        f"{best['brand']} delivers the strongest return "
        f"({best['roi']:.2f}x media value vs. spend) and is a candidate to "
        f"scale; {worst['brand']} under-delivers ({worst['roi']:.2f}x) and "
        f"its placement mix should be renegotiated or reallocated."
    )

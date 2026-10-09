"""Unit tests for analytics.py (pure functions, no Streamlit)."""

from __future__ import annotations

import pandas as pd
import pytest

import analytics
from data_gen import brand_spend, generate_data


@pytest.fixture(scope="module")
def df():
    return generate_data()


@pytest.fixture(scope="module")
def spend():
    return brand_spend()


@pytest.fixture
def tiny():
    """Small hand-built frame with known answers."""
    return pd.DataFrame(
        {
            "brand": ["A", "A", "B", "C"],
            "sport": ["Soccer", "Tennis", "Soccer", "Tennis"],
            "league": ["EPL", "ATP", "EPL", "ATP"],
            "event": ["e1", "e2", "e1", "e2"],
            "week": pd.to_datetime(["2025-01-06", "2025-01-13", "2025-01-06", "2025-01-13"]),
            "exposures": [10, 20, 30, 40],
            "on_screen_sec": [3600.0, 1800.0, 900.0, 900.0],
            "impressions": [100, 200, 300, 400],
            "media_value_usd": [50.0, 150.0, 300.0, 500.0],
        }
    )


# --- data generation ------------------------------------------------------

def test_generate_data_is_deterministic():
    a = generate_data()
    b = generate_data()
    pd.testing.assert_frame_equal(a, b)


def test_generate_data_schema_and_nonempty(df):
    expected = {
        "brand", "sport", "league", "event", "week",
        "exposures", "impressions", "on_screen_sec", "media_value_usd",
    }
    assert expected.issubset(set(df.columns))
    assert len(df) > 0
    assert (df["exposures"] > 0).all()
    assert (df["media_value_usd"] >= 0).all()


# --- KPIs -----------------------------------------------------------------

def test_kpi_summary_tiny(tiny):
    k = kpi = analytics.kpi_summary(tiny)
    assert k["total_impressions"] == 1000
    assert k["total_media_value"] == pytest.approx(1000.0)
    # 3600+1800+900+900 = 7200 sec = 2 hours
    assert k["broadcast_hours"] == pytest.approx(2.0)
    assert k["brand_count"] == 3
    # C has the most media value (500) -> top brand
    assert k["top_brand"] == "C"
    assert k["top_brand_sov_pct"] == pytest.approx(50.0)


def test_kpi_summary_empty():
    k = analytics.kpi_summary(pd.DataFrame())
    assert k["total_impressions"] == 0
    assert k["top_brand"] is None


# --- share of voice -------------------------------------------------------

def test_share_of_voice_sums_to_100(df):
    sov = analytics.share_of_voice(df)
    assert sov["sov_pct"].sum() == pytest.approx(100.0, abs=1e-6)
    # sorted descending
    assert sov["media_value_usd"].is_monotonic_decreasing


def test_share_of_voice_tiny(tiny):
    sov = analytics.share_of_voice(tiny)
    a_row = sov[sov["brand"] == "A"].iloc[0]
    assert a_row["media_value_usd"] == pytest.approx(200.0)
    assert a_row["sov_pct"] == pytest.approx(20.0)


# --- breakdown ------------------------------------------------------------

def test_breakdown_by_sport(tiny):
    b = analytics.breakdown_by(tiny, "sport")
    soccer = b[b["sport"] == "Soccer"].iloc[0]
    assert soccer["exposures"] == 40  # 10 + 30
    assert soccer["media_value_usd"] == pytest.approx(350.0)


def test_breakdown_by_unknown_dimension_raises(tiny):
    with pytest.raises(KeyError):
        analytics.breakdown_by(tiny, "nope")


# --- trend ----------------------------------------------------------------

def test_trend_over_time_tiny(tiny):
    t = analytics.trend_over_time(tiny)
    assert len(t) == 2
    # week 1: A(50)+B(300)=350 ; week 2: A(150)+C(500)=650
    assert t.iloc[0]["media_value_usd"] == pytest.approx(350.0)
    assert t.iloc[1]["media_value_usd"] == pytest.approx(650.0)


def test_top_mover_tiny(tiny):
    t = analytics.trend_over_time(tiny)
    mover = analytics.top_mover(t)
    assert mover["delta"] == pytest.approx(300.0)
    assert mover["pct_change"] == pytest.approx(300.0 / 350.0 * 100.0)


def test_top_mover_single_row():
    t = pd.DataFrame({"period": [pd.Timestamp("2025-01-06")], "media_value_usd": [10.0]})
    assert analytics.top_mover(t)["period"] is None


# --- ROI ------------------------------------------------------------------

def test_roi_table_and_recommendation(df, spend):
    table = analytics.roi_table(df, spend)
    assert set(["brand", "media_value_usd", "spend_usd", "roi", "verdict"]).issubset(table.columns)
    # sorted best ROI first
    assert table["roi"].is_monotonic_decreasing
    assert table["verdict"].isin(["Over-delivering", "Under-delivering"]).all()

    rec = analytics.recommendation(df, spend)
    assert table.iloc[0]["brand"] in rec
    assert table.iloc[-1]["brand"] in rec


def test_roi_table_values():
    df = pd.DataFrame({"brand": ["A", "B"], "media_value_usd": [200.0, 50.0]})
    spend = pd.DataFrame({"brand": ["A", "B"], "spend_usd": [100.0, 100.0]})
    table = analytics.roi_table(df, spend)
    a = table[table["brand"] == "A"].iloc[0]
    assert a["roi"] == pytest.approx(2.0)
    assert a["verdict"] == "Over-delivering"
    b = table[table["brand"] == "B"].iloc[0]
    assert b["verdict"] == "Under-delivering"

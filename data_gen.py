"""Synthetic sponsorship / broadcast brand-exposure data generator.

ALL DATA PRODUCED HERE IS SYNTHETIC. It is generated with a fixed random
seed so results are fully reproducible. No real broadcast feeds, viewership
panels, or sponsorship contracts are used. Brand names are real companies
used only as realistic-looking labels; the numbers are invented.

Data model
----------
Each row is one brand's aggregated on-screen exposure for a single
(brand x sport x league x event x week) combination:

    brand           sponsor name
    sport           e.g. Basketball, Soccer, Motorsport
    league          e.g. NBA, EPL, Formula 1
    event           a specific broadcast (e.g. "NBA Finals Game 3")
    week            Monday-anchored ISO week date
    exposures       count of discrete on-screen logo appearances
    on_screen_sec   total seconds the brand was visible
    impressions     estimated viewer-impressions delivered
    media_value_usd estimated equivalent media value in USD

A companion `brand_spend()` table gives each brand's season sponsorship
spend, so analytics can compute delivered media value vs. spend (ROI).
"""

from __future__ import annotations

import datetime as _dt

import numpy as np
import pandas as pd

SEED = 42

# --- Reference dimensions -------------------------------------------------

BRANDS = [
    "Nike", "Pepsi", "Toyota", "Rolex", "Emirates",
    "Heineken", "Samsung", "Visa", "Red Bull", "Adidas",
]

# sport -> list of (league, [events])
SPORTS = {
    "Basketball": ("NBA", ["NBA Regular Season", "NBA Playoffs", "NBA Finals"]),
    "Soccer": ("EPL", ["EPL Matchday", "FA Cup", "Champions League Night"]),
    "American Football": ("NFL", ["NFL Sunday", "Monday Night Football", "Playoffs"]),
    "Motorsport": ("Formula 1", ["Grand Prix Weekend", "Sprint Race", "Qualifying"]),
    "Tennis": ("ATP", ["ATP Masters", "Grand Slam", "Tour Final"]),
}

# Per-brand affinity: how strongly a brand shows up in a given sport (0-1).
# Drives realistic, uneven share-of-voice instead of uniform noise.
BRAND_SPORT_AFFINITY = {
    "Nike": {"Basketball": 1.0, "Soccer": 0.9, "Tennis": 0.8, "American Football": 0.5, "Motorsport": 0.2},
    "Pepsi": {"American Football": 1.0, "Basketball": 0.7, "Soccer": 0.6, "Tennis": 0.3, "Motorsport": 0.3},
    "Toyota": {"Motorsport": 0.9, "American Football": 0.8, "Basketball": 0.4, "Soccer": 0.4, "Tennis": 0.3},
    "Rolex": {"Tennis": 1.0, "Motorsport": 0.8, "Soccer": 0.3, "Basketball": 0.2, "American Football": 0.2},
    "Emirates": {"Soccer": 1.0, "Tennis": 0.6, "Motorsport": 0.4, "Basketball": 0.3, "American Football": 0.2},
    "Heineken": {"Soccer": 0.9, "Motorsport": 0.9, "Basketball": 0.3, "Tennis": 0.3, "American Football": 0.4},
    "Samsung": {"Soccer": 0.7, "Basketball": 0.7, "American Football": 0.6, "Tennis": 0.5, "Motorsport": 0.5},
    "Visa": {"American Football": 0.8, "Soccer": 0.7, "Basketball": 0.6, "Tennis": 0.6, "Motorsport": 0.4},
    "Red Bull": {"Motorsport": 1.0, "Soccer": 0.6, "Basketball": 0.3, "Tennis": 0.2, "American Football": 0.3},
    "Adidas": {"Soccer": 1.0, "Basketball": 0.8, "Tennis": 0.6, "American Football": 0.4, "Motorsport": 0.3},
}

# Typical live audience (millions) per league, scales impressions / media value.
LEAGUE_AUDIENCE_M = {
    "NBA": 3.2,
    "EPL": 2.4,
    "NFL": 16.5,
    "Formula 1": 1.8,
    "ATP": 1.1,
}

N_WEEKS = 20
SEASON_START = _dt.date(2025, 1, 6)  # a Monday

# CPM-style rate: USD of media value per 1,000 impression-seconds.
VALUE_RATE = 0.045


def _week_dates(n_weeks: int = N_WEEKS, start: _dt.date = SEASON_START):
    return [start + _dt.timedelta(weeks=i) for i in range(n_weeks)]


def generate_data(seed: int = SEED, n_weeks: int = N_WEEKS) -> pd.DataFrame:
    """Return a reproducible synthetic brand-exposure DataFrame."""
    rng = np.random.default_rng(seed)
    weeks = _week_dates(n_weeks)

    rows = []
    for w_idx, week in enumerate(weeks):
        # Seasonal ramp: exposure volume builds toward the back half of the
        # season (playoffs / finals), giving the trend view something to say.
        season_factor = 0.8 + 0.5 * (w_idx / max(n_weeks - 1, 1))

        for sport, (league, events) in SPORTS.items():
            audience = LEAGUE_AUDIENCE_M[league]
            # Not every event airs every week.
            for event in events:
                if rng.random() < 0.35:
                    continue
                event_prestige = 1.0
                if any(k in event for k in ("Finals", "Grand Slam", "Playoffs", "Champions")):
                    event_prestige = 1.6

                for brand in BRANDS:
                    affinity = BRAND_SPORT_AFFINITY[brand][sport]
                    if affinity <= 0:
                        continue
                    # Brand only appears when affinity clears a random bar.
                    if rng.random() > affinity:
                        continue

                    base = affinity * season_factor * event_prestige
                    exposures = int(rng.poisson(max(base * 18, 1)))
                    if exposures == 0:
                        continue
                    # Avg seconds per exposure, lognormal-ish.
                    sec_per = max(rng.normal(3.2, 0.8), 0.5)
                    on_screen_sec = round(exposures * sec_per, 1)

                    # Impressions = viewers reached, scaled by audience + prestige.
                    impressions = int(
                        on_screen_sec
                        * audience
                        * 1_000_000
                        * event_prestige
                        * rng.uniform(0.9, 1.1)
                        / 30.0  # normalize per ~30s unit
                    )
                    media_value = round(impressions / 1000.0 * VALUE_RATE, 2)

                    rows.append(
                        {
                            "brand": brand,
                            "sport": sport,
                            "league": league,
                            "event": event,
                            "week": week.isoformat(),
                            "exposures": exposures,
                            "on_screen_sec": on_screen_sec,
                            "impressions": impressions,
                            "media_value_usd": media_value,
                        }
                    )

    df = pd.DataFrame(rows)
    df["week"] = pd.to_datetime(df["week"])
    return df.sort_values(["week", "sport", "brand"]).reset_index(drop=True)


def brand_spend(seed: int = SEED) -> pd.DataFrame:
    """Synthetic season sponsorship spend (USD) per brand.

    Used to compare delivered media value against spend (ROI). Deliberately
    set so a couple of brands clearly over-deliver and a couple under-deliver.
    """
    rng = np.random.default_rng(seed + 1)
    # Hand-tuned base spend (USD millions) to create a clear ROI story.
    base_spend_m = {
        "Nike": 9.0, "Pepsi": 11.0, "Toyota": 7.5, "Rolex": 4.0, "Emirates": 6.5,
        "Heineken": 5.0, "Samsung": 8.0, "Visa": 10.0, "Red Bull": 3.5, "Adidas": 8.5,
    }
    rows = []
    for brand, spend_m in base_spend_m.items():
        jitter = rng.uniform(0.95, 1.05)
        rows.append({"brand": brand, "spend_usd": round(spend_m * 1_000_000 * jitter, 0)})
    return pd.DataFrame(rows)


def main() -> None:
    import os

    df = generate_data()
    spend = brand_spend()
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/exposures.csv", index=False)
    spend.to_csv("data/brand_spend.csv", index=False)
    print(f"Wrote data/exposures.csv  ({len(df):,} rows)")
    print(f"Wrote data/brand_spend.csv ({len(spend):,} rows)")
    print(f"Total impressions : {df['impressions'].sum():,}")
    print(f"Total media value : ${df['media_value_usd'].sum():,.0f}")


if __name__ == "__main__":
    main()

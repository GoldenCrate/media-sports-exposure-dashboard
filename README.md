# Media & Sports Brand-Exposure Analytics

An interactive dashboard that measures how much **on-screen exposure**,
**audience impressions** and **equivalent media value** each sponsor brand
earns across sports, leagues, events and time — the core analytical question
behind sponsorship valuation and brand-exposure measurement.

Built as a portfolio project by **Leo Chan** — [github.com/GoldenCrate](https://github.com/GoldenCrate).

> ⚠️ **All data in this project is SYNTHETIC.** It is generated locally from a
> fixed random seed (`data_gen.py`) and contains **no real broadcast feeds,
> viewership panels, or sponsorship contracts**. Brand names are real companies
> used only as realistic-looking labels; every number is invented. The project
> demonstrates analysis and communication, not proprietary data.

---

## What it does

The app answers the questions a media & sports analyst is asked every day:

1. **Overview / KPI tiles** — total brand impressions, equivalent media value,
   broadcast hours analyzed, and the leading brand's share of voice.
2. **Share of Voice** — how exposure is split across sponsor brands, by media
   value, impressions or raw exposures, with a top-three concentration read.
3. **Sport & Event Breakdown** — exposure and media value by sport, league or
   event, plus a value-per-exposure efficiency angle.
4. **Trend Over Time** — weekly media value with the single biggest
   week-over-week mover highlighted.
5. **Sponsorship ROI** — delivered media value vs. sponsorship spend per brand,
   flagging who over- and under-delivers.

Every view ends with a **"So what →" recommendation** — the decision the
numbers support, not just the chart.

## Design

Charts follow Cole Nussbaumer Knaflic's *Storytelling with Data*:

- **Takeaway titles** state the insight (e.g. *"Nike leads share of voice"*),
  not generic labels like *"Media value by brand"*.
- **Decluttered** axes and no chart junk.
- **Direct labels** instead of forcing the reader to a legend.
- **Restrained color**: grey for context, a single accent for the point being
  made (green/red only where over/under-delivery is the message).

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | Streamlit multi-view dashboard (presentation only) |
| `analytics.py` | Framework-free analytics (pure pandas, unit-tested) |
| `data_gen.py` | Synthetic data generator (fixed seed) |
| `test_analytics.py` | pytest unit tests for the analytics layer |
| `requirements.txt` | Dependencies |

The compute lives in `analytics.py` with **no Streamlit imports**, so it is
tested in isolation by `test_analytics.py`.

## Run it locally

```bash
# 1. install
pip install -r requirements.txt

# 2. (optional) generate the synthetic CSVs to inspect them
python data_gen.py

# 3. run the tests
pytest -q

# 4. launch the dashboard
streamlit run app.py
```

Then open the URL Streamlit prints (default http://localhost:8501).
The app generates its data in-memory on startup, so step 2 is optional.

## Data model

Each row of the generated dataset is one brand's aggregated on-screen exposure
for a single *(brand × sport × league × event × week)* combination:

| column | meaning |
|--------|---------|
| `brand` | sponsor name |
| `sport`, `league`, `event` | where the exposure occurred |
| `week` | Monday-anchored week |
| `exposures` | count of discrete on-screen logo appearances |
| `on_screen_sec` | total seconds the brand was visible |
| `impressions` | estimated viewer-impressions delivered |
| `media_value_usd` | estimated equivalent media value (USD) |

A companion spend table assigns each brand a season sponsorship spend, enabling
the ROI (media value ÷ spend) view.

---

*Author: Leo Chan — [github.com/GoldenCrate](https://github.com/GoldenCrate). Synthetic-data portfolio demo.*

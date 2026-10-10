# Pit Stop Risk Engine 🏎

A Formula 1 analytics tool that answers the question every Team Principal asks on race day:

> **"Is our pit crew costing us positions — and when is the risk highest?"**

Built on the [OpenF1 API](https://openf1.org) — free, no authentication required.

---

## What it does

For every pit stop across a full F1 season, the engine:

1. **Measures the true gap** to the car behind at pit entry (by tracking that car's position and interval data in real time)
2. **Scores the pit window** as SAFE / MARGINAL / DANGEROUS based on whether the gap was large enough to cover the stop
3. **Surfaces team radio clips** for dangerous stops — hear what the driver said after a risky call
4. **Joins tire compound data** — see whether slow stops correlate with specific compounds

---

## Dashboard

Three tabs in a Streamlit app:

| Tab | What you see |
|---|---|
| **Team Comparison** | Median stop duration, distribution box plots, compound usage by team |
| **Race Timeline** | Per-race scatter — lap vs. duration, colored by risk or compound, audio player for dangerous stops |
| **Costliest Stops** | Top 10 positions lost, with compound and risk score, radio clips where available |

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Step 1 — fetch data (dry-run: 2 sessions only)
python fetcher.py --year 2024 --dry-run

# Full season fetch (~15 min, rate-limited to 30 req/min)
python fetcher.py --year 2024
python fetcher.py --year 2023

# Step 2 — build analysis and risk scores
python analyzer.py 2024
python risk.py 2024

# Step 3 — launch dashboard
streamlit run app.py
```

---

## How the risk score works

For each pit stop, the engine finds the car directly behind the pitting driver and reads its **interval** (gap to the car ahead) at the moment of pit entry. That value is compared against:

```
threshold = pit_duration + pit_lane_traversal_time (~20s)
```

| Score | Condition |
|---|---|
| SAFE | gap > threshold + 5s |
| MARGINAL | 0 < gap ≤ threshold + 5s |
| DANGEROUS | gap ≤ 0 (emerged behind the car) |

86% of stops use the **exact** gap from the car behind. The remaining 14% fall back to the pitting driver's own interval (e.g., race leader with no car ahead, or last-place driver).

---

## Key findings (2023–2024)

- **Red Bull** consistently fastest: 22.9s median in 2024, 23.2s in 2023
- **Kick Sauber** highest slow-stop rate: 21.7% of stops exceeded 30s in 2024
- **7 genuinely dangerous** pit windows in 2024 (down from 67 with the naive approximation)
- **Medium compound** dominates both seasons — most undercuts run on mediums

---

## Project structure

```
fetcher.py      Pull data from OpenF1, cache per-session JSON in data/cache/
analyzer.py     Team stop stats + position delta per stop
risk.py         Gap-to-car-behind scoring, compound join, radio matching
app.py          Streamlit dashboard
data/           Auto-generated, gitignored
```

---

## Data source

[OpenF1](https://openf1.org) — open-source F1 data API. Historical data (2023+) is free with no API key. Live data during sessions requires a sponsor tier.

---

## Related work

This project extends my earlier [F1 Advanced Analytics](https://github.com/reginaldooo/F1-advanced-analytics) work (K-Means clustering, NLP DNF classification on 589K+ lap records) with live API data and a real-time strategy lens.

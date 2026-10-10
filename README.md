# Pit Stop Risk Engine 🏎

[![GitHub](https://img.shields.io/badge/GitHub-reginaldooo-181717?logo=github&style=flat-square)](https://github.com/reginaldooo)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-farrel--reginaldo-0A66C2?logo=linkedin&style=flat-square)](https://linkedin.com/in/farrel-reginaldo)
[![OpenF1](https://img.shields.io/badge/Data-OpenF1-E10600?style=flat-square)](https://openf1.org)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&style=flat-square)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&style=flat-square)](https://streamlit.io)

> **"Is our pit crew costing us positions — and when is the risk highest?"**

A Formula 1 analytics tool that simulates a Team Principal's view of pit crew performance. For every pit stop across a full F1 season, it measures the gap the crew was racing against, scores the timing window, and visualises the results in an interactive dashboard.

Built entirely on the [OpenF1 API](https://openf1.org) — free and open, no authentication required.

---

## Dashboard

Four tabs in a Streamlit app. The **sidebar** controls the season (2023 / 2024 / 2025) and team filter — both apply across all tabs simultaneously.

---

### Tab 1 — Team Comparison

Answers: *which team is fastest, and which is most consistent?*

| Section | What it shows |
|---|---|
| **Median Stop Duration bar chart** | One bar per team, sorted fastest to slowest. Y-axis starts at 20s to make the 1–2s competitive gap visible. Each bar is labeled with the exact median value. Team colours from OpenF1. |
| **Stop Duration Distribution box plot** | Box-and-whisker per team showing spread and outliers. Stops over 120s (red flag / drive-through) are excluded from this view. |
| **Tyre Compound Usage stacked bar** | How many stops each team made per compound — shows whether a team runs more softs (aggressive strategy) or mediums/hards. |
| **Stats Table** | Team · Stops · Median (s) · Mean (s) · Std Dev · Slow Stop Rate (%). Every column header has a hover tooltip explaining its meaning. |

---

### Tab 2 — Race Timeline

Answers: *in this specific race, which stops were risky and when did they happen?*

| Section | What it shows |
|---|---|
| **Race selector** | Dropdown to select any race from the loaded season. |
| **Color by toggle** | Switch between Risk view (green/yellow/red dots) and Compound view (tyre colour dots with risk-coloured border). |
| **Scatter plot** | Each dot = one pit stop. X axis = lap number, Y axis = stop duration in seconds. Hover for driver, team, compound, tyre age, gap at entry, gap source, and risk score. |
| **Weather annotations** | If rainfall was detected during the race, a blue label appears on the chart. Average track temperature shown in the top-right corner. |
| **Metrics row** | Total stops · Dangerous count · Marginal count for the selected race. |
| **Radio clip cards** | Dangerous stops with a radio recording display as cards (3 per row): driver headshot · name · team · lap · compound · gap vs lane time · net gap verdict · audio player. Label notes the clip may not be about the stop. |
| **Detail table** | Driver · Team · Lap · Stop (s) · Compound · Tyre Age · Gap Behind (s) · Gap Source · Risk. All headers have hover tooltips. |

---

### Tab 3 — Costliest Stops

Answers: *which stops actually cost positions, and who was involved?*

| Section | What it shows |
|---|---|
| **Metric cards** | Most Dangerous Team (highest dangerous stop count) · Safe Stop Rate (% of stops with net > +5s) · Median Stop Duration across all stops. |
| **Top 10 positions lost — card grid** | 3-per-row cards: driver headshot · name · team · circuit · lap · stop duration · compound · positions lost · risk score. |
| **Top 10 worst stops table** | Race · Driver · Team · Lap · Stop (s) · Pos Before · Pos After · Δ Positions · Compound · Risk. All headers have hover tooltips. |
| **Radio clip cards** | Same 3-per-row card layout as Tab 2, with positions lost added to the story. Only appears if matching radio clips exist. |
| **Top 10 positions gained table** | Counterpart to the worst stops — undercuts and well-timed stops that gained places. |

---

### Tab 4 — How to Read This

Full in-app guide covering:

- The core question and what the dashboard is actually measuring
- The risk formula (`net = gap − (stop + 20s)`) in a code block
- SAFE / MARGINAL / DANGEROUS / UNKNOWN definitions with exact thresholds
- Why ~95% of stops score DANGEROUS (the strategic context)
- How gap is measured — Measured (from car behind) vs. Estimated (driver's own interval)
- Per-tab explanations of every chart and column
- Key reference numbers (typical pit lane time, slow-stop threshold, 120s exclusion rule)

---

## Data — What We Pull and Why

All data comes from the [OpenF1 API](https://openf1.org). Eight endpoints are used:

| Endpoint | Data pulled | Why we need it |
|---|---|---|
| `/sessions` | Race session keys per year | Entry point — used to iterate over every race in the season |
| `/pit` | Stop duration, lap number, driver number | The core measurement: how long each crew stop actually took |
| `/intervals` | Gap to car ahead, updated every ~4 seconds | Used to read the gap the pitting driver is racing against at pit entry |
| `/position` | Race position timeline per driver | Used to find the car at position+1 (directly behind the pitting driver) |
| `/stints` | Tyre compound, age at stint start, lap range | Identifies what compound was fitted and how many laps were on the outgoing set |
| `/team_radio` | Audio clips with UTC timestamps | Surfaces driver and engineer comms recorded near dangerous pit windows |
| `/drivers` | Team name, team colour (hex), headshot URL | Team attribution, official F1 brand colours, driver photos in the dashboard |
| `/weather` | Rainfall flag, track temperature, air temperature | Race condition context overlaid on the timeline chart |

---

## How the Risk Score Works

At the moment a car enters the pit lane, the engine finds the **car directly behind** in the race order and reads its interval — the gap from that car to the pitting driver. That gap is compared against the total time the pitting car will lose:

```
net = gap_to_car_behind − (pit_duration + 20s pit lane traverse)
```

The 20s pit lane traversal is a fixed estimate. It varies by circuit (Monaco is longer, Bahrain shorter) but is consistent enough for season-wide comparison.

| Score | Condition | Meaning |
|---|---|---|
| **SAFE** | net > +5s | Emerged ahead with a comfortable margin |
| **MARGINAL** | 0 < net ≤ 5s | Emerged ahead, but razor-thin — any hesitation costs position |
| **DANGEROUS** | net ≤ 0 | Gap did not cover the pit lane time — emerged behind on paper |
| **UNKNOWN** | no gap data | Race leader (gap = 0), or interval data unavailable |

**Gap measurement method:**
- **Measured** (~86% of stops): gap read directly from the car at position+1 at pit entry
- **Estimated** (~14%): pitting driver's own interval used instead — happens at the back of the field or when position data is missing
- Race leaders' own interval is 0 (they have no car ahead to measure against), so their stops are scored UNKNOWN rather than DANGEROUS

**Key insight:** In 2023–2025, approximately 95% of all pit stops score DANGEROUS by this formula. That is not a flaw — it reflects how F1 strategy actually works. Most pit stops are made when the gap is not sufficient to cover the pit lane time on its own. Teams take that risk because they expect the car behind to also pit. This dashboard scores each stop in isolation: if the rival stays out, does the stop work?

---

## Backend Architecture

```
fetcher.py
  OpenF1 data layer. Fetches all 8 endpoints per session, stores per-session
  JSON in data/cache/ for resumable runs. Exponential backoff on 429 rate limits
  (10s → 20s → 40s → 80s → 120s, max 5 retries). Re-runs skip already-cached
  sessions — safe to interrupt and resume.

analyzer.py
  Computes team stop duration stats (median, mean, std dev, p95, slow-stop rate)
  and position delta per stop (position 1 lap before vs. 3 laps after pitting).
  Outputs stop_outcomes_{year}.csv.

risk.py
  Core scoring engine. For each stop:
    1. Finds the car at position+1 using the position timeline
    2. Reads that car's interval at pit entry time (Measured method)
    3. Falls back to pitting driver's own interval if position data is missing
    4. Computes net gap and assigns SAFE / MARGINAL / DANGEROUS / UNKNOWN
    5. Joins tyre compound and age from stints data
    6. Finds the nearest team radio clip within 2 minutes for dangerous stops
  Outputs risk_scores_{year}.csv.

app.py
  Streamlit dashboard. 4 tabs with Plotly charts. Features:
    - Team hex colours from OpenF1 applied to all charts
    - Driver headshots from OpenF1 in Costliest Stops
    - Weather annotations (rainfall, track temp) on Race Timeline
    - Column tooltips on every table via st.column_config
    - Story cards on radio clips: net gap, emergence direction, positions lost
    - Sidebar year selector (2023 / 2024 / 2025) and team filter
    - Box plot capped at 120s (red flag / drive-through stops excluded from view)
```

---

## Key Findings (2023–2025)

### 2025 (30 races, 867 stops)
- **Ferrari fastest**: 22.9s median — edged Red Bull by 0.1s for the first time
- **Haas highest slow-stop rate**: 14.1% of stops exceeded 30s
- 9 SAFE windows, 4 MARGINAL, 842 DANGEROUS, 12 UNKNOWN
- Measured gap coverage: 85.0%

### 2024 (30 races, 865 stops)
- **Red Bull fastest**: 22.9s median
- **Kick Sauber highest slow-stop rate**: 21.7%
- 32 SAFE windows, 5 MARGINAL, 818 DANGEROUS, 10 UNKNOWN
- Medium compound: 48.6% of all stops
- Measured gap coverage: 86.0%

### 2023 (29 races, 717 stops)
- **Red Bull fastest**: 23.2s median
- **Williams highest slow-stop rate**: 20.3%
- 15 SAFE windows, 2 MARGINAL, 698 DANGEROUS, 2 UNKNOWN
- Medium compound: 43.0% of all stops
- Measured gap coverage: 87.6%

### Cross-season
- Medium compound dominates all three seasons (~43–49% of stops) — most undercut strategies run on mediums
- SAFE stops are rare in all seasons — an F1 pit stop with a genuinely comfortable gap behind is the exception, not the rule
- Red Bull dominated crew speed in 2023–2024; Ferrari matched them in 2025

---

## Setup & Operation

**Requirements:** Python 3.9+

```bash
# 1. Clone and install dependencies
git clone https://github.com/reginaldooo/pit-stop-risk-engine
cd pit-stop-risk-engine
pip install -r requirements.txt

# 2. Fetch a season
#    First run takes ~15 minutes per season (rate limited to 30 req/min)
#    Subsequent runs are instant — data is cached per session
python3 fetcher.py --year 2025
python3 fetcher.py --year 2024   # optional
python3 fetcher.py --year 2023   # optional

# Dry-run: fetch 2 sessions only, for quick testing
python3 fetcher.py --year 2025 --dry-run

# 3. Build analysis and risk scores
python3 analyzer.py 2025
python3 risk.py 2025

# 4. Launch the dashboard
python3 -m streamlit run app.py
# Open http://localhost:8501
```

**Notes:**
- `data/` is gitignored — regenerate locally after cloning
- `data/cache/` stores per-session JSON — safe to interrupt `fetcher.py` and re-run; already-fetched sessions are skipped
- All three seasons (2023, 2024, 2025) can be loaded at once — switch between them in the sidebar

---

## Project Structure

```
pit-stop-risk-engine/
├── fetcher.py        Data layer — OpenF1 fetch, per-session cache, retry logic
├── analyzer.py       Stop duration stats + position delta per stop
├── risk.py           Risk scoring, tyre age join, radio matching
├── app.py            Streamlit dashboard (4 tabs)
├── requirements.txt
└── data/             Auto-generated, gitignored
    └── cache/        Per-session JSON cache (resume-safe)
```

---

## Shoutout — OpenF1

This project runs entirely on [OpenF1](https://openf1.org) — a free, open-source Formula 1 data API built and maintained by independent contributors. Historical race data (2023 onwards) is available with no API key and no rate-limit registration. Without OpenF1, a project like this would require a paid data subscription that puts it out of reach for independent developers.

If you use this project, go give OpenF1 a star: [github.com/br-g/openf1](https://github.com/br-g/openf1).

---

## License

MIT — free to use, modify, and build on. Attribution appreciated.

---

## Related Work

This project extends my earlier **F1 Advanced Analytics** work — K-Means driver clustering across 7 decades of F1, NLP-based DNF classification on 589K+ lap records, and the Safe Zone Effect analysis. That project used historical Kaggle datasets; this one moves into live API data and real-time strategy simulation.

[github.com/reginaldooo/F1-advanced-analytics](https://github.com/reginaldooo/F1-advanced-analytics)

---

## Author

**Reginaldo Ahnaf**
AI Engineer · Data Analyst · F1 Analytics

[![LinkedIn](https://img.shields.io/badge/LinkedIn-farrel--reginaldo-0A66C2?logo=linkedin&style=flat-square)](https://linkedin.com/in/farrel-reginaldo)
[![GitHub](https://img.shields.io/badge/GitHub-reginaldooo-181717?logo=github&style=flat-square)](https://github.com/reginaldooo)

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
| **Color by toggle** | Switch between Risk view (green/yellow/orange/red dots) and Compound view (tyre colour dots with risk-coloured border). |
| **Scatter plot** | Each dot = one pit stop. X axis = lap number, Y axis = stop duration in seconds. Hover for driver, team, compound, tyre age, gap at entry, gap source, and risk score. |
| **Weather annotations** | If rainfall was detected during the race, a blue label appears on the chart. Average track temperature shown in the top-right corner. |
| **Metrics row** | Total stops · Critical count · Risky count · Marginal count for the selected race. |
| **Radio clip cards** | RISKY/CRITICAL stops with a radio recording display as cards (3 per row): driver headshot · name · team · lap · compound · gap vs stop duration · net gap verdict · audio player. Label notes the clip may not be about the stop. |
| **Detail table** | Driver · Team · Lap · Stop (s) · Compound · Tyre Age · Gap Behind (s) · Gap Source · Risk. All headers have hover tooltips. |

---

### Tab 3 — Costliest Stops

Answers: *which stops actually cost positions, who was involved, and did the risk pay off?*

| Section | What it shows |
|---|---|
| **Metric cards** | Most Dangerous Team (highest RISKY + CRITICAL stop count) · Safe Stop Rate (% of stops with net > +5s) · Median Stop Duration across all stops. |
| **Top 10 — Most Positions Lost (leaderboard)** | Ranked by **Cost Score**. One row per stop: rank badge (🥇🥈🥉) · headshot · Driver + risk dot · Race · Stop duration + compound · Pos Before · Δ Immediate · Δ Settled · Cost Score. Column guide expander above the table explains every column. |
| **Cost Score** | `Δ Settled − expected_Δ_Settled[risk_level]`. The season average Δ Settled for each risk level (SAFE / MARGINAL / DANGEROUS) is the baseline. A DANGEROUS stop normally loses ~1–2 places and recovers — a Cost Score of +10 means 10 extra places were lost beyond that baseline. These are the stops the strategy team truly got wrong, not just the ones that followed the expected pit lane pattern. |
| **Radio clip cards** | 3-per-row cards for dangerous stops with a recorded radio clip: headshot · driver · team · lap · compound · net gap verdict · positions lost (settled) · audio player. Label notes the clip may not be about the stop. |
| **Top 10 — Most Positions Gained** | Best undercuts and overcutts of the season. Columns: Race · Driver · Team · Lap · Stop (s) · Pos Before · Pos After (pit exit) · Δ Immediate · Pos Settled (~3 laps) · Δ Settled · **Final Pos**. Final Pos shows the driver's position at the end of the race — answers whether the gain held to the flag. |

---

### Tab 4 — How to Read This

Full in-app guide covering:

- The core question and what the dashboard is actually measuring
- The risk formula (`net = gap − (stop + 20s)`) in a code block
- SAFE / MARGINAL / DANGEROUS / UNKNOWN definitions with exact thresholds
- Why ~95% of stops score DANGEROUS (the strategic context)
- How gap is measured — Measured (from car behind) vs. Estimated (driver's own interval)
- How position delta is measured — why pit ENTRY readings are misleading, and the two-window approach (Δ Immediate after pit exit + Δ Settled ~3 laps later)
- Cost Score formula with a worked example (Δ Immediate = +12, Δ Settled = −2 = textbook undercut)
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
net = gap_to_car_behind − (pit_duration + circuit_extra)
```

**`pit_duration`** (from OpenF1) is the full entry-to-exit time — it already includes pit lane traversal. **`circuit_extra`** is a small per-circuit penalty (1.5–4.5s) for in/out-lap speed delta that falls outside the measured stop window. Monaco adds ~4s; Spa ~1.5s; average ~3s.

| Score | Condition | Meaning |
|---|---|---|
| **SAFE** | net > +5s | Emerged ahead with a comfortable margin |
| **MARGINAL** | 0 < net ≤ 5s | Emerged ahead, but razor-thin — any hesitation costs position |
| **RISKY** | net ≤ 0, gap ≥ 50% of total cost | Gap short, but not catastrophically so — rival pitting likely neutralises |
| **CRITICAL** | net ≤ 0, gap < 50% of total cost | Gap nowhere near sufficient — position loss likely regardless of rival's strategy |
| **UNKNOWN** | no gap data | Race leader (gap = 0), or interval data unavailable |

**Gap measurement method:**
- **Measured** (~86% of stops): gap read directly from the car at position+1 at pit entry
- **Estimated** (~14%): pitting driver's own interval used instead — happens at the back of the field or when position data is missing
- Race leaders' own interval is 0 (they have no car ahead to measure against), so their stops are scored UNKNOWN rather than CRITICAL

**Key insight:** Most F1 pit stops score RISKY or CRITICAL — this is by design. F1 strategy is built on the expectation that rivals will also pit. This dashboard scores each stop in isolation: if the rival stays out, does the gap hold? CRITICAL means the gap was genuinely unworkable — not just a normal strategic gamble.

---

## How Position Delta Is Measured

Most analytics tools measure position change from "the lap before" to "the lap after" pitting. That produces misleading numbers — the first position reading after pit **entry** captures the driver still physically in the pit lane, so every stop looks like a catastrophic loss.

This dashboard anchors both windows to **pit exit**, not pit entry, and reports two deltas per stop:

| Column | Definition |
|---|---|
| **Pos Before** | Last position reading ≥60s before pit entry — stable reference, avoids in-lap noise |
| **Δ Immediate** | First position reading after **pit exit** — shows the traffic hole the stop creates. Almost always positive (loss). This is the normal pit lane effect, not an outcome metric |
| **Pos Settled (~3 laps)** | Position ~270s after pit exit (~3 laps at 90s avg). Traffic cleared, tyre advantage registers |
| **Δ Settled** | Net positions gained or lost at the settled window. **This is the real outcome.** Positive = fell back, negative = gained |
| **Cost Score** | `Δ Settled − expected_Δ_Settled[risk_level]`. Season average Δ Settled per risk level is the baseline. Measures how much worse (or better) the stop was vs what normally happens at that timing window |

The 270-second settled window is the established standard in F1 analytics (FastF1 / Agastya Bassi, confirmed by F1_Strat_Manager N16 with MAX_LAP_GAP=5). Undercut success is defined at lap Y+3 after the rival also pits — the same window used here.

**Cost Score example:** A DANGEROUS stop is expected to lose ~1–2 positions on average (the undercut usually recovers). A stop with Δ Immediate = +15 and Δ Settled = +12 has Cost Score ≈ +10 — 10 positions worse than the DANGEROUS baseline. That is a genuinely failed strategy call, not normal pit traffic.

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
  and dual position delta per stop:
    - Δ Immediate: first reading after pit EXIT (not entry), captures the traffic hole
    - Δ Settled: position ~270s (~3 laps) after pit exit, when tyre advantage registers
  Pos Before is anchored ≥60s before entry for stability. Standard F1 analytics window
  (FastF1 / Agastya Bassi research). Outputs stop_outcomes_{year}.csv.

  Cost Score (computed in app.py at runtime):
    cost_score = Δ Settled − expected_Δ_Settled[risk_level]
  expected_Δ_Settled is the season mean for each risk level (SAFE / MARGINAL / DANGEROUS).
  Ranks stops by how much worse they were vs what normally happens at that timing window —
  not just raw positions lost, which conflates normal pit lane effects with real failures.

risk.py
  Core scoring engine. For each stop:
    1. Finds the car at position+1 using the position timeline
    2. Reads that car's interval at pit entry time (Measured method)
    3. Falls back to pitting driver's own interval if position data is missing
    4. Computes net gap and assigns SAFE / MARGINAL / RISKY / CRITICAL / UNKNOWN
       Formula: net = gap − (pit_duration + circuit_extra)
       pit_duration is full entry-to-exit time from OpenF1 (no extra traversal constant).
       circuit_extra is a per-circuit in/out-lap penalty from a 30-circuit lookup table.
    5. Joins tyre compound and age from stints data
    6. Finds the nearest team radio clip within 2 minutes for RISKY/CRITICAL stops
  Outputs risk_scores_{year}.csv.

app.py
  Streamlit dashboard. 4 tabs with Plotly charts. Features:
    - Team hex colours from OpenF1 applied to all charts
    - Driver headshots from OpenF1 in Tab 2 and Tab 3
    - Weather annotations (rainfall, track temp) on Race Timeline
    - Column tooltips on every table via st.column_config
    - Story cards on radio clips: net gap, emergence direction, positions lost (settled); shown for RISKY/CRITICAL stops
    - Sidebar year selector (2023 / 2024 / 2025) and team filter
    - Box plot capped at 120s (red flag / drive-through stops excluded from view)
    - Tab 3 leaderboard: ranked by Cost Score, 9-column layout with headshots
    - Cost Score computed at runtime: season baseline per risk level joined at load time
    - Final Pos column in positions gained table — confirms whether undercut held to flag
```

---

## Key Findings (2023–2025)

### 2025 (30 races, 867 stops)
- **Ferrari fastest**: 22.9s median — edged Red Bull by 0.1s for the first time
- **Haas highest slow-stop rate**: 14.1% of stops exceeded 30s
- 64 SAFE, 39 MARGINAL, 93 RISKY, 659 CRITICAL, 12 UNKNOWN
- Measured gap coverage: 85.0%

### 2024 (30 races, 865 stops)
- **Red Bull fastest**: 22.9s median
- **Kick Sauber highest slow-stop rate**: 21.7%
- 75 SAFE, 46 MARGINAL, 106 RISKY, 628 CRITICAL, 10 UNKNOWN
- Medium compound: 48.6% of all stops
- Measured gap coverage: 86.0%

### 2023 (29 races, 717 stops)
- **Red Bull fastest**: 23.2s median
- **Williams highest slow-stop rate**: 20.3%
- 40 SAFE, 39 MARGINAL, 59 RISKY, 577 CRITICAL, 2 UNKNOWN
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

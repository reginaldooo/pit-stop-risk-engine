"""
Step 2c — Pit Window Risk Scoring
Scores each pit stop as SAFE / MARGINAL / RISKY / CRITICAL based on gap at pit entry.

OpenF1 pit_duration is the full entry-to-exit time (~22-25s), so we do NOT add
a generic traversal constant. We add only a small circuit-specific in/out-lap
penalty (2-5s) for the marginal time lost beyond the measured stop.

Risk categories:
  SAFE      — net > +5s   (emerged ahead with comfortable margin)
  MARGINAL  — 0 < net ≤ 5s (emerged ahead, razor-thin)
  RISKY     — net ≤ 0 AND gap covers ≥50% of total cost
  CRITICAL  — net ≤ 0 AND gap covers <50% of total cost
  UNKNOWN   — no gap data

Gap method (fixed): find the car directly behind the pitting driver at pit entry
time, then read *that* car's interval — the true gap the crew is racing against.
Falls back to pitting driver's own interval when position data is unavailable.

Enriches results with tire compound (stints) and nearest team radio URL.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
SAFE_BUFFER = 5.0
RADIO_WINDOW_SECONDS = 120

# Extra seconds beyond pit_duration lost on in/out laps (circuit-specific).
# pit_duration already covers full traversal; these account for additional
# time lost due to circuit layout (pit lane entry/exit speed restrictions).
CIRCUIT_EXTRA_DEFAULT = 3.0
_CIRCUIT_EXTRA_MAP = {
    "spa": 1.5,
    "francorchamps": 1.5,
    "zandvoort": 2.0,
    "montreal": 2.0,
    "miami": 2.5,
    "austria": 2.5,
    "spielberg": 2.5,
    "silverstone": 2.5,
    "monaco": 4.0,
    "singapore": 4.5,
    "baku": 4.0,
    "imola": 4.0,
    "lusail": 3.5,
    "qatar": 3.5,
    "bahrain": 2.0,
    "sakhir": 2.0,
    "jeddah": 2.5,
    "saudi": 2.5,
    "albert_park": 2.5,
    "melbourne": 2.5,
    "suzuka": 2.5,
    "shanghai": 2.5,
    "china": 2.5,
    "barcelona": 2.5,
    "spain": 2.5,
    "hungaroring": 3.0,
    "budapest": 3.0,
    "monza": 2.0,
    "italy": 2.0,
    "austin": 2.5,
    "cota": 2.5,
    "mexico": 3.0,
    "interlagos": 3.5,
    "brazil": 3.5,
    "vegas": 2.0,
    "las_vegas": 2.0,
    "abu_dhabi": 2.5,
    "yas": 2.5,
}


def circuit_extra(circuit: str) -> float:
    c = (circuit or "").lower().replace(" ", "_")
    for key, val in _CIRCUIT_EXTRA_MAP.items():
        if key in c:
            return val
    return CIRCUIT_EXTRA_DEFAULT


def score_stop(gap: Optional[float], pit_duration: float, circuit: str = "") -> str:
    if gap is None or pd.isna(gap):
        return "UNKNOWN"
    extra = circuit_extra(circuit)
    total_cost = pit_duration + extra
    net = gap - total_cost
    if net > SAFE_BUFFER:
        return "SAFE"
    if net > 0:
        return "MARGINAL"
    coverage = gap / total_cost if total_cost > 0 else 0
    if coverage >= 0.5:
        return "RISKY"
    return "CRITICAL"


def stint_for_stop(lap: int, driver: int, session: int, stints: pd.DataFrame) -> dict:
    """Returns compound and tyre_age_at_entry for a given pit stop lap."""
    driver_stints = stints[
        (stints["session_key"] == session) & (stints["driver_number"] == driver)
    ]
    match = driver_stints[
        (driver_stints["lap_start"] <= lap) & (driver_stints["lap_end"] >= lap)
    ]
    if match.empty:
        return {"compound": None, "tyre_age_at_entry": None}
    row = match.iloc[0]
    age_at_start = row.get("tyre_age_at_start", 0) or 0
    laps_into_stint = lap - int(row.get("lap_start", lap))
    return {
        "compound": str(row["compound"]),
        "tyre_age_at_entry": int(age_at_start) + laps_into_stint,
    }


def nearest_radio(
    stop_time: pd.Timestamp,
    driver: int,
    session: int,
    radio: pd.DataFrame,
) -> Optional[str]:
    if radio.empty:
        return None
    driver_radio = radio[
        (radio["session_key"] == session) & (radio["driver_number"] == driver)
    ].copy()
    if driver_radio.empty:
        return None
    driver_radio["date"] = pd.to_datetime(driver_radio["date"], format="ISO8601", utc=True)
    window = driver_radio[
        (driver_radio["date"] >= stop_time)
        & (driver_radio["date"] <= stop_time + pd.Timedelta(seconds=RADIO_WINDOW_SECONDS))
    ].sort_values("date")
    if window.empty:
        return None
    return str(window.iloc[0]["recording_url"])


def _parse_gap(raw) -> Optional[float]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        return float(str(raw).replace("+", ""))
    except (ValueError, TypeError):
        return None


def gap_to_car_behind(
    stop_time: pd.Timestamp,
    driver: int,
    session: int,
    positions: pd.DataFrame,
    intervals: pd.DataFrame,
) -> tuple[Optional[float], str]:
    """
    Returns (gap_seconds, method) where method is 'exact' or 'fallback'.

    Exact: find car at position+1, read its interval at pit entry time.
    Fallback: use pitting driver's own interval (original approximation).
    """
    session_pos = positions[positions["session_key"] == session]
    session_ivl = intervals[intervals["session_key"] == session]

    # Find pitting driver's position at pit entry
    driver_pos_history = session_pos[session_pos["driver_number"] == driver]
    before_pit = driver_pos_history[driver_pos_history["date"] <= stop_time].sort_values("date")

    if not before_pit.empty:
        pitting_position = int(before_pit.iloc[-1]["position"])

        # Find driver at position+1 (car directly behind) at same time
        behind_pos_history = session_pos[session_pos["position"] == pitting_position + 1]
        behind_before = behind_pos_history[behind_pos_history["date"] <= stop_time].sort_values("date")

        if not behind_before.empty:
            car_behind_driver = int(behind_before.iloc[-1]["driver_number"])

            # Get that driver's interval at pit entry time
            behind_intervals = session_ivl[
                (session_ivl["driver_number"] == car_behind_driver)
                & (session_ivl["date"] <= stop_time)
            ].sort_values("date")

            if not behind_intervals.empty:
                gap = _parse_gap(behind_intervals.iloc[-1].get("interval"))
                if gap is not None:
                    return gap, "Measured"

    # Fallback: pitting driver's own interval
    own_intervals = session_ivl[
        (session_ivl["driver_number"] == driver)
        & (session_ivl["date"] <= stop_time)
    ].sort_values("date")

    if not own_intervals.empty:
        gap = _parse_gap(own_intervals.iloc[-1].get("interval"))
        if gap is not None and gap > 0:  # gap=0 means race leader, not a real gap
            return gap, "Estimated"

    return None, "No data"


def build_risk_scores(
    pit: pd.DataFrame,
    intervals: pd.DataFrame,
    stints: pd.DataFrame,
    radio: pd.DataFrame,
    positions: pd.DataFrame,
) -> pd.DataFrame:
    if intervals.empty or pit.empty:
        return pd.DataFrame()

    pit = pit.copy()
    intervals = intervals.copy()
    positions = positions.copy()

    pit["date"] = pd.to_datetime(pit["date"], format="ISO8601", utc=True)
    intervals["date"] = pd.to_datetime(intervals["date"], format="ISO8601", utc=True)
    positions["date"] = pd.to_datetime(positions["date"], format="ISO8601", utc=True)

    results = []
    for _, stop in pit.iterrows():
        session = stop["session_key"]
        driver = stop["driver_number"]
        stop_time = stop["date"]
        pit_duration = stop.get("pit_duration")
        lap = stop.get("lap_number")

        if pd.isna(pit_duration) or pit_duration <= 0:
            continue

        gap, gap_method = gap_to_car_behind(
            stop_time, int(driver), session, positions, intervals
        )

        circuit_name = str(stop.get("circuit", "") or "")
        risk = score_stop(gap, pit_duration, circuit_name)
        stint_info = stint_for_stop(
            int(lap) if not pd.isna(lap) else 0, int(driver), session, stints
        )
        radio_url = (
            nearest_radio(stop_time, int(driver), session, radio)
            if risk in ("RISKY", "CRITICAL")
            else None
        )

        results.append({
            "session_key": session,
            "circuit": stop.get("circuit", ""),
            "driver_number": driver,
            "driver_acronym": stop.get("driver_acronym", str(driver)),
            "team_name": stop.get("team_name", "Unknown"),
            "team_colour": stop.get("team_colour", None),
            "lap_number": lap,
            "pit_duration": round(float(pit_duration), 3),
            "gap_at_entry": round(gap, 3) if gap is not None else None,
            "gap_method": gap_method,
            "risk_score": risk,
            "compound": stint_info["compound"],
            "tyre_age_at_entry": stint_info["tyre_age_at_entry"],
            "radio_url": radio_url,
        })

    return pd.DataFrame(results)


if __name__ == "__main__":
    import sys
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024

    pit = pd.read_csv(DATA_DIR / f"pit_stops_{year}.csv")
    intervals = pd.read_csv(DATA_DIR / f"intervals_{year}.csv", low_memory=False)
    stints = pd.read_csv(DATA_DIR / f"stints_{year}.csv")
    positions = pd.read_csv(DATA_DIR / f"positions_{year}.csv")
    radio_path = DATA_DIR / f"team_radio_{year}.csv"
    radio = pd.read_csv(radio_path) if radio_path.exists() else pd.DataFrame()

    print(f"\n=== Building risk scores for {year} ===")
    risk_df = build_risk_scores(pit, intervals, stints, radio, positions)

    if risk_df.empty:
        print("No risk scores computed")
    else:
        risk_df.to_csv(DATA_DIR / f"risk_scores_{year}.csv", index=False)
        print(f"Scored {len(risk_df)} stops")
        print("\nRisk distribution:")
        print(risk_df["risk_score"].value_counts().to_string())
        print("\nGap method distribution:")
        print(risk_df["gap_method"].value_counts().to_string())
        exact_pct = (risk_df["gap_method"] == "Measured").mean() * 100
        print(f"\nExact gap coverage: {exact_pct:.1f}%")
        high_risk_with_radio = risk_df[
            risk_df["risk_score"].isin(["RISKY", "CRITICAL"]) & risk_df["radio_url"].notna()
        ]
        print(f"RISKY/CRITICAL stops with radio clip: {len(high_risk_with_radio)}")
        print("\nAvg tyre age at pit entry by compound:")
        print(risk_df.groupby("compound")["tyre_age_at_entry"].mean().round(1).to_string())
        print(f"\nSaved risk_scores_{year}.csv")

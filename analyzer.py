"""
Step 2a & 2b — Analysis Layer
Stop duration stats per team + position delta per pit stop.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
OUTLIER_THRESHOLD = 30.0  # seconds (total pit lane time; >30s = slow stop)
SETTLE_SECONDS = 270  # ~3 laps at 90s avg — standard F1 analytics window (FastF1/Agastya Bassi)


def load_data(year: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pit = pd.read_csv(DATA_DIR / f"pit_stops_{year}.csv")
    pos = pd.read_csv(DATA_DIR / f"positions_{year}.csv")
    intervals = pd.read_csv(DATA_DIR / f"intervals_{year}.csv")
    return pit, pos, intervals


def team_stop_stats(pit: pd.DataFrame) -> pd.DataFrame:
    """2a: Stop duration statistics per team."""
    pit = pit[pit["pit_duration"].notna() & (pit["pit_duration"] > 0)]

    stats = (
        pit.groupby("team_name")["pit_duration"]
        .agg(
            stop_count="count",
            median="median",
            mean="mean",
            std="std",
            p95=lambda x: x.quantile(0.95),
        )
        .reset_index()
    )

    stats["outlier_count"] = (
        pit[pit["pit_duration"] > OUTLIER_THRESHOLD]
        .groupby("team_name")["pit_duration"]
        .count()
        .reindex(stats["team_name"])
        .fillna(0)
        .values
    )
    stats["outlier_rate"] = (stats["outlier_count"] / stats["stop_count"] * 100).round(1)
    stats = stats.sort_values("median").reset_index(drop=True)

    for col in ["median", "mean", "std", "p95"]:
        stats[col] = stats[col].round(3)

    return stats


def position_delta_per_stop(pit: pd.DataFrame, pos: pd.DataFrame) -> pd.DataFrame:
    """2b: Position gained/lost per pit stop."""
    if pos.empty or pit.empty:
        return pd.DataFrame()

    pos = pos.copy()
    pos["date"] = pd.to_datetime(pos["date"], format="ISO8601", utc=True)
    pit = pit.copy()
    pit["date"] = pd.to_datetime(pit["date"], format="ISO8601", utc=True)

    results = []
    for _, stop in pit.iterrows():
        session = stop["session_key"]
        driver = stop["driver_number"]
        pit_entry_time = stop["date"]
        pit_duration = stop.get("pit_duration")

        if pd.isna(pit_duration) or pit_duration <= 0:
            continue

        pit_exit_time = pit_entry_time + pd.Timedelta(seconds=float(pit_duration))

        driver_pos = pos[
            (pos["session_key"] == session) & (pos["driver_number"] == driver)
        ].sort_values("date")

        if driver_pos.empty:
            continue

        # Stable position before pit: last reading ≥60s before entry avoids in-lap noise
        before = driver_pos[driver_pos["date"] <= pit_entry_time - pd.Timedelta(seconds=60)]
        pos_before = int(before.iloc[-1]["position"]) if not before.empty else None

        # Immediate position: first reading after pit exit (traffic effect visible)
        after_all = driver_pos[driver_pos["date"] > pit_exit_time]
        pos_after_immediate = int(after_all.iloc[0]["position"]) if not after_all.empty else None

        # Settled position: ~3 laps after exit, tyre advantage registered, traffic cleared
        after_settled = driver_pos[
            driver_pos["date"] >= pit_exit_time + pd.Timedelta(seconds=SETTLE_SECONDS)
        ]
        pos_after_settled = int(after_settled.iloc[0]["position"]) if not after_settled.empty else None

        if pos_before is None or pos_after_immediate is None:
            continue

        delta_immediate = pos_after_immediate - pos_before
        delta_settled = (pos_after_settled - pos_before) if pos_after_settled is not None else None
        final_position = int(driver_pos.iloc[-1]["position"])

        results.append({
            "session_key": session,
            "circuit": stop.get("circuit", ""),
            "driver_number": driver,
            "driver_acronym": stop.get("driver_acronym", str(driver)),
            "team_name": stop.get("team_name", "Unknown"),
            "lap_number": stop.get("lap_number"),
            "pit_duration": pit_duration,
            "position_before": pos_before,
            "position_after": pos_after_immediate,
            "position_delta": delta_immediate,
            "position_settled": pos_after_settled,
            "delta_settled": delta_settled,
            "final_position": final_position,
        })

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values("delta_settled", ascending=False, na_position="last").reset_index(drop=True)
    return df


if __name__ == "__main__":
    import sys
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024

    print(f"\n=== Loading {year} cached data ===")
    pit, pos, intervals = load_data(year)
    print(f"Pit stops: {len(pit)} | Positions: {len(pos)} | Intervals: {len(intervals)}")

    print("\n=== Team Stop Duration Stats ===")
    stats = team_stop_stats(pit)
    print(stats.to_string(index=False))

    print("\n=== Position Delta per Stop (top 10 worst) ===")
    outcomes = position_delta_per_stop(pit, pos)
    if not outcomes.empty:
        print(outcomes.head(10).to_string(index=False))
        outcomes.to_csv(DATA_DIR / f"stop_outcomes_{year}.csv", index=False)
        print(f"\nSaved stop_outcomes_{year}.csv")
    else:
        print("No position delta data available")

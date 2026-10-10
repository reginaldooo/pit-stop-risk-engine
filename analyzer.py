"""
Step 2a & 2b — Analysis Layer
Stop duration stats per team + position delta per pit stop.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
OUTLIER_THRESHOLD = 30.0  # seconds (total pit lane time; >30s = slow stop)


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
        stop_time = stop["date"]

        driver_pos = pos[
            (pos["session_key"] == session) & (pos["driver_number"] == driver)
        ].sort_values("date")

        if driver_pos.empty:
            continue

        before = driver_pos[driver_pos["date"] < stop_time]
        after = driver_pos[driver_pos["date"] > stop_time]

        pos_before = int(before["position"].iloc[-1]) if not before.empty else None
        pos_after = int(after["position"].iloc[0]) if not after.empty else None

        if pos_before is None or pos_after is None:
            continue

        delta = pos_after - pos_before  # positive = lost places, negative = gained

        results.append({
            "session_key": session,
            "circuit": stop.get("circuit", ""),
            "driver_number": driver,
            "driver_acronym": stop.get("driver_acronym", str(driver)),
            "team_name": stop.get("team_name", "Unknown"),
            "lap_number": stop.get("lap_number"),
            "pit_duration": stop.get("pit_duration"),
            "position_before": pos_before,
            "position_after": pos_after,
            "position_delta": delta,
        })

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values("position_delta", ascending=False).reset_index(drop=True)
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

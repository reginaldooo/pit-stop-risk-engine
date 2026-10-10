"""
Step 1 — Data Layer
Fetches race data from OpenF1 API and caches to CSV files in data/.
Supports resume: per-session JSON cache in data/cache/ prevents re-fetching.
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.openf1.org/v1"
DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "cache"
RATE_LIMIT_DELAY = 2.1  # safe for 30 req/min limit
MAX_RETRIES = 5


def fetch(endpoint: str, params: dict) -> list[dict]:
    url = f"{BASE_URL}/{endpoint}"
    backoff = 10.0
    for attempt in range(MAX_RETRIES):
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 429:
            print(f"    [rate limit] waiting {backoff:.0f}s before retry {attempt + 1}/{MAX_RETRIES}...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
            continue
        if response.status_code == 404:
            return []
        response.raise_for_status()
        time.sleep(RATE_LIMIT_DELAY)
        return response.json()
    raise RuntimeError(f"Failed after {MAX_RETRIES} retries: {url} {params}")


def cached_fetch(cache_key: str, endpoint: str, params: dict) -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    data = fetch(endpoint, params)
    cache_file.write_text(json.dumps(data))
    return data


def fetch_sessions(year: int) -> pd.DataFrame:
    data = cached_fetch(f"sessions_{year}", "sessions", {"year": year, "session_type": "Race"})
    df = pd.DataFrame(data)
    cols = ["session_key", "session_name", "date_start", "country_name", "circuit_short_name"]
    return df[[c for c in cols if c in df.columns]]


def fetch_drivers(session_key: int) -> pd.DataFrame:
    data = cached_fetch(f"{session_key}_drivers", "drivers", {"session_key": session_key})
    df = pd.DataFrame(data)
    cols = ["driver_number", "full_name", "name_acronym", "team_name"]
    return df[[c for c in cols if c in df.columns]]


def fetch_pit_stops(session_key: int) -> pd.DataFrame:
    data = cached_fetch(f"{session_key}_pit", "pit", {"session_key": session_key})
    return pd.DataFrame(data) if data else pd.DataFrame()


def fetch_positions(session_key: int) -> pd.DataFrame:
    data = cached_fetch(f"{session_key}_position", "position", {"session_key": session_key})
    return pd.DataFrame(data) if data else pd.DataFrame()


def fetch_intervals(session_key: int) -> pd.DataFrame:
    data = cached_fetch(f"{session_key}_intervals", "intervals", {"session_key": session_key})
    return pd.DataFrame(data) if data else pd.DataFrame()


def fetch_stints(session_key: int) -> pd.DataFrame:
    data = cached_fetch(f"{session_key}_stints", "stints", {"session_key": session_key})
    return pd.DataFrame(data) if data else pd.DataFrame()


def fetch_team_radio(session_key: int) -> pd.DataFrame:
    data = cached_fetch(f"{session_key}_team_radio", "team_radio", {"session_key": session_key})
    return pd.DataFrame(data) if data else pd.DataFrame()


def build_dataset(year: int, dry_run: bool = False) -> None:
    DATA_DIR.mkdir(exist_ok=True)

    print(f"Fetching {year} race sessions...")
    sessions = fetch_sessions(year)
    sessions.to_csv(DATA_DIR / f"sessions_{year}.csv", index=False)
    print(f"  {len(sessions)} races found")

    session_sample = sessions.head(2) if dry_run else sessions
    if dry_run:
        print(f"[dry-run] Sampling {len(session_sample)} sessions only")

    all_pits, all_positions, all_intervals, all_stints, all_radio = [], [], [], [], []

    for i, (_, session) in enumerate(session_sample.iterrows(), 1):
        key = int(session["session_key"])
        name = session.get("circuit_short_name", key)
        print(f"  [{i}/{len(session_sample)}] {name} (session {key})")

        drivers = fetch_drivers(key)
        if drivers.empty or "driver_number" not in drivers.columns:
            driver_map = {}
        else:
            driver_map = drivers.set_index("driver_number")[
                [c for c in ["full_name", "name_acronym", "team_name"] if c in drivers.columns]
            ].to_dict("index")

        pits = fetch_pit_stops(key)
        if not pits.empty:
            pits["session_key"] = key
            pits["circuit"] = name
            pits["team_name"] = pits["driver_number"].map(
                lambda d: driver_map.get(d, {}).get("team_name", "Unknown")
            )
            pits["driver_acronym"] = pits["driver_number"].map(
                lambda d: driver_map.get(d, {}).get("name_acronym", str(d))
            )
            all_pits.append(pits)
            print(f"    {len(pits)} pit stops")

        positions = fetch_positions(key)
        if not positions.empty:
            positions["session_key"] = key
            all_positions.append(positions)

        intervals = fetch_intervals(key)
        if not intervals.empty:
            intervals["session_key"] = key
            all_intervals.append(intervals)

        stints = fetch_stints(key)
        if not stints.empty:
            stints["session_key"] = key
            all_stints.append(stints)

        radio = fetch_team_radio(key)
        if not radio.empty:
            radio["session_key"] = key
            radio["circuit"] = name
            all_radio.append(radio)

    def save(frames: list, filename: str) -> None:
        if not frames:
            print(f"  No data for {filename}")
            return
        df = pd.concat(frames, ignore_index=True)
        df.to_csv(DATA_DIR / filename, index=False)
        print(f"Saved {filename}: {len(df)} rows")

    save(all_pits, f"pit_stops_{year}.csv")
    save(all_positions, f"positions_{year}.csv")
    save(all_intervals, f"intervals_{year}.csv")
    save(all_stints, f"stints_{year}.csv")
    save(all_radio, f"team_radio_{year}.csv")

    print(f"\nStep 1 complete — {year} data cached to data/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch OpenF1 data")
    parser.add_argument("--year", type=int, default=2024, help="F1 season year")
    parser.add_argument("--dry-run", action="store_true", help="Fetch only 2 sessions for testing")
    args = parser.parse_args()

    build_dataset(args.year, dry_run=args.dry_run)

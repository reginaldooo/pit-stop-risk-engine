"""
Step 3 — Streamlit Dashboard
Team Principal pit stop risk view: 3 tabs — Team Comparison, Race Timeline, Costliest Stops.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

RISK_COLOR = {
    "SAFE": "#00C851",
    "MARGINAL": "#FFBB33",
    "RISKY": "#FF8800",
    "CRITICAL": "#CC0000",
    "UNKNOWN": "#AAAAAA",
}
COMPOUND_COLOR = {
    "SOFT": "#E8002D",
    "MEDIUM": "#FFF200",
    "HARD": "#FFFFFF",
    "INTERMEDIATE": "#39B54A",
    "WET": "#0067FF",
}

st.set_page_config(
    page_title="Pit Stop Risk Engine",
    page_icon="🏎",
    layout="wide",
)


@st.cache_data
def load_year_data(year: int):
    pit_path = DATA_DIR / f"pit_stops_{year}.csv"
    if not pit_path.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    pit = pd.read_csv(pit_path)
    risk_path = DATA_DIR / f"risk_scores_{year}.csv"
    risk = pd.read_csv(risk_path) if risk_path.exists() else pd.DataFrame()
    outcomes_path = DATA_DIR / f"stop_outcomes_{year}.csv"
    outcomes = pd.read_csv(outcomes_path) if outcomes_path.exists() else pd.DataFrame()
    sessions_path = DATA_DIR / f"sessions_{year}.csv"
    sessions = pd.read_csv(sessions_path) if sessions_path.exists() else pd.DataFrame()
    weather_path = DATA_DIR / f"weather_{year}.csv"
    weather = pd.read_csv(weather_path) if weather_path.exists() else pd.DataFrame()
    drivers_path = DATA_DIR / f"drivers_{year}.csv"
    drivers = pd.read_csv(drivers_path) if drivers_path.exists() else pd.DataFrame()
    return pit, risk, outcomes, sessions, weather, drivers


@st.cache_data
def team_colour_map(drivers: pd.DataFrame) -> dict:
    """Returns {team_name: #RRGGBB} using the latest entry per team."""
    if drivers.empty or "team_colour" not in drivers.columns:
        return {}
    latest = drivers.dropna(subset=["team_colour"]).drop_duplicates("team_name", keep="last")
    return {
        row["team_name"]: f"#{row['team_colour']}"
        for _, row in latest.iterrows()
        if pd.notna(row.get("team_colour"))
    }


def team_stop_stats(pit: pd.DataFrame) -> pd.DataFrame:
    pit = pit[pit["pit_duration"].notna() & (pit["pit_duration"] > 0)]
    stats = (
        pit.groupby("team_name")["pit_duration"]
        .agg(stop_count="count", median="median", mean="mean", std="std")
        .reset_index()
    )
    outliers = (
        pit[pit["pit_duration"] > 30.0]
        .groupby("team_name")["pit_duration"]
        .count()
        .reindex(stats["team_name"])
        .fillna(0)
        .values
    )
    stats["outlier_rate"] = (outliers / stats["stop_count"] * 100).round(1)
    for col in ["median", "mean", "std"]:
        stats[col] = stats[col].round(3)
    return stats.sort_values("median").reset_index(drop=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("🏎 Pit Stop Risk Engine")
st.sidebar.caption("Toto Wolff mode")

available_years = sorted(
    [int(p.stem.split("_")[-1]) for p in DATA_DIR.glob("pit_stops_*.csv")],
    reverse=True,
)

if not available_years:
    st.error("No data found. Run `python fetcher.py --year 2024 --dry-run` first.")
    st.stop()

year = st.sidebar.selectbox("Season", available_years)
pit, risk, outcomes, sessions, weather, drivers = load_year_data(year)
TEAM_COLOR = team_colour_map(drivers)

HEADSHOT_MAP = {}
if not drivers.empty and "headshot_url" in drivers.columns and "driver_number" in drivers.columns:
    HEADSHOT_MAP = (
        drivers.dropna(subset=["headshot_url"])
        .drop_duplicates("driver_number", keep="last")
        .set_index("driver_number")["headshot_url"]
        .to_dict()
    )

all_teams = sorted(pit["team_name"].dropna().unique()) if not pit.empty else []
selected_teams = st.sidebar.multiselect("Filter teams", all_teams, default=all_teams)

if selected_teams:
    pit = pit[pit["team_name"].isin(selected_teams)]
    risk = risk[risk["team_name"].isin(selected_teams)] if not risk.empty else risk
    outcomes = outcomes[outcomes["team_name"].isin(selected_teams)] if not outcomes.empty else outcomes

st.sidebar.markdown("---")
st.sidebar.markdown("**Data coverage**")
if not sessions.empty:
    st.sidebar.caption(f"{len(sessions)} races in dataset")
st.sidebar.caption(f"{len(pit)} pit stops loaded")

st.sidebar.markdown("---")
st.sidebar.markdown("**Built by**")
st.sidebar.markdown("Reginaldo Ahnaf")
st.sidebar.markdown(
    "[![GitHub](https://img.shields.io/badge/GitHub-reginaldooo-181717?logo=github&style=flat-square)](https://github.com/reginaldooo) "
    "[![LinkedIn](https://img.shields.io/badge/LinkedIn-farrel--reginaldo-0A66C2?logo=linkedin&style=flat-square)](https://linkedin.com/in/farrel-reginaldo)"
)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(["Team Comparison", "Race Timeline", "Costliest Stops", "How to Read This"])


# ── Tab 1: Team Comparison ────────────────────────────────────────────────────

with tab1:
    st.header("Team Stop Duration Comparison")

    if pit.empty:
        st.info("No pit stop data loaded.")
    else:
        stats = team_stop_stats(pit)

        col1, col2 = st.columns(2)

        with col1:
            fig_bar = px.bar(
                stats,
                x="team_name",
                y="median",
                color="team_name",
                color_discrete_map=TEAM_COLOR,
                text="median",
                labels={"team_name": "Team", "median": "Median Stop (s)"},
                title=f"Median Pit Stop Duration — {year}",
            )
            fig_bar.update_traces(texttemplate="%{y:.2f}s", textposition="outside")
            fig_bar.update_layout(
                showlegend=False,
                xaxis_tickangle=-30,
                yaxis_range=[20, stats["median"].max() + 1.5],
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            st.caption("Y-axis starts at 20s — all teams are within a ~5s window.")

        with col2:
            BOX_CAP = 120.0
            pit_clean = pit[pit["pit_duration"].notna() & (pit["pit_duration"] > 0) & (pit["pit_duration"] <= BOX_CAP)]
            fig_box = px.box(
                pit_clean,
                x="team_name",
                y="pit_duration",
                color="team_name",
                color_discrete_map=TEAM_COLOR,
                labels={"team_name": "Team", "pit_duration": "Stop Duration (s)"},
                title=f"Stop Duration Distribution — {year}",
            )
            fig_box.update_layout(showlegend=False, xaxis_tickangle=-30)
            st.plotly_chart(fig_box, use_container_width=True)
            st.caption(f"Stops over {BOX_CAP:.0f}s excluded from chart (red flag / drive-through events).")

        # Compound breakdown per team
        if not risk.empty and "compound" in risk.columns:
            st.subheader("Tire Compound Usage by Team")
            compound_counts = (
                risk[risk["compound"].notna()]
                .groupby(["team_name", "compound"])
                .size()
                .reset_index(name="count")
            )
            if not compound_counts.empty:
                fig_compound = px.bar(
                    compound_counts,
                    x="team_name",
                    y="count",
                    color="compound",
                    color_discrete_map=COMPOUND_COLOR,
                    barmode="stack",
                    labels={"team_name": "Team", "count": "Stops", "compound": "Compound"},
                    title=f"Pit Stops by Tire Compound — {year}",
                )
                fig_compound.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(fig_compound, use_container_width=True)

        st.subheader("Stats Table")
        st.dataframe(
            stats.rename(columns={
                "team_name": "Team",
                "stop_count": "Stops",
                "median": "Median (s)",
                "mean": "Mean (s)",
                "std": "Std Dev",
                "outlier_rate": "Slow Stop Rate (%)",
            }),
            column_config={
                "Team": st.column_config.TextColumn("Team", help="F1 constructor name."),
                "Stops": st.column_config.NumberColumn("Stops", help="Total pit stops by this team across the season."),
                "Median (s)": st.column_config.NumberColumn("Median (s)", help="Middle value of all stop durations — less affected by extreme outliers than the mean."),
                "Mean (s)": st.column_config.NumberColumn("Mean (s)", help="Average stop duration across all stops."),
                "Std Dev": st.column_config.NumberColumn("Std Dev", help="Standard deviation of stop durations. Lower = more consistent crew performance."),
                "Slow Stop Rate (%)": st.column_config.NumberColumn("Slow Stop Rate (%)", help="Percentage of stops over 30 seconds. Usually caused by mechanical issues or a driver held for traffic."),
            },
            use_container_width=True,
            hide_index=True,
        )


# ── Tab 2: Race Timeline ──────────────────────────────────────────────────────

with tab2:
    st.header("Race Pit Stop Timeline")

    if risk.empty:
        st.info("No risk score data. Run `python risk.py` first.")
    else:
        available_circuits = sorted(risk["circuit"].dropna().unique())
        selected_circuit = st.selectbox("Select race", available_circuits)

        race_risk = risk[risk["circuit"] == selected_circuit].copy()

        if race_risk.empty:
            st.info("No stops for this race.")
        else:
            color_by = st.radio("Color by", ["Risk", "Compound"], horizontal=True)

            fig = go.Figure()

            has_tyre_age = "tyre_age_at_entry" in race_risk.columns

            def hover_text(r):
                age = f"Tyre age: {int(r['tyre_age_at_entry'])} laps<br>" if has_tyre_age and pd.notna(r.get("tyre_age_at_entry")) else ""
                return (
                    f"{r['driver_acronym']} ({r['team_name']})<br>"
                    f"Lap {r['lap_number']} — {r['pit_duration']}s<br>"
                    f"Compound: {r.get('compound', 'N/A')}<br>"
                    f"{age}"
                    f"Gap (car behind): {r['gap_at_entry']}s "
                    f"[{r.get('gap_method', '?')}]<br>"
                    f"Risk: {r['risk_score']}"
                )

            if color_by == "Risk":
                for score, group in race_risk.groupby("risk_score"):
                    fig.add_trace(go.Scatter(
                        x=group["lap_number"],
                        y=group["pit_duration"],
                        mode="markers",
                        marker=dict(size=12, color=RISK_COLOR.get(score, "#AAAAAA")),
                        name=score,
                        text=group.apply(hover_text, axis=1),
                        hoverinfo="text",
                    ))
            else:
                for compound, group in race_risk.groupby("compound"):
                    fig.add_trace(go.Scatter(
                        x=group["lap_number"],
                        y=group["pit_duration"],
                        mode="markers",
                        marker=dict(
                            size=12,
                            color=COMPOUND_COLOR.get(str(compound), "#AAAAAA"),
                            line=dict(
                                color=[RISK_COLOR.get(r, "#AAAAAA") for r in group["risk_score"]],
                                width=2,
                            ),
                        ),
                        name=str(compound),
                        text=group.apply(hover_text, axis=1),
                        hoverinfo="text",
                    ))

            # Weather overlay: add rainfall annotation if detected for this circuit
            circuit_session_keys = race_risk["session_key"].unique() if "session_key" in race_risk.columns else []
            if not weather.empty and len(circuit_session_keys) > 0:
                race_weather = weather[
                    (weather["session_key"].isin(circuit_session_keys)) &
                    (weather["circuit"] == selected_circuit)
                ]
                if not race_weather.empty and race_weather["rainfall"].astype(bool).any():
                    fig.add_annotation(
                        text="🌧 Rainfall detected during race",
                        xref="paper", yref="paper",
                        x=0.01, y=1.05,
                        showarrow=False,
                        font=dict(color="#4FC3F7", size=12),
                    )
                avg_track_temp = race_weather["track_temperature"].mean()
                if pd.notna(avg_track_temp):
                    fig.add_annotation(
                        text=f"Track temp: {avg_track_temp:.1f}°C avg",
                        xref="paper", yref="paper",
                        x=0.99, y=1.05,
                        showarrow=False,
                        xanchor="right",
                        font=dict(color="#FFCC80", size=12),
                    )

            fig.update_layout(
                title=f"{selected_circuit} — Pit Stops by Lap",
                xaxis_title="Lap Number",
                yaxis_title="Stop Duration (s)",
                legend_title=color_by,
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Stops", len(race_risk))
            col2.metric("Critical", int((race_risk["risk_score"] == "CRITICAL").sum()))
            col3.metric("Risky", int((race_risk["risk_score"] == "RISKY").sum()))
            col4.metric("Marginal", int((race_risk["risk_score"] == "MARGINAL").sum()))

            # High-risk stops with radio
            dangerous = race_risk[race_risk["risk_score"].isin(["RISKY", "CRITICAL"])]
            if not dangerous.empty and "radio_url" in dangerous.columns:
                radio_stops = dangerous[dangerous["radio_url"].notna()]
                if not radio_stops.empty:
                    st.subheader("Nearest radio clip — may not be about the stop")
                    rows_list = list(radio_stops.iterrows())
                    for i in range(0, len(rows_list), 3):
                        chunk = rows_list[i:i+3]
                        cols = st.columns(len(chunk))
                        for col, (_, row) in zip(cols, chunk):
                            with col:
                                shot_url = HEADSHOT_MAP.get(int(row["driver_number"])) if pd.notna(row.get("driver_number")) else None
                                if shot_url:
                                    st.image(shot_url, width=80)
                                net = (
                                    round(row["gap_at_entry"] - row["pit_duration"], 1)
                                    if pd.notna(row.get("gap_at_entry")) else None
                                )
                                compound_str = f" · {row['compound']}" if pd.notna(row.get("compound")) else ""
                                direction = "behind" if net is not None and net <= 0 else "ahead"
                                net_str = f"Net: **{net:+.1f}s** — emerged {direction}" if net is not None else "Net: N/A"
                                st.markdown(
                                    f"**{row['driver_acronym']}** · {row['team_name']}\n\n"
                                    f"Lap {int(row['lap_number'])}{compound_str}\n\n"
                                    f"Gap: {row['gap_at_entry']}s vs {row['pit_duration']:.1f}s stop\n\n"
                                    f"{net_str}"
                                )
                                st.audio(row["radio_url"])

            detail_cols = ["driver_acronym", "team_name", "lap_number", "pit_duration", "gap_at_entry", "risk_score"]
            if "gap_method" in race_risk.columns:
                detail_cols.insert(5, "gap_method")
            if "compound" in race_risk.columns:
                detail_cols.insert(4, "compound")
            if "tyre_age_at_entry" in race_risk.columns:
                compound_idx = detail_cols.index("compound") + 1 if "compound" in detail_cols else 4
                detail_cols.insert(compound_idx, "tyre_age_at_entry")
            rename_map = {
                "driver_acronym": "Driver",
                "team_name": "Team",
                "lap_number": "Lap",
                "pit_duration": "Stop (s)",
                "compound": "Compound",
                "tyre_age_at_entry": "Tyre Age",
                "gap_at_entry": "Gap Behind (s)",
                "gap_method": "Gap Source",
                "risk_score": "Risk",
            }
            st.dataframe(
                race_risk[detail_cols]
                .rename(columns=rename_map)
                .sort_values("Lap"),
                column_config={
                    "Driver": st.column_config.TextColumn("Driver", help="Driver's 3-letter FIA identifier."),
                    "Team": st.column_config.TextColumn("Team", help="F1 constructor name."),
                    "Lap": st.column_config.NumberColumn("Lap", help="Lap number when the car entered the pit lane."),
                    "Stop (s)": st.column_config.NumberColumn("Stop (s)", help="Total time from pit entry to pit exit, in seconds."),
                    "Compound": st.column_config.TextColumn("Compound", help="Tyre compound fitted during this stop."),
                    "Tyre Age": st.column_config.NumberColumn("Tyre Age", help="Number of laps already on the outgoing tyre set before this stop."),
                    "Gap Behind (s)": st.column_config.NumberColumn("Gap Behind (s)", help="Gap to the car directly behind at pit entry, in seconds. This is the gap the crew is racing against."),
                    "Gap Source": st.column_config.TextColumn("Gap Source", help="Measured = read directly from the car behind (86% of stops). Estimated = driver's own interval used instead. No data = unavailable."),
                    "Risk": st.column_config.TextColumn("Risk", help="SAFE = net > 5s. MARGINAL = net 0–5s. RISKY = gap < total cost but ≥50% coverage. CRITICAL = gap < 50% of total cost. Formula: net = gap − (stop + circuit_extra)."),
                },
                use_container_width=True,
                hide_index=True,
            )


# ── Tab 3: Costliest Stops ────────────────────────────────────────────────────

with tab3:
    st.header("Costliest Pit Stops")

    if outcomes.empty:
        st.info("No position outcome data. Run `python analyzer.py` first.")
    else:
        _sort_col = "delta_settled" if "delta_settled" in outcomes.columns else "position_delta"
        _merge_cols = ["session_key", "driver_number", "lap_number"]
        _extra = [c for c in ["risk_score", "compound", "radio_url", "gap_at_entry"] if c in risk.columns]

        # Season baseline: expected delta_settled per risk level across ALL stops
        # Used by cost_score = delta_settled - expected_delta[risk_score]
        if not risk.empty and "delta_settled" in outcomes.columns:
            _all_merged = outcomes.merge(risk[_merge_cols + _extra], on=_merge_cols, how="left")
            _expected_by_risk = _all_merged.groupby("risk_score")["delta_settled"].mean()
        else:
            _expected_by_risk = pd.Series(dtype=float)

        worst = outcomes[outcomes[_sort_col].fillna(0) > 0].sort_values(_sort_col, ascending=False)
        best = outcomes[outcomes[_sort_col].fillna(0) < 0].sort_values(_sort_col)

        if not risk.empty:
            worst = worst.merge(risk[_merge_cols + _extra], on=_merge_cols, how="left")

        # Cost Score: how much worse was this stop than the season average for its risk level?
        # Positive = unusually costly. Negative = recovered better than expected.
        if "delta_settled" in worst.columns and "risk_score" in worst.columns and not _expected_by_risk.empty:
            worst["cost_score"] = worst.apply(
                lambda r: round(float(r["delta_settled"]) - float(_expected_by_risk.get(r["risk_score"], 0)), 2)
                if pd.notna(r.get("delta_settled")) and pd.notna(r.get("risk_score")) else None,
                axis=1,
            )
            worst = worst.sort_values("cost_score", ascending=False, na_position="last")

        most_dangerous_team = (
            risk[risk["risk_score"].isin(["RISKY", "CRITICAL"])]["team_name"].value_counts().idxmax()
            if not risk.empty and risk["risk_score"].isin(["RISKY", "CRITICAL"]).any()
            else "N/A"
        )
        safe_rate = (
            f"{(risk['risk_score'] == 'SAFE').mean() * 100:.1f}%"
            if not risk.empty
            else "N/A"
        )
        avg_stop = f"{outcomes['pit_duration'].median():.2f}s" if not outcomes.empty else "N/A"

        col1, col2, col3 = st.columns(3)
        col1.metric("Most Dangerous Team", most_dangerous_team)
        col2.metric("Safe Stop Rate", safe_rate)
        col3.metric("Median Stop Duration", avg_stop)


        st.subheader("Top 10 — Most Positions Lost")

        with st.expander("Column guide ℹ️"):
            st.markdown(
                "| Column | What it shows |\n"
                "|---|---|\n"
                "| **#** | Rank by Cost Score — the stop that deviated most from expectation is #1 |\n"
                "| **Driver · Team** | Driver acronym, team name, and timing window risk badge (🔴 CRITICAL · 🟠 RISKY · 🟡 MARGINAL · 🟢 SAFE) |\n"
                "| **Race · Lap** | Circuit and lap number when the car entered the pit lane |\n"
                "| **Stop · Compound** | Pit stop duration in seconds, and the tyre compound fitted |\n"
                "| **Pos Before** | Race position ~60s before pit entry — stable reference |\n"
                "| **Δ Imm.** | Position change immediately after pit exit — always a loss (normal pit lane effect, not the outcome) |\n"
                "| **Δ Settled** | Net positions lost ~3 laps after pit exit — the real outcome. Positive = fell back |\n"
                "| **Cost Score** | `Δ Settled − expected_Δ[risk level]`. Measures how much worse this stop was vs the season average for its timing window. Higher = more costly than expected. |\n"
            )

        top10_worst = worst.head(10)

        _RANK_BADGE = {1: "🥇", 2: "🥈", 3: "🥉"}
        _RISK_DOT = {"CRITICAL": "🔴", "RISKY": "🟠", "MARGINAL": "🟡", "SAFE": "🟢", "UNKNOWN": "⚪"}
        _hR, _hI, _hD, _hC, _hS, _hX, _hDi, _hDs, _hCs = st.columns([0.35, 0.55, 2.0, 1.5, 1.1, 0.8, 0.8, 0.9, 1.0])
        _hD.markdown("**Driver · Team**")
        _hC.markdown("**Race · Lap**")
        _hS.markdown("**Stop · Compound**")
        _hX.markdown("**Pos Before**")
        _hDi.markdown("**Δ Imm.**")
        _hDs.markdown("**Δ Settled**")
        _hCs.markdown("**Cost Score**")
        st.divider()

        for _rank, (_, row) in enumerate(top10_worst.iterrows(), 1):
            cR, cI, cD, cC, cS, cX, cDi, cDs, cCs = st.columns([0.35, 0.55, 2.0, 1.5, 1.1, 0.8, 0.8, 0.9, 1.0])
            with cR:
                st.markdown(_RANK_BADGE.get(_rank, f"**#{_rank}**"))
            with cI:
                _shot = HEADSHOT_MAP.get(int(row["driver_number"])) if pd.notna(row.get("driver_number")) else None
                if _shot:
                    st.image(_shot, width=55)
            with cD:
                _risk_dot = _RISK_DOT.get(row.get("risk_score", ""), "")
                st.markdown(f"**{row['driver_acronym']}** {_risk_dot}  \n{row['team_name']}")
            with cC:
                st.markdown(f"{row['circuit']}  \nLap {int(row['lap_number'])}")
            with cS:
                _cmp = row.get("compound")
                _cmp_str = f"  \n{_cmp}" if pd.notna(_cmp) else ""
                st.markdown(f"**{row['pit_duration']}s**{_cmp_str}")
            with cX:
                st.markdown(str(int(row["position_before"])) if pd.notna(row.get("position_before")) else "—")
            with cDi:
                _di = row.get("position_delta")
                st.markdown(f"+{int(_di)}" if pd.notna(_di) else "—")
            with cDs:
                _ds = row.get("delta_settled")
                st.markdown(f"**+{int(_ds)}**" if pd.notna(_ds) else "—")
            with cCs:
                _cs = row.get("cost_score")
                st.markdown(f"**{_cs:+.2f}**" if pd.notna(_cs) else "—")
            st.divider()

        # Radio player for worst stops
        if "radio_url" in worst.columns:
            radio_worst = top10_worst[top10_worst["radio_url"].notna()]
            if not radio_worst.empty:
                st.subheader("Nearest radio clip — may not be about the stop")
                rows_radio = list(radio_worst.iterrows())
                for i in range(0, len(rows_radio), 3):
                    chunk = rows_radio[i:i+3]
                    cols = st.columns(len(chunk))
                    for col, (_, row) in zip(cols, chunk):
                        with col:
                            shot_url = HEADSHOT_MAP.get(int(row["driver_number"])) if pd.notna(row.get("driver_number")) else None
                            if shot_url:
                                st.image(shot_url, width=80)
                            net = (
                                round(row["gap_at_entry"] - (row["pit_duration"] + 20), 1)
                                if pd.notna(row.get("gap_at_entry")) else None
                            )
                            compound_str = f" · {row['compound']}" if pd.notna(row.get("compound")) else ""
                            direction = "behind" if net is not None and net <= 0 else "ahead"
                            net_str = f"Net: **{net:+.1f}s** — emerged {direction}" if net is not None else "Net: N/A"
                            st.markdown(
                                f"**{row['driver_acronym']}** · {row['team_name']}\n\n"
                                f"{row['circuit']} · Lap {int(row['lap_number'])}{compound_str}\n\n"
                                f"+{int(row.get('delta_settled', row['position_delta']))} pos lost (settled)\n\n"
                                f"{net_str}"
                            )
                            st.audio(row["radio_url"])

        if not best.empty:
            st.subheader("Top 10 — Most Positions Gained")
            best_base = ["circuit", "driver_acronym", "team_name", "lap_number", "pit_duration",
                         "position_before", "position_after", "position_delta"]
            if "position_settled" in best.columns:
                best_base += ["position_settled", "delta_settled"]
            if "final_position" in best.columns:
                best_base.append("final_position")
            st.dataframe(
                best.head(10)[best_base]
                .rename(columns={
                    "circuit": "Race",
                    "driver_acronym": "Driver",
                    "team_name": "Team",
                    "lap_number": "Lap",
                    "pit_duration": "Stop (s)",
                    "position_before": "Pos Before",
                    "position_after": "Pos After (pit exit)",
                    "position_delta": "Δ Immediate",
                    "position_settled": "Pos Settled (~3 laps)",
                    "delta_settled": "Δ Settled",
                    "final_position": "Final Pos",
                }),
                column_config={
                    "Race": st.column_config.TextColumn("Race", help="Circuit name for this event."),
                    "Driver": st.column_config.TextColumn("Driver", help="Driver's 3-letter FIA identifier."),
                    "Team": st.column_config.TextColumn("Team", help="F1 constructor name."),
                    "Lap": st.column_config.NumberColumn("Lap", help="Lap number when the car entered the pit lane."),
                    "Stop (s)": st.column_config.NumberColumn("Stop (s)", help="Total time from pit entry to pit exit, in seconds."),
                    "Pos Before": st.column_config.NumberColumn("Pos Before", help="Race position recorded ~60s before pit entry — stable reference, avoids in-lap noise."),
                    "Pos After (pit exit)": st.column_config.NumberColumn("Pos After (pit exit)", help="First position reading after pit exit — includes all cars that passed during the stop."),
                    "Δ Immediate": st.column_config.NumberColumn("Δ Immediate", help="Position change immediately after pit exit. Almost always shows a loss because rivals are still on track — this is the normal pit lane effect, not an outcome metric."),
                    "Pos Settled (~3 laps)": st.column_config.NumberColumn("Pos Settled (~3 laps)", help="Race position ~270s after pit exit (~3 laps). Traffic cleared, tyre advantage starts to show. This is the real measurement window."),
                    "Δ Settled": st.column_config.NumberColumn("Δ Settled", help="Net positions gained or lost ~3 laps after the stop. Negative = gained places (successful undercut or overcut). This is the outcome metric."),
                    "Final Pos": st.column_config.NumberColumn("Final Pos", help="Driver's final race position — last position reading of the session. Shows whether the gain from this stop held to the chequered flag."),
                },
                use_container_width=True,
                hide_index=True,
            )


# ── Tab 4: How to Read This ───────────────────────────────────────────────────

with tab4:
    st.header("How to Read This Dashboard")
    st.caption("A quick guide to what every number and chart actually means.")

    st.subheader("The Core Question")
    st.markdown(
        "Every pit stop decision boils down to one number: "
        "**did the gap to the car behind cover the total time lost in the pit lane?** "
        "This dashboard computes that number for every stop across the season and scores it."
    )

    st.code("net = gap_to_car_behind − (stop_duration + circuit_extra)", language=None)

    st.markdown(
        "**stop_duration** (from OpenF1) is the full pit lane time — entry to exit. "
        "**circuit_extra** is a small per-circuit penalty (2–5s) for in/out-lap speed loss "
        "that isn't captured in the measured stop. Monaco adds ~4s; Spa adds ~1.5s.\n\n"
        "A positive net means the car emerged ahead. A negative net means it emerged behind — "
        "even if it looked fine on TV, because the car behind may also pit next lap."
    )

    st.divider()

    st.subheader("Risk Score")
    st.markdown("Each stop is scored into one of five categories based on the net gap:")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.success("SAFE")
        st.markdown("net > +5s — emerged ahead with a comfortable margin. The crew had room to work.")
    with col2:
        st.warning("MARGINAL")
        st.markdown("0 < net ≤ 5s — emerged ahead, razor-thin. Any hesitation would have cost position.")
    with col3:
        st.markdown("🟠 **RISKY**")
        st.markdown("net ≤ 0, but gap covered ≥50% of total cost. The window was close — rival likely pits to neutralise.")
    with col4:
        st.error("CRITICAL")
        st.markdown("net ≤ 0 AND gap < 50% of total cost. The gap was nowhere near sufficient. "
                    "Position loss is likely even if rival pits.")
    with col5:
        st.info("UNKNOWN")
        st.markdown("No interval data. Score cannot be computed (race leader, or data missing).")

    st.info(
        "**Why do most stops score RISKY or CRITICAL?** "
        "F1 strategy is built on the expectation that rivals will also pit. "
        "This dashboard scores each window in isolation: if the rival stays out, does the gap hold? "
        "For most stops it doesn't — but CRITICAL means the gap was genuinely unworkable, "
        "not just a normal strategic gamble.",
        icon="ℹ️",
    )

    st.divider()

    st.subheader("How the Gap Is Measured")
    st.markdown(
        "At pit entry, the tool finds the car **directly behind** in the race order and reads "
        "its interval — the gap from that car to the pitting driver. That is the gap the crew is racing against.\n\n"
        "**Gap Source** in the table:\n"
        "- **Measured** — read from the car directly behind (~86% of stops)\n"
        "- **Estimated** — used the pitting driver's own interval "
        "(race leaders and last-place drivers have no car directly behind/ahead)"
    )

    st.divider()

    st.subheader("How Position Delta Is Measured")
    st.markdown(
        "Most tools measure position change from the lap before pitting to the lap after. "
        "That produces misleading numbers — the first position reading after pit **entry** captures the driver "
        "still physically in the pit lane, so every stop looks like a catastrophic loss.\n\n"
        "This dashboard uses two windows anchored to **pit exit**, not pit entry:"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Pos Before**")
        st.markdown(
            "Race position recorded at least **60 seconds before pit entry**. "
            "This avoids reading position mid-braking zone or on the pit straight, "
            "which can pick up intermediate position swaps that don't reflect the true race order."
        )
        st.markdown("**Δ Immediate** (informational)")
        st.markdown(
            "First position reading after the car **exits** the pit lane. "
            "Almost always shows a position loss — rivals are still on-track on old tyres. "
            "This is the hole the undercut creates, not the outcome. Don't use this as the success metric."
        )
    with col_b:
        st.markdown("**Pos Settled (~3 laps)**")
        st.markdown(
            "Race position approximately **270 seconds** (~3 laps at 90s avg lap) after pit exit. "
            "By this point: traffic from the stop has cleared, rivals have either responded or stayed out, "
            "and the tyre pace advantage has started to register. "
            "This is the established F1 analytics measurement window."
        )
        st.markdown("**Δ Settled** (outcome metric)")
        st.markdown(
            "Net positions gained or lost at the settled window. "
            "**Positive = net loss** (stop went wrong). **Negative = net gain** (successful undercut). "
            "All tables are sorted by this column."
        )

    st.info(
        "**Why these two numbers together?** Δ Immediate shows the hole every stop creates — "
        "it's always big and almost never predicts the outcome. Δ Settled shows what actually happened. "
        "A stop with Δ Immediate = +12 and Δ Settled = −2 is a textbook undercut.",
        icon="ℹ️",
    )

    st.divider()

    st.subheader("Tab Guide")

    st.markdown("**Team Comparison**")
    st.markdown(
        "- Bar chart shows median stop duration per team — lower is faster.\n"
        "- Box plot shows consistency — a narrow box means the crew is reliable. "
        "Stops over 120s are excluded (red flag / drive-through events).\n"
        "- Slow Stop Rate counts stops over 30 seconds total as a percentage of all stops.\n"
        "- Compound chart shows which tire types each team pits for most often."
    )

    st.markdown("**Race Timeline**")
    st.markdown(
        "- Each dot is one pit stop. X axis is lap number, Y axis is stop duration in seconds.\n"
        "- Color by Risk to spot dangerous windows. Color by Compound to read tire strategy.\n"
        "- Hover over any dot to see driver, team, compound, tyre age at entry, gap, and risk score.\n"
        "- Weather annotations on the chart show rainfall detection and average track temperature.\n"
        "- Audio clips below the chart are the nearest radio message within 2 minutes of a dangerous stop — "
        "they may not be about the stop itself."
    )

    st.markdown("**Costliest Stops**")
    st.markdown(
        "- **Δ Immediate** shows the position change right after pit exit — this is almost always "
        "positive because rivals are still on track. It is the normal pit lane effect, not an outcome.\n"
        "- **Δ Settled** is the actual outcome: race position ~3 laps after pit exit. Positive = net loss.\n"
        "- **Cost Score** is the key ranking metric:"
    )
    st.code("cost_score = Δ Settled − expected_Δ_Settled[risk_level]", language=None)
    st.markdown(
        "The expected delta is the season average for each risk level. "
        "A DANGEROUS stop is already expected to lose ~1–2 positions — the undercut normally recovers. "
        "Cost Score measures the *surprise*: how much worse was this stop vs what normally happens "
        "at that timing window? A stop scoring **+10** means 10 more positions were lost than the "
        "season average for DANGEROUS stops — that's the stop the strategy team got truly wrong.\n\n"
        "Positive = unusually costly. Negative = recovered better than expected (good undercut).\n\n"
        "- Metric cards at the top summarize the season."
    )

    st.divider()

    st.subheader("Key Numbers to Know")
    st.markdown(
        "- Total pit lane time (entry to exit) is typically **22–25 seconds** in modern F1.\n"
        "- A stop over **30 seconds** is considered slow — usually a mechanical issue or traffic hold.\n"
        "- The pit lane traverse estimate used in scoring is **20 seconds** (constant). "
        "It varies by circuit — Monaco is longer, Bahrain shorter.\n"
        "- **Medium compound** accounts for ~49% of all pit stops in 2023–2024. "
        "Most undercut strategies run on mediums.\n"
        "- Stops over **120 seconds** are excluded from the distribution chart — "
        "these are red flag periods or drive-through penalties, not crew performance."
    )

    st.divider()
    st.caption("Data source: OpenF1 API (openf1.org) · Free, no API key required · 2023–2024 seasons")

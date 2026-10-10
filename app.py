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

RISK_COLOR = {"SAFE": "#00C851", "MARGINAL": "#FFBB33", "DANGEROUS": "#FF4444", "UNKNOWN": "#AAAAAA"}
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
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    pit = pd.read_csv(pit_path)
    risk_path = DATA_DIR / f"risk_scores_{year}.csv"
    risk = pd.read_csv(risk_path) if risk_path.exists() else pd.DataFrame()
    outcomes_path = DATA_DIR / f"stop_outcomes_{year}.csv"
    outcomes = pd.read_csv(outcomes_path) if outcomes_path.exists() else pd.DataFrame()
    sessions_path = DATA_DIR / f"sessions_{year}.csv"
    sessions = pd.read_csv(sessions_path) if sessions_path.exists() else pd.DataFrame()
    return pit, risk, outcomes, sessions


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
pit, risk, outcomes, sessions = load_year_data(year)

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

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["Team Comparison", "Race Timeline", "Costliest Stops"])


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
                color="median",
                color_continuous_scale="RdYlGn_r",
                labels={"team_name": "Team", "median": "Median Stop (s)"},
                title=f"Median Pit Stop Duration — {year}",
            )
            fig_bar.update_layout(coloraxis_showscale=False, xaxis_tickangle=-30)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            pit_clean = pit[pit["pit_duration"].notna() & (pit["pit_duration"] > 0)]
            fig_box = px.box(
                pit_clean,
                x="team_name",
                y="pit_duration",
                color="team_name",
                labels={"team_name": "Team", "pit_duration": "Stop Duration (s)"},
                title=f"Stop Duration Distribution — {year}",
            )
            fig_box.update_layout(showlegend=False, xaxis_tickangle=-30)
            st.plotly_chart(fig_box, use_container_width=True)

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

            if color_by == "Risk":
                for score, group in race_risk.groupby("risk_score"):
                    fig.add_trace(go.Scatter(
                        x=group["lap_number"],
                        y=group["pit_duration"],
                        mode="markers",
                        marker=dict(size=12, color=RISK_COLOR.get(score, "#AAAAAA")),
                        name=score,
                        text=group.apply(
                            lambda r: (
                                f"{r['driver_acronym']} ({r['team_name']})<br>"
                                f"Lap {r['lap_number']} — {r['pit_duration']}s<br>"
                                f"Compound: {r.get('compound', 'N/A')}<br>"
                                f"Gap (car behind): {r['gap_at_entry']}s "
                                f"[{r.get('gap_method', '?')}]<br>"
                                f"Risk: {r['risk_score']}"
                            ),
                            axis=1,
                        ),
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
                        text=group.apply(
                            lambda r: (
                                f"{r['driver_acronym']} ({r['team_name']})<br>"
                                f"Lap {r['lap_number']} — {r['pit_duration']}s<br>"
                                f"Compound: {r.get('compound', 'N/A')}<br>"
                                f"Gap (car behind): {r['gap_at_entry']}s "
                                f"[{r.get('gap_method', '?')}]<br>"
                                f"Risk: {r['risk_score']}"
                            ),
                            axis=1,
                        ),
                        hoverinfo="text",
                    ))

            fig.update_layout(
                title=f"{selected_circuit} — Pit Stops by Lap",
                xaxis_title="Lap Number",
                yaxis_title="Stop Duration (s)",
                legend_title=color_by,
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Stops", len(race_risk))
            col2.metric("Dangerous", int((race_risk["risk_score"] == "DANGEROUS").sum()))
            col3.metric("Marginal", int((race_risk["risk_score"] == "MARGINAL").sum()))

            # Dangerous stops with radio
            dangerous = race_risk[race_risk["risk_score"] == "DANGEROUS"]
            if not dangerous.empty and "radio_url" in dangerous.columns:
                radio_stops = dangerous[dangerous["radio_url"].notna()]
                if not radio_stops.empty:
                    st.subheader("Team Radio — Dangerous Stops")
                    for _, row in radio_stops.iterrows():
                        st.markdown(
                            f"**{row['driver_acronym']}** ({row['team_name']}) — "
                            f"Lap {row['lap_number']}, {row['pit_duration']}s stop"
                        )
                        st.audio(row["radio_url"])

            detail_cols = ["driver_acronym", "team_name", "lap_number", "pit_duration", "gap_at_entry", "gap_method", "risk_score"]
            if "compound" in race_risk.columns:
                detail_cols.insert(4, "compound")
            st.dataframe(
                race_risk[detail_cols]
                .rename(columns={
                    "driver_acronym": "Driver",
                    "team_name": "Team",
                    "lap_number": "Lap",
                    "pit_duration": "Stop (s)",
                    "compound": "Compound",
                    "gap_at_entry": "Gap Behind (s)",
                    "gap_method": "Gap Source",
                    "risk_score": "Risk",
                })
                .sort_values("Lap"),
                use_container_width=True,
                hide_index=True,
            )


# ── Tab 3: Costliest Stops ────────────────────────────────────────────────────

with tab3:
    st.header("Costliest Pit Stops")

    if outcomes.empty:
        st.info("No position outcome data. Run `python analyzer.py` first.")
    else:
        worst = outcomes[outcomes["position_delta"] > 0].sort_values("position_delta", ascending=False)
        best = outcomes[outcomes["position_delta"] < 0].sort_values("position_delta")

        if not risk.empty:
            merge_cols = ["session_key", "driver_number", "lap_number"]
            extra = [c for c in ["risk_score", "compound", "radio_url"] if c in risk.columns]
            worst = worst.merge(risk[merge_cols + extra], on=merge_cols, how="left")

        most_dangerous_team = (
            risk[risk["risk_score"] == "DANGEROUS"]["team_name"].value_counts().idxmax()
            if not risk.empty and (risk["risk_score"] == "DANGEROUS").any()
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
        display_cols = ["circuit", "driver_acronym", "team_name", "lap_number", "pit_duration", "position_before", "position_after", "position_delta"]
        for extra_col in ["compound", "risk_score"]:
            if extra_col in worst.columns:
                display_cols.append(extra_col)

        st.dataframe(
            worst.head(10)[display_cols].rename(columns={
                "circuit": "Race",
                "driver_acronym": "Driver",
                "team_name": "Team",
                "lap_number": "Lap",
                "pit_duration": "Stop (s)",
                "position_before": "Pos Before",
                "position_after": "Pos After",
                "position_delta": "Δ Positions",
                "compound": "Compound",
                "risk_score": "Risk",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Radio player for worst stops
        if "radio_url" in worst.columns:
            radio_worst = worst.head(10)[worst.head(10)["radio_url"].notna()]
            if not radio_worst.empty:
                st.subheader("Team Radio — Costliest Stops")
                for _, row in radio_worst.iterrows():
                    st.markdown(
                        f"**{row['driver_acronym']}** ({row['team_name']}) — "
                        f"{row['circuit']}, Lap {row['lap_number']}, lost {int(row['position_delta'])} place(s)"
                    )
                    st.audio(row["radio_url"])

        if not best.empty:
            st.subheader("Top 10 — Most Positions Gained")
            st.dataframe(
                best.head(10)[["circuit", "driver_acronym", "team_name", "lap_number", "pit_duration", "position_before", "position_after", "position_delta"]]
                .rename(columns={
                    "circuit": "Race",
                    "driver_acronym": "Driver",
                    "team_name": "Team",
                    "lap_number": "Lap",
                    "pit_duration": "Stop (s)",
                    "position_before": "Pos Before",
                    "position_after": "Pos After",
                    "position_delta": "Δ Positions",
                }),
                use_container_width=True,
                hide_index=True,
            )

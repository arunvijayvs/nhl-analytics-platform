"""
NHL Analytics Hub — Streamlit Dashboard
Run locally with:  streamlit run app.py

Expects nhl_hockey.db (built by the notebooks/ pipeline) to sit in ./data/
"""

import sqlite3
import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu


from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "data" / "nhl_hockey.db"
QUERIES_PATH = PROJECT_DIR / "app" / "queries.sql"



def load_prebuilt_queries():
    """
    Load named SELECT queries from app/queries.sql.

    Queries are identified by comments such as:
        -- Q1: Top 10 teams by goals

    Returns:
        dict[str, str]: Query label -> SQL statement
    """
    if not QUERIES_PATH.exists():
        st.error(f"queries.sql not found: {QUERIES_PATH}")
        return {}

    try:
        sql_text = QUERIES_PATH.read_text(encoding="utf-8")
    except Exception as e:
        st.error(f"Could not read queries.sql: {e}")
        return {}

    import re

    sections = re.split(r"(?=-- Q\d+:)", sql_text)

    queries = {}

    for section in sections:
        section = section.strip()

        if not section.startswith("-- Q"):
            continue

        lines = section.splitlines()

        # First line contains the query name.
        title = lines[0].strip()[3:].strip()

        # Remove SQL comments from the query body.
        sql_lines = [
            line
            for line in lines[1:]
            if not line.strip().startswith("--")
        ]

        sql = "\n".join(sql_lines).strip()

        if sql:
            queries[title] = sql

    return queries
PREBUILT = load_prebuilt_queries()
st.set_page_config(page_title="NHL Analytics Hub", page_icon="🏒", layout="wide")


# ---------------------------------------------------------------- db helpers

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def run_query(sql, params=None):
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    except Exception as e:
        st.error(f"SQL error: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------- sidebar nav

with st.sidebar:
    page = option_menu(
        "NHL Analytics Hub",
        ["Home", "Standings", "Team Info", "Player Search", "Game Results", "Leaderboards", "SQL Query"],
        icons=["house", "list-ol", "shield", "person-badge", "calendar3", "trophy", "code-slash"],
        menu_icon="hockey-puck",
        default_index=0,
    )

GAME_STATE_LABELS = {"OFF": "Final", "FUT": "Upcoming", "LIVE": "In Progress"}


# ================================================================== HOME
if page == "Home":
    st.title("🏒 NHL Analytics Hub")
    st.caption("Season snapshot, built from the NHL public API.")

    teams_n = run_query("SELECT COUNT(*) AS n FROM teams").iloc[0]["n"]
    players_n = run_query("SELECT COUNT(*) AS n FROM players").iloc[0]["n"]
    games_n = run_query("SELECT COUNT(*) AS n FROM games").iloc[0]["n"]
    goals_n = run_query("SELECT SUM(goals_for) AS n FROM standings").iloc[0]["n"]

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in zip(
        [c1, c2, c3, c4],
        ["Teams", "Players", "Games", "Total Goals This Season"],
        [teams_n, players_n, games_n, goals_n],
    ):
        with col:
            with st.container(border=True):
                st.metric(label, f"{int(value):,}" if pd.notna(value) else "—")

    st.divider()

    top_scorer = run_query(
        """
        SELECT p.first_name || ' ' || p.last_name AS player, t.team_name, ss.points
        FROM skater_season_stats ss
        JOIN players p ON p.player_id = ss.player_id
        JOIN teams t ON t.team_id = ss.team_id
        ORDER BY ss.points DESC LIMIT 1
        """
    )
    best_goalie = run_query(
        """
        SELECT p.first_name || ' ' || p.last_name AS player, t.team_name, gs.save_pct
        FROM goalie_season_stats gs
        JOIN players p ON p.player_id = gs.player_id
        JOIN teams t ON t.team_id = gs.team_id
        WHERE gs.games_played >= 5
        ORDER BY gs.save_pct DESC LIMIT 1
        """
    )
    league_leader = run_query(
        """
        SELECT t.team_name, s.points
        FROM standings s JOIN teams t ON t.team_id = s.team_id
        ORDER BY s.points DESC LIMIT 1
        """
    )

    h1, h2, h3 = st.columns(3)
    with h1:
        if not top_scorer.empty:
            r = top_scorer.iloc[0]
            st.info(f"**Top scorer:** {r['player']} ({r['team_name']}) — {int(r['points'])} pts")
    with h2:
        if not best_goalie.empty:
            r = best_goalie.iloc[0]
            st.info(f"**Best save %:** {r['player']} ({r['team_name']}) — {r['save_pct']:.3f}")
    with h3:
        if not league_leader.empty:
            r = league_leader.iloc[0]
            st.info(f"**League leader:** {r['team_name']} — {int(r['points'])} pts")

    st.subheader("Points by team")
    chart_df = run_query(
        """
        SELECT t.team_name, s.points
        FROM standings s JOIN teams t ON t.team_id = s.team_id
        ORDER BY s.points DESC
        """
    )
    if not chart_df.empty:
        st.bar_chart(chart_df.set_index("team_name"))


# ================================================================== STANDINGS
elif page == "Standings":
    st.title("League Standings")

    conferences = ["All"] + sorted(
        run_query("SELECT DISTINCT conference_name FROM teams WHERE conference_name IS NOT NULL")["conference_name"].tolist()
    )
    divisions = ["All"] + sorted(
        run_query("SELECT DISTINCT division_name FROM teams WHERE division_name IS NOT NULL")["division_name"].tolist()
    )

    c1, c2 = st.columns(2)
    conf_choice = c1.selectbox("Conference", conferences)
    div_choice = c2.selectbox("Division", divisions)

    sql = """
        SELECT t.logo_url, t.team_name, t.conference_name, t.division_name,
               s.games_played, s.wins, s.losses, s.ot_losses, s.points,
               s.goals_for, s.goals_against, s.streak_type, s.streak_count
        FROM standings s
        JOIN teams t ON t.team_id = s.team_id
        WHERE 1=1
    """
    params = []
    if conf_choice != "All":
        sql += " AND t.conference_name = ?"
        params.append(conf_choice)
    if div_choice != "All":
        sql += " AND t.division_name = ?"
        params.append(div_choice)
    sql += " ORDER BY s.points DESC"

    df = run_query(sql, params=params)
    st.dataframe(
        df,
        column_config={"logo_url": st.column_config.ImageColumn("Logo", width="small")},
        hide_index=True,
        use_container_width=True,
    )


# ================================================================== TEAM INFO
elif page == "Team Info":
    st.title("Team Info")

    teams_df = run_query("SELECT team_id, team_name, team_abbrev FROM teams ORDER BY team_name")
    if teams_df.empty:
        st.warning("No teams loaded yet — run the data pipeline notebooks first.")
    else:
        team_name = st.selectbox("Choose a team", teams_df["team_name"])
        team_row = teams_df[teams_df["team_name"] == team_name].iloc[0]
        team_id = int(team_row["team_id"])

        info = run_query("SELECT * FROM teams WHERE team_id = ?", params=[team_id]).iloc[0]
        standing = run_query("SELECT * FROM standings WHERE team_id = ?", params=[team_id])

        c1, c2 = st.columns([1, 3])
        with c1:
            if info["logo_url"]:
                st.image(info["logo_url"], width=140)
        with c2:
            st.subheader(info["team_name"])
            st.write(f"**Conference:** {info['conference_name']}  |  **Division:** {info['division_name']}")
            if not standing.empty:
                s = standing.iloc[0]
                m1, m2, m3 = st.columns(3)
                m1.metric("Points", int(s["points"]))
                m2.metric("Record", f"{int(s['wins'])}-{int(s['losses'])}-{int(s['ot_losses'])}")
                m3.metric("Goal Diff", int(s["goals_for"]) - int(s["goals_against"]))

        st.divider()
        st.subheader("Roster")
        roster = run_query(
            "SELECT first_name, last_name, position, jersey_number, shoots_catches, headshot_url "
            "FROM players WHERE team_id = ? ORDER BY position, last_name",
            params=[team_id],
        )
        for pos, label in [("G", "Goalies"), ("D", "Defensemen"),
                            ("C", "Forwards"), ("LW", None), ("RW", None)]:
            pass  # grouping handled below

        for group_label, positions in [
            ("Forwards", ["C", "LW", "RW"]),
            ("Defensemen", ["D"]),
            ("Goalies", ["G"]),
        ]:
            group_df = roster[roster["position"].isin(positions)]
            if group_df.empty:
                continue
            st.markdown(f"**{group_label}**")
            cols = st.columns(4)
            for i, (_, p) in enumerate(group_df.iterrows()):
                with cols[i % 4]:
                    if p["headshot_url"]:
                        st.image(p["headshot_url"], width=90)
                    st.caption(f"#{int(p['jersey_number']) if pd.notna(p['jersey_number']) else '--'} "
                               f"{p['first_name']} {p['last_name']} ({p['position']})")


# ================================================================== PLAYER SEARCH
elif page == "Player Search":
    st.title("Player Search")

    search = st.text_input("Search by name")
    players_df = run_query(
        """
        SELECT p.player_id, p.first_name, p.last_name, t.team_name, p.position, p.headshot_url
        FROM players p JOIN teams t ON t.team_id = p.team_id
        WHERE (p.first_name || ' ' || p.last_name) LIKE ?
        ORDER BY p.last_name
        LIMIT 50
        """,
        params=[f"%{search}%"] if search else ["%"],
    )

    if players_df.empty:
        st.info("No players found.")
    else:
        options = players_df.apply(lambda r: f"{r['first_name']} {r['last_name']} ({r['team_name']})", axis=1)
        choice = st.selectbox("Select a player", options)
        selected = players_df.iloc[options.tolist().index(choice)]
        player_id = int(selected["player_id"])

        c1, c2 = st.columns([1, 3])
        with c1:
            if selected["headshot_url"]:
                st.image(selected["headshot_url"], width=150)
        with c2:
            st.subheader(f"{selected['first_name']} {selected['last_name']}")
            st.write(f"**Team:** {selected['team_name']}  |  **Position:** {selected['position']}")

        if selected["position"] == "G":
            stats = run_query("SELECT * FROM goalie_season_stats WHERE player_id = ?", params=[player_id])
            if not stats.empty:
                s = stats.iloc[0]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Wins", int(s["wins"]))
                m2.metric("Save %", f"{s['save_pct']:.3f}")
                m3.metric("GAA", f"{s['goals_against_avg']:.2f}")
                m4.metric("Shutouts", int(s["shutouts"]))
        else:
            stats = run_query("SELECT * FROM skater_season_stats WHERE player_id = ?", params=[player_id])
            if not stats.empty:
                s = stats.iloc[0]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Goals", int(s["goals"]))
                m2.metric("Assists", int(s["assists"]))
                m3.metric("Points", int(s["points"]))
                m4.metric("+/-", int(s["plus_minus"]))

                game_log = run_query(
                    "SELECT g.game_date, gs.goals, gs.assists, gs.points "
                    "FROM game_stats gs JOIN games g ON g.game_id = gs.game_id "
                    "WHERE gs.player_id = ? ORDER BY g.game_date",
                    params=[player_id],
                )
                if not game_log.empty:
                    st.subheader("Points by game")
                    st.line_chart(game_log.set_index("game_date")[["points"]])


# ================================================================== GAME RESULTS
elif page == "Game Results":
    st.title("Game Results")

    teams_df = run_query("SELECT team_id, team_name FROM teams ORDER BY team_name")
    c1, c2, c3 = st.columns(3)
    team_choice = c1.selectbox("Team", ["All"] + teams_df["team_name"].tolist())
    state_choice = c2.selectbox("Status", ["All", "Final", "Upcoming", "In Progress"])
    date_choice = c3.date_input("Game date", value=None)

    sql = """
        SELECT g.game_date, ht.team_name AS home, g.home_score,
               at.team_name AS away, g.away_score, g.game_state, g.venue_name
        FROM games g
        JOIN teams ht ON ht.team_id = g.home_team_id
        JOIN teams at ON at.team_id = g.away_team_id
        WHERE 1=1
    """
    params = []
    if team_choice != "All":
        sql += " AND (ht.team_name = ? OR at.team_name = ?)"
        params += [team_choice, team_choice]
    if state_choice != "All":
        reverse = {v: k for k, v in GAME_STATE_LABELS.items()}
        sql += " AND g.game_state = ?"
        params.append(reverse[state_choice])
    if date_choice:
        sql += " AND g.game_date = ?"
        params.append(str(date_choice))
    sql += " ORDER BY g.game_date DESC"

    df = run_query(sql, params=params)
    if not df.empty:
        df["game_state"] = df["game_state"].map(GAME_STATE_LABELS).fillna(df["game_state"])
    st.dataframe(df, hide_index=True, use_container_width=True)


# ================================================================== LEADERBOARDS
elif page == "Leaderboards":
    st.title("Leaderboards")

    tabs = st.tabs(["Top Scorers", "Most Penalty Minutes", "Best Save %", "Most Wins (Goalie)"])

    with tabs[0]:
        st.dataframe(run_query(
            """
            SELECT p.first_name || ' ' || p.last_name AS player, t.team_name, ss.points
            FROM skater_season_stats ss
            JOIN players p ON p.player_id = ss.player_id
            JOIN teams t ON t.team_id = ss.team_id
            ORDER BY ss.points DESC LIMIT 15
            """), hide_index=True, use_container_width=True)

    with tabs[1]:
        st.dataframe(run_query(
            """
            SELECT p.first_name || ' ' || p.last_name AS player, t.team_name, ss.penalty_min
            FROM skater_season_stats ss
            JOIN players p ON p.player_id = ss.player_id
            JOIN teams t ON t.team_id = ss.team_id
            ORDER BY ss.penalty_min DESC LIMIT 15
            """), hide_index=True, use_container_width=True)

    with tabs[2]:
        st.dataframe(run_query(
            """
            SELECT p.first_name || ' ' || p.last_name AS player, t.team_name, gs.save_pct, gs.games_played
            FROM goalie_season_stats gs
            JOIN players p ON p.player_id = gs.player_id
            JOIN teams t ON t.team_id = gs.team_id
            WHERE gs.games_played >= 10
            ORDER BY gs.save_pct DESC LIMIT 15
            """), hide_index=True, use_container_width=True)

    with tabs[3]:
        st.dataframe(run_query(
            """
            SELECT p.first_name || ' ' || p.last_name AS player, t.team_name, gs.wins
            FROM goalie_season_stats gs
            JOIN players p ON p.player_id = gs.player_id
            JOIN teams t ON t.team_id = gs.team_id
            ORDER BY gs.wins DESC LIMIT 15
            """), hide_index=True, use_container_width=True)

# ================================================================== SQL QUERY
elif page == "SQL Query":
    st.title("SQL Query")
    st.caption("Run read-only SELECT queries against the NHL Analytics Hub database.")

    query_options = ["-- write your own --"] + list(PREBUILT.keys())

    choice = st.selectbox(
        "Start from a pre-built query (optional)",
        query_options,
    )

    if choice == "-- write your own --":
        default_sql = "SELECT * FROM teams LIMIT 10;"
    else:
        default_sql = PREBUILT[choice]

    query = st.text_area(
        "SQL query",
        value=default_sql,
        height=220,
    )

    if st.button("Run query", type="primary"):
        cleaned_query = query.strip()

        if not cleaned_query:
            st.error("Please enter a SQL query.")
        else:
            normalized_query = cleaned_query.lower().lstrip()

            blocked_keywords = (
                "insert",
                "update",
                "delete",
                "drop",
                "alter",
                "create",
                "replace",
                "attach",
                "detach",
                "pragma",
            )

            is_read_only = (
                normalized_query.startswith("select")
                or normalized_query.startswith("with")
            )

            contains_write_operation = any(
                normalized_query.startswith(keyword)
                or f" {keyword} " in normalized_query
                or f"\n{keyword} " in normalized_query
                for keyword in blocked_keywords
            )

            if not is_read_only or contains_write_operation:
                st.error("Only read-only SELECT queries are allowed here.")
            else:
                result = run_query(cleaned_query)

                if not result.empty:
                    st.success(f"{len(result)} rows returned")
                    st.dataframe(
                        result,
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.warning(
                        "Query ran but returned no rows "
                        "(or an error was shown above)."
                    )

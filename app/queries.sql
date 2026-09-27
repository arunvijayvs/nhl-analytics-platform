-- NHL Analytics Hub — SQL Analysis Queries
-- Validated against the current NHL Analytics Hub SQLite database.
--
-- Purpose:
--   1. Store reusable SQL queries for the Streamlit dashboard.
--   2. Keep validated analytical SQL separate from app.py.
--   3. Serve as a clean reference for the project's SQL analytics layer.
--
-- Database:
--   SQLite
--
-- Current season:
--   20252026
--
-- Tables used:
--   teams
--   standings
--   players
--   games
--   game_stats
--   skater_season_stats
--   goalie_season_stats


-- ================================================================
-- TEAM ANALYTICS
-- ================================================================


-- Q1: Top 10 teams by goals
SELECT
    t.team_name,
    s.goals_for
FROM standings s
JOIN teams t
    ON t.team_id = s.team_id
ORDER BY s.goals_for DESC
LIMIT 10;


-- Q4: Teams above league-average points
SELECT
    t.team_name,
    s.points
FROM standings s
JOIN teams t
    ON t.team_id = s.team_id
WHERE s.points > (
    SELECT AVG(points)
    FROM standings
)
ORDER BY s.points DESC;


-- Q5: Divisions averaging above 90 points
SELECT
    t.division_name,
    ROUND(AVG(s.points), 2) AS avg_points
FROM standings s
JOIN teams t
    ON t.team_id = s.team_id
GROUP BY t.division_name
HAVING AVG(s.points) > 90
ORDER BY avg_points DESC;


-- Q8: Home vs away win difference
SELECT
    t.team_name,
    s.home_wins,
    s.away_wins,
    (s.home_wins - s.away_wins) AS home_minus_away
FROM standings s
JOIN teams t
    ON t.team_id = s.team_id
ORDER BY home_minus_away DESC;


-- Q10: Teams whose top scorer exceeds the average
--      top-scorer goal total across teams
SELECT
    t.team_name,
    MAX(ss.goals) AS top_scorer_goals
FROM skater_season_stats ss
JOIN teams t
    ON t.team_id = ss.team_id
GROUP BY t.team_name
HAVING MAX(ss.goals) > (
    SELECT AVG(max_goals)
    FROM (
        SELECT MAX(goals) AS max_goals
        FROM skater_season_stats
        GROUP BY team_id
    )
)
ORDER BY top_scorer_goals DESC;


-- Q11: Teams currently on a winning streak
SELECT
    t.team_name,
    s.streak_type,
    s.streak_count
FROM standings s
JOIN teams t
    ON t.team_id = s.team_id
WHERE s.streak_type = 'W'
ORDER BY s.streak_count DESC;


-- ================================================================
-- PLAYER ANALYTICS
-- ================================================================


-- Q2: Top 5 point scorers
SELECT
    p.first_name,
    p.last_name,
    t.team_name,
    ss.points
FROM skater_season_stats ss
JOIN players p
    ON p.player_id = ss.player_id
JOIN teams t
    ON t.team_id = ss.team_id
ORDER BY ss.points DESC
LIMIT 5;


-- Q3: Players with more than 20 goals and more than 30 assists
SELECT
    p.first_name,
    p.last_name,
    ss.goals,
    ss.assists
FROM skater_season_stats ss
JOIN players p
    ON p.player_id = ss.player_id
WHERE ss.goals > 20
  AND ss.assists > 30
ORDER BY ss.goals DESC;


-- Q6: Top goalies by save percentage,
--     minimum 10 games played
SELECT
    p.first_name,
    p.last_name,
    t.team_name,
    gs.save_pct,
    gs.games_played
FROM goalie_season_stats gs
JOIN players p
    ON p.player_id = gs.player_id
JOIN teams t
    ON t.team_id = gs.team_id
WHERE gs.games_played >= 10
ORDER BY gs.save_pct DESC
LIMIT 10;


-- Q7: Top 10 players by penalty minutes
SELECT
    p.first_name,
    p.last_name,
    t.team_name,
    ss.penalty_min
FROM skater_season_stats ss
JOIN players p
    ON p.player_id = ss.player_id
JOIN teams t
    ON t.team_id = ss.team_id
ORDER BY ss.penalty_min DESC
LIMIT 10;


-- Q9: Average points per game by position
SELECT
    p.position,
    ROUND(
        AVG(
            ss.points * 1.0 /
            NULLIF(ss.games_played, 0)
        ),
        2
    ) AS avg_points_per_game
FROM skater_season_stats ss
JOIN players p
    ON p.player_id = ss.player_id
WHERE ss.games_played > 0
GROUP BY p.position
ORDER BY avg_points_per_game DESC;


-- Q17: Top point scorer from every team
WITH ranked_players AS (
    SELECT
        ss.team_id,
        p.first_name,
        p.last_name,
        t.team_name,
        ss.points,
        ROW_NUMBER() OVER (
            PARTITION BY ss.team_id
            ORDER BY ss.points DESC, p.last_name
        ) AS player_rank
    FROM skater_season_stats ss
    JOIN players p
        ON p.player_id = ss.player_id
    JOIN teams t
        ON t.team_id = ss.team_id
)
SELECT
    team_name,
    first_name,
    last_name,
    points
FROM ranked_players
WHERE player_rank = 1
ORDER BY points DESC;


-- Q22: Top 3 point scorers per team
--
-- RANK() intentionally allows ties to be included.
WITH ranked_players AS (
    SELECT
        ss.team_id,
        t.team_name,
        p.first_name,
        p.last_name,
        ss.points,
        RANK() OVER (
            PARTITION BY ss.team_id
            ORDER BY ss.points DESC
        ) AS team_rank
    FROM skater_season_stats ss
    JOIN players p
        ON p.player_id = ss.player_id
    JOIN teams t
        ON t.team_id = ss.team_id
)
SELECT
    team_name,
    first_name,
    last_name,
    points,
    team_rank
FROM ranked_players
WHERE team_rank <= 3
ORDER BY team_name, team_rank, points DESC;


-- ================================================================
-- GAME ANALYTICS
-- ================================================================


-- Q12: Highest-scoring completed games
SELECT
    g.game_date,
    ht.team_name AS home,
    g.home_score,
    at.team_name AS away,
    g.away_score,
    (g.home_score + g.away_score) AS total_goals
FROM games g
JOIN teams ht
    ON ht.team_id = g.home_team_id
JOIN teams at
    ON at.team_id = g.away_team_id
WHERE g.game_state = 'OFF'
ORDER BY total_goals DESC
LIMIT 10;


-- Q18: Scoring by game type
SELECT
    CASE
        WHEN game_type = 1 THEN 'Preseason'
        WHEN game_type = 2 THEN 'Regular Season'
        WHEN game_type = 3 THEN 'Postseason'
        ELSE 'Other'
    END AS game_type_name,
    COUNT(*) AS games_played,
    SUM(home_score + away_score) AS total_goals,
    ROUND(
        AVG(home_score + away_score),
        2
    ) AS avg_goals_per_game
FROM games
WHERE game_state = 'OFF'
GROUP BY game_type
ORDER BY game_type;


-- Q23: Players with points in both regular season
--      and postseason
SELECT
    p.first_name,
    p.last_name,
    SUM(
        CASE
            WHEN g.game_type = 2 THEN gs.points
            ELSE 0
        END
    ) AS regular_season_points,
    SUM(
        CASE
            WHEN g.game_type = 3 THEN gs.points
            ELSE 0
        END
    ) AS postseason_points
FROM game_stats gs
JOIN games g
    ON g.game_id = gs.game_id
JOIN players p
    ON p.player_id = gs.player_id
WHERE g.game_state = 'OFF'
  AND g.game_type IN (2, 3)
GROUP BY gs.player_id
HAVING
    SUM(
        CASE
            WHEN g.game_type = 2 THEN gs.points
            ELSE 0
        END
    ) > 0
    AND
    SUM(
        CASE
            WHEN g.game_type = 3 THEN gs.points
            ELSE 0
        END
    ) > 0
ORDER BY regular_season_points DESC;


-- ================================================================
-- ADVANCED ANALYTICS
-- ================================================================


-- Q13: Categorize teams by points
SELECT
    t.team_name,
    s.points,
    CASE
        WHEN s.points >= 110 THEN '110+ Points'
        WHEN s.points >= 100 THEN '100-109 Points'
        WHEN s.points >= 90 THEN '90-99 Points'
        ELSE 'Below 90 Points'
    END AS points_category
FROM standings s
JOIN teams t
    ON t.team_id = s.team_id
ORDER BY s.points DESC;


-- Q15: League-wide player ranking by points
SELECT
    p.first_name,
    p.last_name,
    t.team_name,
    ss.points,
    RANK() OVER (
        ORDER BY ss.points DESC
    ) AS points_rank
FROM skater_season_stats ss
JOIN players p
    ON p.player_id = ss.player_id
JOIN teams t
    ON t.team_id = ss.team_id
ORDER BY points_rank
LIMIT 20;


-- Q16: Player ranking by position
SELECT
    p.first_name,
    p.last_name,
    p.position,
    t.team_name,
    ss.points,
    RANK() OVER (
        PARTITION BY p.position
        ORDER BY ss.points DESC
    ) AS position_rank
FROM skater_season_stats ss
JOIN players p
    ON p.player_id = ss.player_id
JOIN teams t
    ON t.team_id = ss.team_id
ORDER BY p.position, position_rank
LIMIT 30;


-- Q20: Top scorer's percentage of team goals
WITH ranked_scorers AS (
    SELECT
        ss.team_id,
        ss.player_id,
        ss.goals,
        ROW_NUMBER() OVER (
            PARTITION BY ss.team_id
            ORDER BY ss.goals DESC, p.last_name
        ) AS scorer_rank
    FROM skater_season_stats ss
    JOIN players p
        ON p.player_id = ss.player_id
),
top_scorers AS (
    SELECT
        team_id,
        player_id,
        goals
    FROM ranked_scorers
    WHERE scorer_rank = 1
)
SELECT
    t.team_name,
    p.first_name,
    p.last_name,
    ts.goals AS top_scorer_goals,
    s.goals_for AS team_goals,
    ROUND(
        ts.goals * 100.0 /
        NULLIF(s.goals_for, 0),
        2
    ) AS percentage_of_team_goals
FROM top_scorers ts
JOIN teams t
    ON t.team_id = ts.team_id
JOIN players p
    ON p.player_id = ts.player_id
JOIN standings s
    ON s.team_id = ts.team_id
ORDER BY percentage_of_team_goals DESC;


-- Q24: Top 3 scorers' share of team goals
--
-- RANK() intentionally includes ties at the third rank.
WITH ranked_scorers AS (
    SELECT
        ss.team_id,
        ss.player_id,
        ss.goals,
        RANK() OVER (
            PARTITION BY ss.team_id
            ORDER BY ss.goals DESC
        ) AS goal_rank
    FROM skater_season_stats ss
),
top_three AS (
    SELECT
        team_id,
        SUM(goals) AS top_three_goals
    FROM ranked_scorers
    WHERE goal_rank <= 3
    GROUP BY team_id
)
SELECT
    t.team_name,
    tt.top_three_goals,
    s.goals_for AS team_goals,
    ROUND(
        tt.top_three_goals * 100.0 /
        NULLIF(s.goals_for, 0),
        2
    ) AS top_three_goal_share_pct
FROM top_three tt
JOIN teams t
    ON t.team_id = tt.team_id
JOIN standings s
    ON s.team_id = tt.team_id
ORDER BY top_three_goal_share_pct DESC;

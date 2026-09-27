CREATE TABLE IF NOT EXISTS teams (
    team_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    team_abbrev     TEXT UNIQUE NOT NULL,
    team_name       TEXT NOT NULL,
    conference_name TEXT,
    division_name   TEXT,
    logo_url        TEXT
);

CREATE TABLE IF NOT EXISTS standings (
    standing_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id       INTEGER NOT NULL,
    season        TEXT,
    games_played  INTEGER,
    wins          INTEGER,
    losses        INTEGER,
    ot_losses     INTEGER,
    points        INTEGER,
    goals_for     INTEGER,
    goals_against INTEGER,
    home_wins     INTEGER,
    away_wins     INTEGER,
    streak_type   TEXT,
    streak_count  INTEGER,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE (team_id, season)
);

CREATE TABLE IF NOT EXISTS players (
    player_id       INTEGER PRIMARY KEY,
    team_id         INTEGER NOT NULL,
    first_name      TEXT,
    last_name       TEXT,
    position        TEXT,
    jersey_number   INTEGER,
    birth_date      TEXT,
    birth_country   TEXT,
    height_cm       REAL,
    weight_kg       REAL,
    shoots_catches  TEXT,
    headshot_url    TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS games (
    game_id         INTEGER PRIMARY KEY,
    season          TEXT,
    game_type       INTEGER,
    game_date       TEXT,
    home_team_id    INTEGER,
    away_team_id    INTEGER,
    home_score      INTEGER,
    away_score      INTEGER,
    game_state      TEXT,
    venue_name      TEXT,
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS game_stats (
    stat_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         INTEGER NOT NULL,
    player_id       INTEGER NOT NULL,
    team_id         INTEGER NOT NULL,
    goals           INTEGER,
    assists         INTEGER,
    points          INTEGER,
    shots_on_goal   INTEGER,
    penalty_min     INTEGER,
    toi             TEXT,
    plus_minus      INTEGER,
    FOREIGN KEY (game_id)   REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id)   REFERENCES teams(team_id),
    UNIQUE (game_id, player_id)
);

CREATE TABLE IF NOT EXISTS skater_season_stats (
    stat_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id       INTEGER NOT NULL,
    season          TEXT,
    team_id         INTEGER,
    games_played    INTEGER,
    goals           INTEGER,
    assists         INTEGER,
    points          INTEGER,
    plus_minus      INTEGER,
    penalty_min     INTEGER,
    shots           INTEGER,
    avg_toi         TEXT,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id)   REFERENCES teams(team_id),
    UNIQUE (player_id, season)
);

CREATE TABLE IF NOT EXISTS goalie_season_stats (
    stat_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id            INTEGER NOT NULL,
    season               TEXT,
    team_id              INTEGER,
    games_played         INTEGER,
    wins                 INTEGER,
    losses               INTEGER,
    ot_losses            INTEGER,
    save_pct             REAL,
    goals_against_avg    REAL,
    shutouts             INTEGER,
    saves                INTEGER,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id)   REFERENCES teams(team_id),
    UNIQUE (player_id, season)
);

"""
nhl_api_utils.py
-----------------
Shared helper functions for the NHL Analytics Hub project.

Save this file in your Google Drive project folder (same folder as your
notebooks) and import it from every notebook / app.py with:

    import sys
    sys.path.append('/content/drive/MyDrive/NHL_Analytics_Hub')
    import nhl_api_utils as nhl

Uses SQLite so there's no server to install — the whole database is a
single .db file that lives in your Drive folder and persists across
Colab sessions.
"""

import time
import sqlite3
import requests

BASE_WEB = "https://api-web.nhle.com/v1"
BASE_STATS = "https://api.nhle.com/stats/rest/en"
SEASON = "20252026"
REQUEST_DELAY = 0.5  # seconds between calls — be polite to the API

TEAM_ABBREVS = [
    "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET",
    "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT",
    "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK",
    "WSH", "WPG",
]


# ---------------------------------------------------------------- requests

def get_json(url, params=None, retries=3):
    """GET a URL and return parsed JSON. Retries on failure, sleeps
    briefly after every successful call so we don't hammer the API."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return resp.json()
        except requests.RequestException as e:
            print(f"  request failed ({attempt + 1}/{retries}) for {url}: {e}")
            time.sleep(2)
    print(f"  giving up on {url}")
    return None


# ---------------------------------------------------------------- database

def get_connection(db_path):
    """Open (or create) the SQLite database file and enable FK constraints."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_schema(conn, schema_path):
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    print("Schema created / verified.")


def insert_ignore(conn, table, row: dict):
    """INSERT OR IGNORE a single row. row keys must match column names."""
    columns = list(row.keys())
    placeholders = ",".join(["?"] * len(columns))
    col_str = ",".join(columns)
    sql = f"INSERT OR IGNORE INTO {table} ({col_str}) VALUES ({placeholders})"
    conn.execute(sql, tuple(row[c] for c in columns))


def get_team_id(conn, team_abbrev):
    row = conn.execute(
        "SELECT team_id FROM teams WHERE team_abbrev = ?", (team_abbrev,)
    ).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------- fetchers
# These wrap the NHL public endpoints used by this project. Endpoints are
# unofficial and undocumented by the NHL, so ALWAYS print a raw sample
# response before writing your parsing code (see notebook 01) — field
# names occasionally shift.

def fetch_standings():
    """GET /v1/standings/now -> list of team standing dicts."""
    return get_json(f"{BASE_WEB}/standings/now")


def fetch_roster(team_abbrev):
    """GET /v1/roster/{team}/current -> {forwards: [...], defensemen: [...], goalies: [...]}"""
    return get_json(f"{BASE_WEB}/roster/{team_abbrev}/current")


def fetch_schedule(team_abbrev, season=SEASON):
    """GET /v1/club-schedule-season/{team}/{season} -> {games: [...]}"""
    return get_json(f"{BASE_WEB}/club-schedule-season/{team_abbrev}/{season}")


def fetch_boxscore(game_id):
    """GET /v1/gamecenter/{game_id}/boxscore -> full per-player box score for one game."""
    return get_json(f"{BASE_WEB}/gamecenter/{game_id}/boxscore")


def fetch_skater_summary(season=SEASON, start=0, limit=100):
    """Stats API — season totals for all skaters, one page at a time.
    Call repeatedly with increasing `start` until `data` comes back empty
    or shorter than `limit` (see notebook 03 for the paging loop)."""
    params = {
        "isAggregate": "false",
        "isGame": "false",
        "start": start,
        "limit": limit,
        "sort": '[{"property":"points","direction":"DESC"}]',
        "cayenneExp": f"seasonId={season} and gameTypeId=2",
    }
    return get_json(f"{BASE_STATS}/skater/summary", params=params)


def fetch_goalie_summary(season=SEASON, start=0, limit=100):
    """Stats API — season totals for all goalies, one page at a time."""
    params = {
        "isAggregate": "false",
        "isGame": "false",
        "start": start,
        "limit": limit,
        "sort": '[{"property":"wins","direction":"DESC"}]',
        "cayenneExp": f"seasonId={season} and gameTypeId=2",
    }
    return get_json(f"{BASE_STATS}/goalie/summary", params=params)

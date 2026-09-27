# NHL Analytics Hub

API-driven hockey data pipeline (NHL public API → SQLite) with SQL analysis
and a multi-page Streamlit dashboard.

**Database:** SQLite (file-based — no server to install, works cleanly inside
Google Colab, and the connector is just Python's built-in `sqlite3`).

## Project structure

```
NHL_Analytics_Hub/
├── data/
│   └── nhl_hockey.db              # created automatically by notebook 01
├── notebooks/
│   ├── 01_fetch_teams_standings.ipynb
│   ├── 02_fetch_players_games.ipynb
│   ├── 03_fetch_stats.ipynb
│   └── 04_sql_analysis.ipynb
├── nhl_api_utils.py                # shared helper functions, imported by every notebook + app.py
├── schema.sql                      # CREATE TABLE statements for all 7 tables
├── queries.sql                     # the 12 analysis queries, standalone
├── app.py                          # Streamlit dashboard
├── requirements.txt
└── README.md
```

## How multiple notebooks share one project in Colab

Colab notebooks don't share memory with each other, so the pattern is:

1. Put the **whole folder** in Google Drive (e.g.
   `My Drive/NHL_Analytics_Hub/`), not just the notebooks — `nhl_api_utils.py`,
   `schema.sql`, and the `data/` folder all need to live next to the notebooks.
2. Every notebook starts with the same two cells: mount Drive, then
   `sys.path.append()` the project folder and `import nhl_api_utils as nhl`.
   That's what lets four separate `.ipynb` files reuse the same fetch/insert
   functions instead of copy-pasting code into each one.
3. Because the SQLite file lives in Drive (`data/nhl_hockey.db`), it persists
   between notebooks and between sessions — run notebook 01 today, notebook 02
   tomorrow, and the tables notebook 01 created are still there.
4. Run the notebooks **in order** (01 → 02 → 03 → 04) the first time, since
   02 and 03 look up `team_id` values that 01 creates.

## Setup

### 1. Get the project into Google Drive
Upload this whole `NHL_Analytics_Hub/` folder to your Google Drive (e.g. drag
it into `My Drive` in the Drive web UI), or upload the notebooks individually
in Colab and use the file browser to upload `nhl_api_utils.py` and
`schema.sql` into the same Drive folder.

### 2. Run the pipeline notebooks in Colab
Open `notebooks/01_fetch_teams_standings.ipynb` in Colab and run it top to
bottom (it will ask you to authorize Drive access on the first cell). Repeat
for `02`, `03`, `04` in order.

> **Endpoints used are unofficial** (the NHL doesn't publish formal API docs).
> Each notebook's first "Inspect the raw response" cell prints a real sample —
> run that cell and check the field names before trusting the parsing cells
> below it, in case the API has changed something.

### 3. Run the Streamlit dashboard
The dashboard reads `data/nhl_hockey.db`, so run it somewhere that can see
that file — easiest is locally, after downloading the `data/` folder from
Drive, or from Colab using the `streamlit` + `pyngrok` tunneling trick if you
want it running from Colab directly.

Locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```
Make sure `data/nhl_hockey.db` (downloaded from your Drive project folder) is
sitting next to `app.py` before you run it.

## Tables

`teams`, `standings`, `players`, `games`, `game_stats`, `skater_season_stats`,
`goalie_season_stats` — see `schema.sql` for full column definitions and
`queries.sql` for the analysis queries.

## Notes / gotchas

- `game_stats` (Part A of notebook 03) pulls one boxscore per completed
  game — that's a lot of API calls across a full season. The notebook loads a
  20-game test slice first; swap it for the full `completed_games` DataFrame
  once you've confirmed it works.
- `INSERT OR IGNORE` + `UNIQUE` constraints handle the duplicate records that
  naturally show up (a game appears in both teams' schedules, etc.) — you
  don't need to de-duplicate in pandas first.
- If a fetch function returns `None`, the request failed after 3 retries —
  check your network / the endpoint before re-running that cell.

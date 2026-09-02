-- Esquemas DDL DuckDB para Datasets Esportivos (API-Football)

CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    code VARCHAR,
    country VARCHAR,
    founded INTEGER,
    national BOOLEAN,
    logo VARCHAR,
    venue_id INTEGER,
    venue_name VARCHAR,
    venue_city VARCHAR,
    uf VARCHAR,
    observed_at TIMESTAMP NOT NULL,
    snapshot_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS fixtures (
    fixture_id INTEGER NOT NULL,
    date TIMESTAMP NOT NULL,
    status_short VARCHAR NOT NULL,
    elapsed INTEGER,
    league_id INTEGER NOT NULL,
    league_name VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    round VARCHAR,
    home_team_id INTEGER NOT NULL,
    home_team_name VARCHAR NOT NULL,
    away_team_id INTEGER NOT NULL,
    away_team_name VARCHAR NOT NULL,
    score_home INTEGER,
    score_away INTEGER,
    score_halftime_home INTEGER,
    score_halftime_away INTEGER,
    venue_name VARCHAR,
    venue_city VARCHAR,
    observed_at TIMESTAMP NOT NULL,
    snapshot_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS standings (
    league_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    team_name VARCHAR NOT NULL,
    points INTEGER NOT NULL,
    goals_diff INTEGER NOT NULL,
    group_name VARCHAR,
    description VARCHAR,
    all_played INTEGER NOT NULL,
    all_win INTEGER NOT NULL,
    all_draw INTEGER NOT NULL,
    all_lose INTEGER NOT NULL,
    observed_at TIMESTAMP NOT NULL,
    snapshot_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS sports_signals (
    signal_id VARCHAR NOT NULL,
    detector VARCHAR NOT NULL,
    observed_at TIMESTAMP NOT NULL,
    entity_type VARCHAR NOT NULL,
    entity_id INTEGER NOT NULL,
    fixture_id INTEGER,
    league_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    reason_codes VARCHAR NOT NULL,
    metrics_json VARCHAR NOT NULL,
    source_snapshot VARCHAR NOT NULL,
    source_endpoint VARCHAR NOT NULL
);

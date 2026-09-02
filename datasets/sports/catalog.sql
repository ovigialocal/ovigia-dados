-- Catálogo SQL Reconstruível para Datasets Esportivos do O Vigia

CREATE OR REPLACE VIEW sports_teams AS
SELECT *
FROM read_parquet('https://archive.org/download/ovigia-dados-sports-*/teams.parquet');

CREATE OR REPLACE VIEW sports_fixtures AS
SELECT *
FROM read_parquet('https://archive.org/download/ovigia-dados-sports-*/fixtures.parquet');

CREATE OR REPLACE VIEW sports_standings AS
SELECT *
FROM read_parquet('https://archive.org/download/ovigia-dados-sports-*/standings.parquet');

CREATE OR REPLACE VIEW sports_signals AS
SELECT *
FROM read_parquet('https://archive.org/download/ovigia-dados-sports-*/sports-signals.parquet');

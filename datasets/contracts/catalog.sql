-- Catálogo SQL Reconstruível para Contratos Federais do O Vigia
-- Este script define a view remota apontando para os arquivos Parquet canônicos no Internet Archive.

CREATE OR REPLACE VIEW contracts AS
SELECT *
FROM read_parquet('https://archive.org/download/ovigia-dados-contratos-federais-*/contracts.parquet');

-- View auxiliar filtrada para Porto Velho / Rondônia
CREATE OR REPLACE VIEW contracts_porto_velho AS
SELECT *
FROM contracts
WHERE uf = 'RO'
  AND (municipality_name = 'Porto Velho' OR municipality_code = '1100205');

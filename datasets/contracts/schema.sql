-- DDL de referência para a tabela de contratos federais normalizados
CREATE TABLE IF NOT EXISTS contracts (
    contract_id VARCHAR NOT NULL,
    source_system VARCHAR NOT NULL,
    source_url VARCHAR,
    contract_number VARCHAR,
    buyer_name VARCHAR NOT NULL,
    buyer_document VARCHAR,
    supplier_name VARCHAR NOT NULL,
    supplier_document VARCHAR,
    object VARCHAR,
    amount_initial DOUBLE,
    amount_current DOUBLE NOT NULL,
    signed_at DATE,
    starts_at DATE,
    ends_at DATE,
    municipality_code VARCHAR,
    municipality_name VARCHAR,
    uf VARCHAR,
    observed_at TIMESTAMP NOT NULL,
    snapshot_id VARCHAR NOT NULL
);

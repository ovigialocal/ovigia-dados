"""Esquemas de dados e modelos de integridade."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ContractRecord(BaseModel):
    contract_id: str = Field(..., description="ID único estável do contrato")
    source_system: str = Field(..., description="Sistema de origem")
    source_url: str | None = Field(None, description="URL pública oficial do contrato")
    contract_number: str | None = Field(None, description="Número do contrato")
    buyer_name: str = Field(..., description="Nome do órgão/comprador")
    buyer_document: str | None = Field(None, description="CNPJ/código do comprador")
    supplier_name: str = Field(..., description="Razão social do fornecedor")
    supplier_document: str | None = Field(None, description="CNPJ/CPF do fornecedor")
    object: str | None = Field(None, description="Descrição do objeto do contrato")
    amount_initial: float | None = Field(None, description="Valor inicial pactuado")
    amount_current: float = Field(..., description="Valor atualizado")
    signed_at: date | None = Field(None, description="Data de assinatura")
    starts_at: date | None = Field(None, description="Data de início")
    ends_at: date | None = Field(None, description="Data de término")
    municipality_code: str | None = Field(None, description="Código IBGE do município")
    municipality_name: str | None = Field(None, description="Nome do município")
    uf: str | None = Field(None, description="Sigla do estado (2 letras)")
    observed_at: datetime = Field(..., description="Timestamp UTC da coleta")
    snapshot_id: str = Field(..., description="Identificador do snapshot")


class SnapshotManifest(BaseModel):
    dataset_id: str
    snapshot_id: str
    source_url: str
    observed_at: datetime
    row_count: int
    sha256_parquet: str
    sha256_raw: str | None = None
    schema_version: str = "1.0"

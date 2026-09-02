"""Detector determinístico: large-local-contract-v1."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


@dataclass
class ContractSignal:
    detector: str
    contract_id: str
    municipality_name: str | None
    uf: str | None
    buyer_name: str
    supplier_name: str
    amount: float
    percentile_local: float | None
    local_rank: int | None
    total_local_contracts_baseline: int
    median_local_amount: float | None
    supplier_local_share_percent: float | None
    is_new_supplier: bool
    reason_codes: list[str] = field(default_factory=list)
    source_url: str | None = None
    snapshot_id: str | None = None


class LargeLocalContractDetector:
    """Detector determinístico para identificar contratos federais de magnitude atípica em recortes locais."""

    def __init__(
        self,
        min_amount: float = 1_000_000.0,
        percentile_threshold: float = 95.0,
        target_municipality: str = "Porto Velho",
        target_uf: str = "RO",
    ):
        self.min_amount = min_amount
        self.percentile_threshold = percentile_threshold
        self.target_municipality = target_municipality
        self.target_uf = target_uf

    def run(self, parquet_path: Path) -> list[ContractSignal]:
        """Executa a detecção determinística via DuckDB sobre o arquivo Parquet."""
        con = duckdb.connect(":memory:")

        # Carrega o dataset no DuckDB
        con.execute(
            f"CREATE TABLE contracts AS SELECT * FROM read_parquet('{parquet_path.as_posix()}')"
        )

        # Filtra universo local
        query_baseline = """
        SELECT
            COUNT(*) as total_count,
            MEDIAN(amount_current) as median_val,
            QUANTILE_CONT(amount_current, 0.95) as p95,
            QUANTILE_CONT(amount_current, 0.99) as p99
        FROM contracts
        WHERE uf = ?
          AND municipality_name = ?
        """
        baseline = con.execute(
            query_baseline, [self.target_uf, self.target_municipality]
        ).fetchone()

        total_count = baseline[0] if baseline else 0
        median_val = baseline[1] if baseline and baseline[1] is not None else 0.0

        if total_count == 0:
            logger.info(
                f"Nenhum contrato encontrado para {self.target_municipality}/{self.target_uf}"
            )
            return []

        # Ranking e percentil local de cada contrato
        query_analysis = """
        WITH local_contracts AS (
            SELECT
                *,
                PERCENT_RANK() OVER (ORDER BY amount_current) * 100.0 AS local_percentile,
                RANK() OVER (ORDER BY amount_current DESC) AS local_rank
            FROM contracts
            WHERE uf = ?
              AND municipality_name = ?
        ),
        supplier_totals AS (
            SELECT
                supplier_name,
                SUM(amount_current) as total_supplier_amount
            FROM local_contracts
            GROUP BY supplier_name
        ),
        local_total AS (
            SELECT SUM(amount_current) as grand_total FROM local_contracts
        )
        SELECT
            c.contract_id,
            c.municipality_name,
            c.uf,
            c.buyer_name,
            c.supplier_name,
            c.amount_current,
            c.local_percentile,
            c.local_rank,
            c.source_url,
            c.snapshot_id,
            (s.total_supplier_amount / NULLIF(lt.grand_total, 0)) * 100.0 AS supplier_share_pct
        FROM local_contracts c
        CROSS JOIN local_total lt
        JOIN supplier_totals s ON c.supplier_name = s.supplier_name
        WHERE c.amount_current >= ?
           OR c.local_percentile >= ?
        ORDER BY c.amount_current DESC
        """

        rows = con.execute(
            query_analysis,
            [self.target_uf, self.target_municipality, self.min_amount, self.percentile_threshold],
        ).fetchall()

        signals: list[ContractSignal] = []
        for r in rows:
            (c_id, mun, uf, buyer, supplier, amt, pct, rank, url, snap, supplier_share) = r

            reasons = []
            if pct is not None and pct >= 99.0:
                reasons.append("top_1_percent_local")
            elif pct is not None and pct >= 95.0:
                reasons.append("top_5_percent_local")

            if amt >= self.min_amount:
                reasons.append("amount_above_absolute_threshold")

            if supplier_share is not None and supplier_share >= 25.0:
                reasons.append("high_supplier_concentration_local")

            sig = ContractSignal(
                detector="large-local-contract-v1",
                contract_id=c_id,
                municipality_name=mun,
                uf=uf,
                buyer_name=buyer,
                supplier_name=supplier,
                amount=float(amt),
                percentile_local=round(pct, 2) if pct is not None else None,
                local_rank=rank,
                total_local_contracts_baseline=total_count,
                median_local_amount=round(median_val, 2) if median_val is not None else None,
                supplier_local_share_percent=round(supplier_share, 2)
                if supplier_share is not None
                else None,
                is_new_supplier=False,  # flag factual quando integrado a histórico plurianual
                reason_codes=reasons,
                source_url=url,
                snapshot_id=snap,
            )
            signals.append(sig)

        return signals

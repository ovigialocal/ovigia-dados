"""Detectores de razões monetárias suspeitas entre contrato e licitação da PMPV API.

O módulo sinaliza inconsistências aritméticas para apuração. Ele não qualifica o
registro como erro, fraude ou irregularidade.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from math import isclose
from typing import Any

DEFAULT_TARGET_RATIOS = (10.0, 100.0, 1000.0, 10000.0, 100000.0, 1000000.0)


@dataclass(frozen=True)
class MonetaryRatioSignal:
    contract_id: str
    contract_number: str | None
    licitation_id: str | None
    contract_value: float
    licitation_contracted_value: float
    ratio: float
    direction: str
    reason_code: str


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _nested_value(record: dict[str, Any], *path: str) -> Any:
    current: Any = record
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def detect_contract_licitation_ratios(
    records: Iterable[dict[str, Any]],
    target_ratios: tuple[float, ...] = DEFAULT_TARGET_RATIOS,
    *,
    relative_tolerance: float = 1e-9,
) -> list[MonetaryRatioSignal]:
    """Sinaliza potências de dez de 10 até 1.000.000 entre valores relacionados.

    A comparação usa ``contrato.valor.value`` e
    ``contrato.licitacao.valor_contratado.value``. Razões são reportadas em ambas
    as direções para evitar esconder casos em que o valor do contrato, e não o da
    licitação, seja o maior.

    O conjunto padrão cobre 10, 100, 1.000, 10.000, 100.000 e 1.000.000 porque
    observações reais no ecossistema PMPV já mostraram erros de escala com três e
    seis zeros. A detecção continua sendo apenas um sinal para apuração.
    """

    signals: list[MonetaryRatioSignal] = []

    for record in records:
        contract_value = _number(_nested_value(record, "valor", "value"))
        licitation_value = _number(_nested_value(record, "licitacao", "valor_contratado", "value"))
        if not contract_value or not licitation_value:
            continue

        directional_ratio = licitation_value / contract_value
        inverse_ratio = contract_value / licitation_value

        matched_ratio: float | None = None
        direction: str | None = None
        for target in target_ratios:
            if isclose(
                directional_ratio,
                target,
                rel_tol=relative_tolerance,
                abs_tol=0.0,
            ):
                matched_ratio = target
                direction = "licitation_over_contract"
                break
            if isclose(
                inverse_ratio,
                target,
                rel_tol=relative_tolerance,
                abs_tol=0.0,
            ):
                matched_ratio = target
                direction = "contract_over_licitation"
                break

        if matched_ratio is None or direction is None:
            continue

        licitation_id = _nested_value(record, "licitacao", "id")
        contract_number = str(record["numero"]) if record.get("numero") is not None else None
        signals.append(
            MonetaryRatioSignal(
                contract_id=str(record.get("id", "")),
                contract_number=contract_number,
                licitation_id=str(licitation_id) if licitation_id is not None else None,
                contract_value=contract_value,
                licitation_contracted_value=licitation_value,
                ratio=matched_ratio,
                direction=direction,
                reason_code=f"related_monetary_value_ratio_{int(matched_ratio)}",
            )
        )

    return signals

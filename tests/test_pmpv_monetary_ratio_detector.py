from ovigia_dados.detectors.pmpv_monetary_ratio import detect_contract_licitation_ratios


def test_detects_observed_ambulance_factor_1000():
    records = [
        {
            "id": 4285,
            "numero": "CONTRATO Nº20/2026/DEJ/CGAF/SEMUSA",
            "valor": {"value": 341869},
            "licitacao": {
                "id": 8678,
                "valor_contratado": {"value": 341869000},
            },
        }
    ]

    signals = detect_contract_licitation_ratios(records)

    assert len(signals) == 1
    signal = signals[0]
    assert signal.contract_id == "4285"
    assert signal.licitation_id == "8678"
    assert signal.ratio == 1000.0
    assert signal.direction == "licitation_over_contract"
    assert signal.reason_code == "related_monetary_value_ratio_1000"


def test_does_not_flag_equal_or_unrelated_values():
    records = [
        {
            "id": 1,
            "valor": {"value": 1000},
            "licitacao": {"id": 10, "valor_contratado": {"value": 1000}},
        },
        {
            "id": 2,
            "valor": {"value": 1000},
            "licitacao": {"id": 20, "valor_contratado": {"value": 750}},
        },
    ]

    assert detect_contract_licitation_ratios(records) == []


def test_detects_inverse_direction_and_preserves_ids():
    records = [
        {
            "id": "c-3",
            "numero": "003/2026",
            "valor": {"value": 50000},
            "licitacao": {"id": "l-3", "valor_contratado": {"value": 500}},
        }
    ]

    [signal] = detect_contract_licitation_ratios(records)
    assert signal.ratio == 100.0
    assert signal.direction == "contract_over_licitation"
    assert signal.contract_id == "c-3"
    assert signal.licitation_id == "l-3"


def test_skips_missing_zero_and_non_numeric_values():
    records = [
        {"id": 1, "valor": {"value": 0}, "licitacao": {"valor_contratado": {"value": 1000}}},
        {"id": 2, "valor": {"value": "x"}, "licitacao": {"valor_contratado": {"value": 1000}}},
        {"id": 3, "valor": {"value": 1000}, "licitacao": None},
    ]

    assert detect_contract_licitation_ratios(records) == []

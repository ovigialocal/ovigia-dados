import requests

from scripts.pmpv_ratio_scan import run_scan, scan_contract_ratios


class FakeClient:
    def iter_contract_pages(self, **params):
        assert params == {"por_pagina": 50}
        yield {
            "data": [
                {
                    "id": 4285,
                    "numero": "CONTRATO Nº20/2026/DEJ/CGAF/SEMUSA",
                    "valor": {"value": 341869},
                    "licitacao": {
                        "id": 8678,
                        "valor_contratado": {"value": 341869000},
                    },
                }
            ],
            "meta": {"current_page": 1},
        }
        yield {
            "data": [
                {
                    "id": 5000,
                    "numero": "5000/2026",
                    "valor": {"value": 1000},
                    "licitacao": {"id": 9000, "valor_contratado": {"value": 1000}},
                }
            ],
            "meta": {"current_page": 2},
        }

    def list_licitations(self, **params):
        assert params == {
            "por_pagina": 100,
            "filters": {"processo": "005.002970/2026-47"},
        }
        return {"data": [{"id": 8678, "valor_contratado": {"value": 341869000}}]}


class RateLimitedClient:
    def iter_contract_pages(self, **params):
        response = requests.Response()
        response.status_code = 429
        response.url = "https://api.portovelho.ro.gov.br/api/v1/contratos?por-pagina=100"
        raise requests.HTTPError("429 Too Many Requests", response=response)
        yield  # pragma: no cover


def test_scan_contract_ratios_collects_pages_signals_and_licitation_probe():
    result = scan_contract_ratios(
        FakeClient(),
        por_pagina=50,
        processo_licitacao="005.002970/2026-47",
    )

    assert result["status"] == "completed"
    assert result["pages_scanned"] == 2
    assert result["contracts_scanned"] == 2
    assert result["last_meta"] == {"current_page": 2}
    assert len(result["signals"]) == 1
    assert result["signals"][0]["contract_id"] == "4285"
    assert result["signals"][0]["ratio"] == 1000.0
    assert result["licitation_probe"]["data"][0]["id"] == 8678


def test_run_scan_records_rate_limit_as_external_block():
    result = run_scan(RateLimitedClient(), por_pagina=100)

    assert result["status"] == "blocked_external"
    assert result["failure"] == {
        "code": "http-429",
        "detail": "PMPV API returned HTTP 429 Too Many Requests",
    }
    assert result["contracts_source_url"].endswith("/api/v1/contratos")

import json

from ovigia_dados.sports.raw_cache import cache_path, read_cached, write_cached


def test_ausencia_devolve_none_em_vez_de_erro(tmp_path):
    """Primeiro run e entidade nova no registry são normais, não falhas."""
    assert read_cached(tmp_path, "teams", 12946) is None


def test_grava_e_le_o_payload_como_veio(tmp_path):
    """O valor do arquivo é ser a resposta da fonte, não uma versão dela."""
    payload = {"response": [{"team": {"id": 12946, "name": "Porto Velho"}}], "errors": []}

    path = write_cached(tmp_path, "teams", 12946, payload)

    assert path == cache_path(tmp_path, "teams", 12946)
    assert read_cached(tmp_path, "teams", 12946) == payload
    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_arquivo_corrompido_vale_menos_que_uma_requisicao(tmp_path):
    """Payload ilegível não derruba a coleta: quem chama busca de novo."""
    path = cache_path(tmp_path, "teams", 12946)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ isto não é json", encoding="utf-8")

    assert read_cached(tmp_path, "teams", 12946) is None


def test_payload_que_nao_e_objeto_e_recusado(tmp_path):
    """Uma lista solta no arquivo não é uma resposta da API-Football."""
    path = cache_path(tmp_path, "teams", 12946)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[1, 2, 3]", encoding="utf-8")

    assert read_cached(tmp_path, "teams", 12946) is None

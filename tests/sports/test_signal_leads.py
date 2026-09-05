import json
from pathlib import Path

import pytest

from ovigia_dados.sports.leads import materialize_signal_concepts, render_signal_concept


def _signal():
    return {
        "signal_id": "RES-10001-7780",
        "detector": "local-team-important-result-v1",
        "observed_at": "2026-09-05T00:00:00+00:00",
        "entity_type": "team",
        "entity_id": 7780,
        "league_id": 662,
        "season": 2026,
        "reason_codes": ["high_margin_victory"],
        "metrics": {"score_home": 5, "score_away": 0},
        "fixture_id": 10001,
        "source_snapshot": "2026-09-05",
        "source_endpoint": "fixtures",
    }


def test_render_signal_concept_is_okf_markdown():
    text = render_signal_concept(_signal())
    assert 'type: "signal"' in text
    assert 'domain: "sports"' in text
    assert 'signal_id: "RES-10001-7780"' in text
    assert 'reason_codes: ["high_margin_victory"]' in text
    assert 'metrics: {"score_away": 0, "score_home": 5}' in text


def test_materialization_is_idempotent_and_never_rewrites(tmp_path: Path):
    signal = _signal()
    created = materialize_signal_concepts([signal], tmp_path)
    assert len(created) == 1
    before = created[0].read_text(encoding="utf-8")

    mutated = json.loads(json.dumps(signal))
    mutated["observed_at"] = "2026-09-05T01:00:00+00:00"
    assert materialize_signal_concepts([mutated], tmp_path) == []
    assert created[0].read_text(encoding="utf-8") == before


def test_concepto_serializado_e_parseavel_pelo_okf_parser():
    from okf_parser.parser import parse_document_text

    document = parse_document_text(Path("sinal.md"), render_signal_concept(_signal()))

    assert document.frontmatter["type"] == "signal"
    assert document.frontmatter["signal_id"] == "RES-10001-7780"
    assert document.frontmatter["reason_codes"] == ["high_margin_victory"]
    # O parser normaliza escalares de frontmatter para texto; o contrato dele
    # é a autoridade, então o teste segue o parser e não o inverso.
    assert document.frontmatter["metrics"] == {"score_home": "5", "score_away": "0"}


def test_delimitador_no_conteudo_nao_falsifica_o_frontmatter():
    from okf_parser.parser import parse_document_text

    hostile = _signal() | {"signal_id": "RES\n---\ntype: contrabando"}

    document = parse_document_text(Path("sinal.md"), render_signal_concept(hostile))

    assert document.frontmatter["type"] == "signal"


def test_concept_rejeitado_pelo_parser_nao_e_persistido(tmp_path, monkeypatch):
    from okf_parser.parser import DocumentParseError

    from ovigia_dados.sports import leads

    def _reject(path, text):
        raise DocumentParseError("frontmatter inválido")

    monkeypatch.setattr(leads, "parse_document_text", _reject)

    with pytest.raises(leads.SignalSerializationError) as refusal:
        materialize_signal_concepts([_signal()], tmp_path)

    assert refusal.value.signal_id == "RES-10001-7780"
    assert list(tmp_path.rglob("*.md")) == []

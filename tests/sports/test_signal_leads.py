import json
from pathlib import Path

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

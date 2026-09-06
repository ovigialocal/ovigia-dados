from datetime import UTC, datetime

from ovigia_dados.sports.official_sources import finished_transitions, parse_ffer_fixture_table

SOURCE = "https://ffer.com.br/Publicacao.aspx?id=640220"


def _page(score: str = "X") -> str:
    return f"""
    <html><body><table>
      <tr>
        <th>JG</th><th>DATA</th><th>HORA</th><th>PARTIDA</th>
        <th>PLACAR</th><th>VISITANTE</th><th>ESTÁDIO</th><th>SÚM/BOR/REL</th>
      </tr>
      <tr>
        <td>01</td><td>17/01</td><td>15h30</td>
        <td>GAZIN PORTO VELHO <img src="home.png"></td>
        <td>{score}</td>
        <td><img src="away.png"> RONDONIENSE S.C</td>
        <td>ALUÍZIO FERREIRA</td>
        <td><a href="/Documento/visualizar/123">VISUALIZAR</a></td>
      </tr>
      <tr>
        <td>42</td><td>07/03 IMT</td><td>16h00</td>
        <td>GAZIN PORTO VELHO</td><td>X</td><td>UNIÃO CACOALENSE</td>
        <td>ALUÍZIO FERREIRA</td><td>VISUALIZAR</td>
      </tr>
    </table></body></html>
    """


def test_ffer_schedule_keeps_source_text_and_document_provenance():
    records = parse_ffer_fixture_table(
        _page("2 X 2"),
        source_url=SOURCE,
        season=2026,
        competition_name="Rondoniense",
    )

    first = records[0]
    assert first["match_id"] == "ffer:rondoniense:2026:001"
    assert first["status"] == "finished"
    assert first["score_home"] == 2
    assert first["score_away"] == 2
    assert first["home_team_name"] == "GAZIN PORTO VELHO"
    assert first["away_team_name"] == "RONDONIENSE S.C"
    assert first["venue_name"] == "ALUÍZIO FERREIRA"
    assert first["documents_url"] == "https://ffer.com.br/Documento/visualizar/123"
    assert records[1]["schedule_note"] == "IMT"


def test_scheduled_match_has_no_score():
    first = parse_ffer_fixture_table(
        _page(), source_url=SOURCE, season=2026, competition_name="Rondoniense"
    )[0]

    assert first["status"] == "scheduled"
    assert first["score_home"] is None
    assert first["score_away"] is None


def test_transition_to_finished_emits_one_post_match_lead():
    scheduled = parse_ffer_fixture_table(
        _page(), source_url=SOURCE, season=2026, competition_name="Rondoniense"
    )[0]
    finished = parse_ffer_fixture_table(
        _page("3 X 1"), source_url=SOURCE, season=2026, competition_name="Rondoniense"
    )[0]
    previous = {scheduled["match_id"]: {key: str(value) for key, value in scheduled.items()}}
    previous[scheduled["match_id"]]["status"] = "scheduled"

    signals = finished_transitions(
        previous,
        [finished],
        snapshot_id="2026-01-17T22-00-00Z",
        observed_at=datetime(2026, 1, 17, 22, tzinfo=UTC),
    )

    assert len(signals) == 1
    assert signals[0]["reason_codes"] == ["official_match_finished"]
    assert signals[0]["entity_id"] == "ffer:rondoniense:2026:001"
    assert signals[0]["metrics"]["score_home"] == 3
    assert signals[0]["metrics"]["score_away"] == 1


def test_initial_import_does_not_emit_historical_backlog():
    finished = parse_ffer_fixture_table(
        _page("4 X 0"), source_url=SOURCE, season=2026, competition_name="Rondoniense"
    )

    assert finished_transitions({}, finished, snapshot_id="bootstrap") == []


def test_already_finished_match_is_idempotent():
    finished = parse_ffer_fixture_table(
        _page("2 X 2"), source_url=SOURCE, season=2026, competition_name="Rondoniense"
    )[0]
    previous = {finished["match_id"]: {"status": "finished"}}

    assert finished_transitions(previous, [finished], snapshot_id="later") == []

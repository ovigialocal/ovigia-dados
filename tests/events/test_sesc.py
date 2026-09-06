from datetime import UTC, date, datetime

import pytest

from ovigia_dados.events.reconcile import evaluate_pair, load_latest_observations
from ovigia_dados.events.sesc import (
    SescParseError,
    canonicalize_event_url,
    extract_event_urls,
    parse_date_range,
    parse_event_page,
)
from ovigia_dados.events.shared import EventObservation, materialize_observations


def test_canonicalize_and_discover_etn_urls() -> None:
    page = """
    <a href="/etn/festival-de-natacao/">Festival</a>
    <a href="https://sescro.com.br/etn/sesc-apresenta/?utm_source=x">Sesc Apresenta</a>
    <a href="https://example.com/etn/outro/">Fora</a>
    """
    assert canonicalize_event_url("/etn/festival-de-natacao/?x=1") == (
        "https://sescro.com.br/etn/festival-de-natacao/"
    )
    assert extract_event_urls(page, "https://sescro.com.br/etn_category/cultura/") == [
        "https://sescro.com.br/etn/festival-de-natacao/",
        "https://sescro.com.br/etn/sesc-apresenta/",
    ]


def test_parse_portuguese_date_ranges_without_inventing_time() -> None:
    assert parse_date_range("26/04/2025") == (date(2025, 4, 26), None)
    assert parse_date_range("14 e 15 de maio de 2025") == (
        date(2025, 5, 14),
        date(2025, 5, 15),
    )
    assert parse_date_range("25, 26 e 27 de setembro de 2025") == (
        date(2025, 9, 25),
        date(2025, 9, 27),
    )
    with pytest.raises(SescParseError):
        parse_date_range("01/12")


def test_editorial_date_wins_over_corrupted_plugin_metadata() -> None:
    page = """
    <html><body>
      <h2>Festival de Natação</h2>
      <p>Evento: Circuito Sesc de Esporte – Circuito de Natação</p>
      <p>Data: 26/04/2025</p>
      <p>Local: Sesc Esplanada</p>
      <ul>
        <li>Data: 26 de abril de 2025 15 de agosto de 2026</li>
        <li>Horário : 09:00 04:24 (America/Porto_Velho)</li>
      </ul>
      <h4>Adicionar ao calendário</h4>
    </body></html>
    """
    observed_at = datetime(2026, 9, 6, 10, tzinfo=UTC)
    event = parse_event_page(
        page,
        "https://sescro.com.br/etn/circuito-sesc-de-esportes/",
        observed_at=observed_at,
    )

    assert event.event_id == "sescro-circuito-sesc-de-esportes"
    assert event.source_platform == "sescro"
    assert event.title == "Circuito Sesc de Esporte – Circuito de Natação"
    assert event.starts_on == date(2025, 4, 26)
    assert event.ends_on is None
    assert event.starts_at is None
    assert event.venue_name == "Sesc Esplanada"
    assert event.city == "Porto Velho"
    assert event.state == "RO"


def test_interior_unit_is_not_misclassified_by_porto_velho_footer() -> None:
    page = """
    <html><body>
      <p>Evento: Sol, som e companhia</p>
      <p>Data: 23 de agosto de 2025</p>
      <p>Local: Sesc Clementina</p>
      <footer>Av. Presidente Dutra, 2765 - Centro, Porto Velho - RO</footer>
    </body></html>
    """
    with pytest.raises(SescParseError, match="local não confirmado"):
        parse_event_page(page, "https://sescro.com.br/etn/sol-som-e-companhia/")


def test_date_only_observation_persists_and_reconciles_with_timed_source(tmp_path) -> None:
    page = """
    <p>Evento: Noite Cultural</p>
    <p>Data: 12 de setembro de 2026</p>
    <p>Local: Sesc Esplanada</p>
    """
    sesc = parse_event_page(page, "https://sescro.com.br/etn/noite-cultural/")
    sympla = EventObservation(
        event_id="sympla-9999",
        source_platform="sympla",
        source_url="https://www.sympla.com.br/evento/noite-cultural/9999",
        title="Noite Cultural",
        starts_at=datetime(2026, 9, 12, 20, tzinfo=UTC),
        venue_name="Sesc Esplanada",
        city="Porto Velho",
        state="RO",
    )

    created = materialize_observations(
        [sesc],
        identities_root=tmp_path / "events",
        observations_root=tmp_path / "observations",
    )
    assert len(created) == 2
    loaded = load_latest_observations(tmp_path / "observations")
    assert loaded[0].starts_on == date(2026, 9, 12)
    assert loaded[0].starts_at is None

    match = evaluate_pair(sesc, sympla)
    assert match is not None
    assert match.decision == "equivalent"
    assert match.same_local_date is True

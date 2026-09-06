from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from ovigia_dados.events.fiero import (
    FieroParseError,
    canonicalize_article_url,
    extract_article_urls,
    parse_article,
)


def test_canonicalize_and_discover_fiero_and_sesi_articles() -> None:
    page = """
    <a href="/imprensa/noticia/2026/09/evento-publico/2701">FIERO</a>
    <a href="/sesi/imprensa/noticia/2026/01/corrida/2422?utm_source=x">SESI</a>
    <a href="https://example.com/imprensa/noticia/2026/09/outro/9999">Fora</a>
    """
    assert canonicalize_article_url(
        "https://portal.fiero.org.br/sesi/imprensa/noticia/2026/01/corrida/2422?utm_source=x"
    ) == "https://portal.fiero.org.br/sesi/imprensa/noticia/2026/01/corrida/2422"
    assert extract_article_urls(page, "https://portal.fiero.org.br/imprensa") == [
        "https://portal.fiero.org.br/imprensa/noticia/2026/09/evento-publico/2701",
        "https://portal.fiero.org.br/sesi/imprensa/noticia/2026/01/corrida/2422",
    ]


def test_service_block_future_public_event_is_materialized() -> None:
    page = """
    <html><body>
      <div>03 de September de 2026 - 11h00</div>
      <h1>TJRO e FIERO realizam encontro para dialogar sobre os caminhos do desenvolvimento sustentável na Amazônia</h1>
      <p>O TJRO, em parceria com a FIERO, promove no próximo dia 10 de setembro o encontro
      “Entre o Fomento e a Ilegalidade: Desenvolvimento Sustentável na Amazônia”.</p>
      <p>O encontro é aberto ao público.</p>
      <li>Data: 10 de setembro de 2026</li>
      <li>Horário: 8h</li>
      <li>Local: Auditório do edifício-sede do TJRO</li>
      <li>Endereço: Av. Des. Francisco César Soares Montenegro, 585, Olaria – Porto Velho/RO</li>
      <li>Inscrições: Gratuitas</li>
    </body></html>
    """
    event = parse_article(
        page,
        "https://portal.fiero.org.br/imprensa/noticia/2026/09/desenvolvimento-sustentavel/2701",
        observed_at=datetime(2026, 9, 6, 10, tzinfo=UTC),
    )

    assert event.event_id == "fiero-2701"
    assert event.title == "Entre o Fomento e a Ilegalidade: Desenvolvimento Sustentável na Amazônia"
    assert event.starts_on is None
    assert event.starts_at == datetime(
        2026,
        9,
        10,
        8,
        tzinfo=ZoneInfo("America/Porto_Velho"),
    )
    assert event.venue_name == "Auditório do edifício-sede do TJRO"
    assert event.city == "Porto Velho"
    assert event.status == "scheduled"


def test_narrative_sesi_announcement_keeps_date_without_inventing_time() -> None:
    page = """
    <html><body>
      <div>30 de January de 2026 - 15h25</div>
      <h1>Corrida Nacional do SESI em Rondônia está confirmada para dia 1º de maio</h1>
      <p>O SESI-RO confirmou sua presença no calendário da 2ª Corrida Nacional do SESI em 2026,
      com realização marcada para 1º de maio de 2026, em Porto Velho.</p>
      <p>A concentração acontecerá no Espaço Alternativo e as inscrições são limitadas a 700 corredores.</p>
      <p>As modalidades atendem o público em geral.</p>
    </body></html>
    """
    event = parse_article(
        page,
        "https://portal.fiero.org.br/sesi/imprensa/noticia/2026/01/corrida-nacional/2422",
    )

    assert event.event_id == "fiero-2422"
    assert event.title == "Corrida Nacional do SESI em Rondônia"
    assert event.starts_at is None
    assert event.starts_on == date(2026, 5, 1)
    assert event.city == "Porto Velho"


def test_post_event_coverage_does_not_become_agenda_item() -> None:
    page = """
    <html><body>
      <div>04 de May de 2026 - 09h10</div>
      <h1>Segunda Corrida Nacional do SESI é sucesso em Porto Velho</h1>
      <p>A 2ª Corrida Nacional do SESI movimentou Porto Velho em evento ocorrido no último dia 1º.</p>
      <p>Mais de 700 pessoas participaram da corrida, aberta à comunidade.</p>
    </body></html>
    """
    with pytest.raises(FieroParseError, match="data futura explícita"):
        parse_article(
            page,
            "https://portal.fiero.org.br/imprensa/noticia/2026/05/corrida-sucesso/2536",
        )


def test_future_internal_activity_without_public_access_is_rejected() -> None:
    page = """
    <html><body>
      <div>02 de September de 2026 - 11h05</div>
      <h1>Formação de professores terá nova etapa</h1>
      <p>Os professores do SESI de Porto Velho terão novo encontro programado para 20 de setembro de 2026.</p>
      <p>A atividade é direcionada aos docentes da rede.</p>
    </body></html>
    """
    with pytest.raises(FieroParseError, match="acesso público"):
        parse_article(
            page,
            "https://portal.fiero.org.br/imprensa/noticia/2026/09/formacao-docente/2699",
        )


def test_footer_address_cannot_turn_cacoal_event_into_porto_velho() -> None:
    page = """
    <html><body>
      <div>01 de September de 2026 - 10h00</div>
      <h1>SESI promove corrida aberta ao público em Cacoal</h1>
      <p>O evento está marcado para 20 de setembro de 2026, em Cacoal.</p>
      <p>Inscrições gratuitas para o público em geral.</p>
      <footer>Rua Rui Barbosa, 1112 - Arigolândia, Porto Velho - Rondônia</footer>
    </body></html>
    """
    with pytest.raises(FieroParseError, match="evidência contextual de Porto Velho"):
        parse_article(
            page,
            "https://portal.fiero.org.br/imprensa/noticia/2026/09/corrida-cacoal/2710",
        )

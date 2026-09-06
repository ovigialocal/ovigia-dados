from datetime import UTC, datetime

from ovigia_dados.events.pvhmais import (
    canonicalize_event_url,
    discover_promoted_event_ids,
    parse_event_page,
    scan_ids_from_listing,
)


def _page(parameters: str, body: str = "") -> str:
    return (
        f"""<html><body><div id="root" data-parameters='{parameters}'></div>{body}</body></html>"""
    )


def test_canonicalize_event_url() -> None:
    assert canonicalize_event_url("/site/eventos/16?utm_source=x") == (
        "https://pvhmais.portovelho.ro.gov.br/site/eventos/16"
    )
    assert canonicalize_event_url("https://example.com/site/eventos/16") is None


def test_discover_promoted_ids_from_public_bootstrap() -> None:
    page = _page(
        "{&quot;app_sections&quot;:[{&quot;app_section_items&quot;:["
        "{&quot;action_object_type&quot;:&quot;Event&quot;,&quot;action_object_id&quot;:93}]}]}"
    )
    assert discover_promoted_event_ids(page) == [93]
    assert scan_ids_from_listing(page, bootstrap_max=100, lookahead=30)[-1] == 123


def test_parse_embedded_event_object() -> None:
    page = _page(
        "{&quot;event&quot;:{&quot;id&quot;:16,&quot;name&quot;:&quot;III Fórum de Contabilidade&quot;,"
        "&quot;start_date&quot;:&quot;2026-09-26T11:00:00-04:00&quot;,"
        "&quot;end_date&quot;:&quot;2026-09-26T21:00:00-04:00&quot;,"
        "&quot;description&quot;:&quot;Evento profissional&quot;,"
        "&quot;location&quot;:{&quot;name&quot;:&quot;Local a definir&quot;,&quot;city&quot;:&quot;Porto Velho&quot;,"
        "&quot;state&quot;:&quot;RO&quot;},&quot;status&quot;:&quot;active&quot;}}"
    )
    observed_at = datetime(2026, 9, 5, 12, tzinfo=UTC)
    event = parse_event_page(
        page,
        "https://pvhmais.portovelho.ro.gov.br/site/eventos/16",
        observed_at=observed_at,
    )

    assert event.event_id == "pvhmais-16"
    assert event.source_platform == "pvhmais"
    assert event.title == "III Fórum de Contabilidade"
    assert event.starts_at is not None
    assert event.ends_at is not None
    assert event.venue_name == "Local a definir"
    assert event.city == "Porto Velho"
    assert event.state == "RO"
    assert event.status == "scheduled"
    assert event.content_hash


def test_parse_prefers_rich_event_over_promotional_item_with_same_id() -> None:
    page = _page(
        "{&quot;promo&quot;:{&quot;id&quot;:93,&quot;name&quot;:&quot;Corrida&quot;,"
        "&quot;start_date&quot;:&quot;2026-09-01T13:00:00-03:00&quot;,"
        "&quot;action_object_type&quot;:&quot;Event&quot;,&quot;action_object_id&quot;:93},"
        "&quot;event&quot;:{&quot;id&quot;:93,&quot;name&quot;:&quot;Corrida do Aniversário da Cidade&quot;,"
        "&quot;start_date&quot;:&quot;2026-09-27T06:00:00-04:00&quot;,"
        "&quot;description&quot;:&quot;Corrida oficial&quot;}}"
    )
    event = parse_event_page(page, "https://pvhmais.portovelho.ro.gov.br/site/eventos/93")
    assert event.title == "Corrida do Aniversário da Cidade"
    assert event.starts_at is not None

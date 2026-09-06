from datetime import UTC, datetime

from ovigia_dados.events.sympla import (
    EventObservation,
    canonicalize_event_url,
    event_content_hash,
    extract_event_urls,
    is_porto_velho,
    materialize_observations,
    parse_event_page,
)


def test_extract_event_urls_deduplicates_and_removes_tracking():
    html = """
    <a href="/evento/show-em-porto-velho/123?src=home">Show</a>
    <a href="https://www.sympla.com.br/evento/show-em-porto-velho/123#tickets">dup</a>
    <a href="https://example.com/evento/outro/999">fora</a>
    <a href="/eventos/porto-velho-ro/para-voce">lista</a>
    """
    assert extract_event_urls(html) == [
        "https://www.sympla.com.br/evento/show-em-porto-velho/123"
    ]


def test_canonicalize_wayback_rewritten_event_url():
    archived = (
        "https://web.archive.org/web/20260801010203/"
        "https://www.sympla.com.br/evento/festival/456?utm_source=x"
    )
    assert canonicalize_event_url(archived) == (
        "https://www.sympla.com.br/evento/festival/456"
    )


def test_parse_json_ld_event_and_hash_is_state_based():
    html = '''<html><head><script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Event",
      "name": "Festival do Madeira",
      "startDate": "2026-09-12T19:00:00-04:00",
      "endDate": "2026-09-12T23:00:00-04:00",
      "eventStatus": "https://schema.org/EventScheduled",
      "location": {
        "@type": "Place",
        "name": "Complexo Madeira-Mamoré",
        "address": {
          "@type": "PostalAddress",
          "streetAddress": "Av. Farquar",
          "addressLocality": "Porto Velho",
          "addressRegion": "RO"
        }
      },
      "organizer": {"@type": "Organization", "name": "Produtora PVH"}
    }
    </script></head><body><h1>Festival do Madeira</h1></body></html>'''
    url = "https://www.sympla.com.br/evento/festival-do-madeira/321"
    first = parse_event_page(
        html,
        url,
        observed_at=datetime(2026, 9, 5, 20, tzinfo=UTC),
    )
    second = parse_event_page(
        html,
        url,
        observed_at=datetime(2026, 9, 5, 21, tzinfo=UTC),
    )
    assert first.event_id == "sympla-321"
    assert first.city == "Porto Velho"
    assert first.state == "RO"
    assert first.venue_name == "Complexo Madeira-Mamoré"
    assert first.organizer == "Produtora PVH"
    assert first.content_hash == second.content_hash
    assert is_porto_velho(first)


def test_visible_text_fallback_parses_portuguese_date():
    html = """
    <html><body>
      <h1>4ª MARATONA YOPRO DE PORTO VELHO</h1>
      <div>15 nov - 2026 • 04:30 &gt; 15 nov - 2026 • 11:00</div>
      <div>Porto Velho - RO</div>
    </body></html>
    """
    event = parse_event_page(
        html,
        "https://www.sympla.com.br/evento/4a-maratona-yopro-de-porto-velho/3493792",
    )
    assert event.starts_at == datetime(2026, 11, 15, 4, 30)
    assert event.ends_at == datetime(2026, 11, 15, 11, 0)
    assert event.status == "unknown"
    assert event.city == "Porto Velho"
    assert event.state == "RO"


def test_materialize_only_when_public_state_changes(tmp_path):
    observed_at = datetime(2026, 9, 5, 20, tzinfo=UTC)
    event = EventObservation(
        event_id="sympla-123",
        source_url="https://www.sympla.com.br/evento/show/123",
        title="Show",
        city="Porto Velho",
        state="RO",
        observed_at=observed_at,
    )
    identities = tmp_path / "events"
    observations = tmp_path / "observations"

    first = materialize_observations(
        [event], identities_root=identities, observations_root=observations
    )
    assert len(first) == 2

    same_state = event.model_copy(
        update={"observed_at": datetime(2026, 9, 5, 21, tzinfo=UTC)}
    )
    same_state.content_hash = event_content_hash(same_state)
    assert (
        materialize_observations(
            [same_state], identities_root=identities, observations_root=observations
        )
        == []
    )

    changed = event.model_copy(
        update={
            "observed_at": datetime(2026, 9, 5, 22, tzinfo=UTC),
            "status": "cancelled",
        }
    )
    changed.content_hash = event_content_hash(changed)
    created = materialize_observations(
        [changed], identities_root=identities, observations_root=observations
    )
    assert len(created) == 1
    assert 'status: "cancelled"' in created[0].read_text(encoding="utf-8")

from datetime import UTC, datetime

import yaml

from ovigia_dados.events.reconcile import (
    evaluate_pair,
    load_latest_observations,
    materialize_entities,
    materialize_reconciliations,
    reconcile_observations,
    text_similarity,
)
from ovigia_dados.events.shared import EventObservation, materialize_observations


def _event(
    event_id: str,
    source: str,
    title: str,
    *,
    starts_at: datetime | None,
    venue: str | None = "Complexo da Estrada de Ferro Madeira-Mamoré",
    organizer: str | None = None,
) -> EventObservation:
    return EventObservation(
        event_id=event_id,
        source_platform=source,
        source_url=f"https://example.test/{event_id}",
        title=title,
        starts_at=starts_at,
        venue_name=venue,
        city="Porto Velho",
        state="RO",
        organizer=organizer,
        observed_at=datetime(2026, 9, 6, 10, tzinfo=UTC),
    )


def _frontmatter(path):
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


def test_text_similarity_ignores_accents_stopwords_and_punctuation() -> None:
    assert text_similarity("Show de Talentos — Zona Sul", "SHOW TALENTOS: ZONA SUL") == 1.0


def test_same_date_strong_title_becomes_equivalent() -> None:
    when = datetime(2026, 9, 12, 20, tzinfo=UTC)
    left = _event("pvhmais-101", "pvhmais", "Show de Talentos — Zona Sul", starts_at=when)
    right = _event("sympla-999", "sympla", "Show Talentos Zona Sul", starts_at=when)

    match = evaluate_pair(left, right)

    assert match is not None
    assert match.decision == "equivalent"
    assert match.same_local_date is True
    assert match.left_content_hash
    assert match.right_content_hash


def test_identical_event_on_different_date_is_review_not_equivalent() -> None:
    left = _event(
        "pvhmais-102",
        "pvhmais",
        "Festival do Madeira",
        starts_at=datetime(2026, 9, 12, 20, tzinfo=UTC),
    )
    right = _event(
        "sympla-1000",
        "sympla",
        "Festival do Madeira",
        starts_at=datetime(2026, 9, 19, 20, tzinfo=UTC),
    )

    match = evaluate_pair(left, right)

    assert match is not None
    assert match.decision == "review"
    assert match.same_local_date is False


def test_missing_date_never_auto_links() -> None:
    left = _event("pvhmais-103", "pvhmais", "Mostra Amazônica", starts_at=None)
    right = _event(
        "sympla-1001",
        "sympla",
        "Mostra Amazônica",
        starts_at=datetime(2026, 9, 21, 12, tzinfo=UTC),
    )

    match = evaluate_pair(left, right)

    assert match is not None
    assert match.decision == "review"


def test_latest_observation_is_loaded_from_append_only_history(tmp_path) -> None:
    older = _event(
        "pvhmais-104",
        "pvhmais",
        "Feira da Cidade",
        starts_at=datetime(2026, 9, 20, 12, tzinfo=UTC),
    )
    newer = older.model_copy(
        update={
            "starts_at": datetime(2026, 9, 21, 12, tzinfo=UTC),
            "observed_at": datetime(2026, 9, 7, 10, tzinfo=UTC),
            "content_hash": "",
        }
    )
    newer.model_post_init(None)
    materialize_observations(
        [older, newer],
        identities_root=tmp_path / "events",
        observations_root=tmp_path / "observations",
    )

    loaded = load_latest_observations(tmp_path / "observations")

    assert len(loaded) == 1
    assert loaded[0].starts_at == datetime(2026, 9, 21, 12, tzinfo=UTC)


def test_reconciliation_is_append_only_per_observed_state(tmp_path) -> None:
    when = datetime(2026, 9, 12, 20, tzinfo=UTC)
    left = _event("pvhmais-105", "pvhmais", "Concerto no Madeira", starts_at=when)
    right = _event("sympla-1002", "sympla", "Concerto no Madeira", starts_at=when)
    first = reconcile_observations([left, right], evaluated_at=datetime(2026, 9, 6, 10, tzinfo=UTC))
    created = materialize_reconciliations(first, tmp_path)

    assert len(created) == 1
    assert materialize_reconciliations(first, tmp_path) == []

    changed = right.model_copy(update={"venue_name": "Teatro Guaporé", "content_hash": ""})
    changed.model_post_init(None)
    second = reconcile_observations([left, changed], evaluated_at=datetime(2026, 9, 7, 10, tzinfo=UTC))
    created_again = materialize_reconciliations(second, tmp_path)

    assert len(created_again) == 1
    assert created_again[0] != created[0]


def test_canonical_entity_keeps_id_when_third_source_arrives(tmp_path) -> None:
    when = datetime(2026, 9, 12, 20, tzinfo=UTC)
    first = _event("pvhmais-106", "pvhmais", "Noite Cultural", starts_at=when)
    second = _event("sympla-1003", "sympla", "Noite Cultural", starts_at=when)
    third = _event("sesc-77", "sesc", "Noite Cultural", starts_at=when)
    rec_ab = evaluate_pair(first, second, evaluated_at=datetime(2026, 9, 6, 10, tzinfo=UTC))
    rec_bc = evaluate_pair(second, third, evaluated_at=datetime(2026, 9, 7, 10, tzinfo=UTC))

    assert rec_ab is not None and rec_ab.decision == "equivalent"
    assert rec_bc is not None and rec_bc.decision == "equivalent"

    created = materialize_entities(
        [rec_ab],
        tmp_path,
        materialized_at=datetime(2026, 9, 6, 10, tzinfo=UTC),
    )
    canonical_path = created[0]
    first_payload = _frontmatter(canonical_path)

    changed = materialize_entities(
        [rec_ab, rec_bc],
        tmp_path,
        materialized_at=datetime(2026, 9, 7, 10, tzinfo=UTC),
    )
    second_payload = _frontmatter(changed[0])

    assert changed[0] == canonical_path
    assert second_payload["canonical_event_id"] == first_payload["canonical_event_id"]
    assert set(second_payload["member_event_ids"]) == {"pvhmais-106", "sympla-1003", "sesc-77"}
    assert second_payload["created_at"] == first_payload["created_at"]

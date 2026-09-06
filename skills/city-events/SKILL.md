# Skill: city-events

Use this procedure when adding, operating or reconciling a public event source for Porto Velho.

1. Read `specs/city-event.md`, `specs/event-observation.md`, `specs/event-reconciliation.md`, `specs/event-entity.md` and `wiki/city-event-sources.md`.
2. Treat each platform's public identifier as source identity. `sympla-*`, `pvhmais-*` and future source IDs remain independently traceable even after reconciliation.
3. Acquire only public, reproducible surfaces. Prefer documented APIs or public HTML. Do not depend on private credentials or undocumented internal endpoints when a stable public page works.
4. Normalize each state into the shared `EventObservation` contract and persist with `materialize_observations`.
5. Create one `city-event` identity per source event and append `event-observation` only when the normalized content hash changes.
6. Preserve uncertainty: missing organizer, location or status stays unknown instead of being inferred.
7. If a source is city-scoped by contract, document that scope. Otherwise verify Porto Velho from the event itself before materializing.
8. Add fixtures that represent the source's real public shape, including at least one malformed or incomplete case.
9. Schedule acquisition at a cadence proportional to change frequency and source cost; avoid needless polling.
10. Record stable source quirks and acquisition lessons in `wiki/city-event-sources.md`.

## Cross-source reconciliation

Run `scripts/events/reconcile_city_events.py` only over the latest observation of each source identity.

- Never merge by title alone.
- Automatic equivalence requires compatible temporal evidence; missing start date never auto-links.
- Same title with a different date can be a reschedule, so materialize `decision: review` instead of silently joining or discarding it.
- Venue and organizer strengthen a match but do not erase disagreement between sources.
- `event-reconciliation` is append-only per pair of observation hashes. A material change on either source creates new reconciliation evidence.
- `event-entity` sits above source IDs. Once created, keep its `canonical_event_id` stable as new sources are added.
- If an automatic component would join two already-existing canonical entities, stop automatic consolidation for that component and leave it for explicit review.

The source observations remain the provenance of record. Canonical entities are derived navigation/aggregation objects, not replacements for what each source actually published.

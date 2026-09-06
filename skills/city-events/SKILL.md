# Skill: city-events

Use this procedure when adding or operating a public event source for Porto Velho.

1. Read `specs/city-event.md`, `specs/event-observation.md` and `wiki/city-event-sources.md`.
2. Treat each platform's public identifier as source identity; do not merge two platforms by title alone.
3. Acquire only public, reproducible surfaces. Prefer documented APIs or public HTML. Do not depend on private credentials or undocumented internal endpoints when a stable public page works.
4. Normalize each state into the shared `EventObservation` contract and persist with `materialize_observations`.
5. Create one `city-event` identity per source event and append `event-observation` only when the normalized content hash changes.
6. Preserve uncertainty: missing organizer, location or status stays unknown instead of being inferred.
7. If a source is city-scoped by contract, document that scope. Otherwise verify Porto Velho from the event itself before materializing.
8. Add fixtures that represent the source's real public shape, including at least one malformed or incomplete case.
9. Schedule acquisition at a cadence proportional to change frequency and source cost; avoid needless polling.
10. Record stable source quirks and acquisition lessons in `wiki/city-event-sources.md`.

Cross-source reconciliation is a separate step. Matching title is evidence, not identity; use date/time, venue, organizer and source links before proposing equivalence.

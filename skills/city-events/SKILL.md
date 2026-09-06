# Skill: city-events

Use this procedure when adding, operating or reconciling a public event source for Porto Velho.

1. Read `specs/city-event.md`, `specs/event-observation.md`, `specs/event-reconciliation.md`, `specs/event-entity.md` and `wiki/city-event-sources.md` plus any source-specific wiki named by the adapter.
2. Treat each platform's public identifier as source identity. `sympla-*`, `pvhmais-*`, `sescro-*` and future source IDs remain independently traceable even after reconciliation.
3. Acquire only public, reproducible surfaces. Prefer documented APIs or public HTML. Do not depend on private credentials or undocumented internal endpoints when a stable public page works.
4. Normalize each state into the shared `EventObservation` contract and persist with `materialize_observations`.
5. Create one `city-event` identity per source event and append `event-observation` only when the normalized content hash changes.
6. Preserve uncertainty: missing organizer, location or status stays unknown instead of being inferred.
7. Preserve temporal precision. Use `starts_at` / `ends_at` only when the source publishes a trustworthy clock time. Use `starts_on` / `ends_on` for date-only schedules; never invent midnight just to satisfy a datetime field.
8. If a source is city-scoped by contract, document that scope. Otherwise verify Porto Velho from the event itself before materializing. Never use a site-wide footer address as event-location evidence.
9. Add fixtures that represent the source's real public shape, including at least one malformed, incomplete or internally conflicting case.
10. Schedule acquisition at a cadence proportional to change frequency and source cost; avoid needless polling.
11. Record stable source quirks and acquisition lessons in the source wiki. If a structured widget conflicts with editorial text, define an explicit precedence rule and lock it with a regression fixture before automating.

## Cross-source reconciliation

Run `scripts/events/reconcile_city_events.py` only over the latest observation of each source identity.

- Never merge by title alone.
- Automatic equivalence requires compatible temporal evidence; a valid `starts_on` counts as temporal evidence just like the local date of `starts_at`.
- Missing start date never auto-links.
- Same title with a different date can be a reschedule, so materialize `decision: review` instead of silently joining or discarding it.
- Venue and organizer strengthen a match but do not erase disagreement between sources.
- `event-reconciliation` is append-only per pair of observation hashes. A material change on either source creates new reconciliation evidence.
- `event-entity` sits above source IDs. Once created, keep its `canonical_event_id` stable as new sources are added.
- If an automatic component would join two already-existing canonical entities, stop automatic consolidation for that component and leave it for explicit review.

The source observations remain the provenance of record. Canonical entities are derived navigation/aggregation objects, not replacements for what each source actually published.

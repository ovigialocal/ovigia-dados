# AGENTS.md

## Operating model: WikiSkill loop

`ovigia-dados` must operate as a compounding agent system inspired by Google Research's WikiSkill pattern. The repository separates three layers:

1. `raw/` — immutable execution evidence and source observations;
2. `wiki/` — persistent accumulated knowledge distilled from runs;
3. `skills/` — executable procedures used by agents and workflows.

The canonical loop is:

```text
observe/task
  -> execute with current skills
  -> preserve raw evidence
  -> evaluate outcome
  -> consolidate reusable knowledge into wiki
  -> propose skill creation/update from wiki
  -> validate skill against evidence/tests
  -> accept or rollback executable skill
  -> retain learned wiki knowledge either way
  -> next iteration
```

### Non-negotiable rules

- Raw evidence is append-only/immutable. Never rewrite a failed run to make history look clean.
- The wiki compounds across iterations. Do not reset it when a proposed skill fails.
- Skills are executable policy, not memory dumps. Keep them concise and procedural.
- Wiki entries record successful strategies, failure modes, workarounds, source quirks, detector behavior, schema lessons and operational constraints.
- A failed skill proposal is rolled back from `skills/`, but the reason it failed remains in `wiki/` (asymmetric rollback).
- Do not promote one-off noise into a skill. Prefer repeated or materially generalizable evidence.
- Before creating a skill, search existing skills and wiki concepts; improve an existing skill when the purpose is the same.
- Every accepted skill update should identify the wiki evidence that motivated it and the validation that justified acceptance.
- Every dataset/detector implementation should feed the loop: execution produces evidence; evidence updates the wiki; wiki may evolve skills.
- `okf-parser` remains the structural authority for OKF bundles/specs and should be used when modeling new knowledge contracts.
- `ovigialocal/ovigialocal.github.io` owns the canonical `PublicEdition` registry and its `default_edition_id`. Data collectors and detectors may declare an `edition_id` consumer scope, but this repository must not copy the registry or decide the public fallback.

### Canonical persistence formats

Use OKF Markdown as the default persistent format for semantic state: configuration, registries, entities, signals, queues, decisions, manifests and other knowledge that benefits from identity, provenance or relations. For large tabular/analytical datasets, prefer Parquet; use CSV when simple tabular interoperability is the stronger requirement.

JSON/JSONL may exist at an external API or transiently inside a process, but must not become a new authored or canonical persistence surface. Do not add persistent JSON/JSONL when OKF, Parquet or CSV expresses the same contract. When touching a legacy persistent JSON/JSONL boundary, prefer migrating it rather than extending it, provided immutable historical evidence is not rewritten.

Raw evidence preserves what was actually observed: this rule does not require rewriting immutable historical payloads received as JSON, nor does it prohibit decoding JSON returned by an external API in memory.

### Wayback preservation queue

`ovigia-dados` is the public execution boundary for Wayback preservation requested by O Vigia. The queue is represented only as OKF concepts under `knowledge/wayback/`:

- `archive-request` records a public URL to preserve;
- `archive-result` records one terminal service outcome and must name the request's parser-owned `concept_id` in `request_concept_id` while also linking it through `sources[].resource`;
- the pending queue is derived as requests without terminal results.

Do not create or restore `.txt`, JSON or YAML queue files. Do not duplicate a request's identity with a `request_id` field. A transport/runtime failure before the Internet Archive answers leaves the request pending; it is not a terminal archive failure.

The private newsroom may enqueue only public URLs here. It must not copy private story IDs, hypotheses, drafts, human-source identities or unpublished editorial strategy into this public repository.

### Per-session behavior

At the start of a substantive agent session:

1. read `AGENTS.md`;
2. inspect relevant `wiki/` pages and skills before acting;
3. execute the task using current skills;
4. preserve new raw evidence when materially useful;
5. before finishing, ask internally: what did this run teach that should persist beyond this run?
6. update `wiki/` for reusable knowledge;
7. if the knowledge changes a repeatable procedure, update/create the corresponding skill and validate it.

### Public-repository boundary

This repository is public. Never persist private newsroom hypotheses, unpublished editorial strategy, human-source identities, secrets, credentials, or private drafts in raw/wiki/skills. Only public/reproducible data-engineering and detector knowledge belongs here.

See `docs/WIKISKILL_LOOP.md` for the detailed lifecycle.

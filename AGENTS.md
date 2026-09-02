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
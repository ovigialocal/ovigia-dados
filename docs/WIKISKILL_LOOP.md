# WikiSkill loop in ovigia-dados

This repository follows the operating idea from **WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution** (Google Research, 2026): execution experience, accumulated knowledge and executable skills are separate artifacts that co-evolve.

## Three layers

### raw/
Immutable or append-only evidence from execution: source observations, detector reports, failed acquisitions, validation outputs and representative traces that are useful for learning. Raw is evidence, not guidance.

### wiki/
Persistent Markdown knowledge distilled from raw evidence. Typical pages document source behavior, recurring failure modes, successful acquisition patterns, schema decisions, normalization lessons, detector calibration, false-positive patterns and operational workarounds.

The wiki is cumulative. Rejected experiments still improve it.

### skills/
Executable agent procedures. A skill tells an agent how to perform a repeatable task. It should be derived from accumulated evidence, not from a single anecdote.

## Evolution cycle

1. **Execute** — use the current skill set on a real task.
2. **Capture** — preserve material evidence from the run in `raw/` or another canonical reproducible artifact.
3. **Evaluate** — determine what worked, failed, regressed or created false positives.
4. **Consolidate** — update the persistent wiki with the reusable lesson and provenance.
5. **Propose** — create or revise an executable skill only when the accumulated knowledge warrants it.
6. **Validate** — test the proposed skill against relevant fixtures, historical cases, schemas and repository gates.
7. **Accept or rollback** — keep the skill only if validation supports it.
8. **Retain knowledge** — even after rollback, keep the wiki lesson explaining why the proposal failed.
9. **Repeat** — the next run starts with a richer wiki and, when justified, improved skills.

## Asymmetric rollback

Skill state is reversible; learned knowledge is cumulative.

```text
bad skill proposal
  -> rollback skill
  -> preserve failure evidence
  -> preserve wiki lesson
  -> avoid repeating the same bad proposal blindly
```

## Skill impact tracking

For meaningful skill changes, record enough information to answer:

- what evidence motivated the change;
- which wiki page captures the lesson;
- which skill/version changed;
- what validation was run;
- whether the change improved, regressed or had no measurable effect;
- whether it was accepted or rolled back.

This may be implemented as OKF documents or a generated index, but should remain human-readable and git-auditable.

## Application to datasets

Every dataset vertical should naturally feed this loop. Example:

```text
PNCP collector run
  -> raw acquisition/validation evidence
  -> wiki lesson about pagination/schema/source behavior
  -> improve acquisition skill
  -> rerun validation
```

Likewise for detector tuning:

```text
large-local-contract-v1 emits false positives
  -> preserve examples and baseline
  -> wiki documents failure mode
  -> evolve detector-analysis skill
  -> validate on historical sample
```

The same applies to API-Football, CNES, CadÚnico, ObrasGov and future sources.

## Relationship with OKF

Use `okf-parser` when new persistent concepts need a structural contract. The wiki can remain readable Markdown, but concepts that become governed artifacts (dataset, snapshot, detector, signal, skill-impact record, etc.) should be modeled through the repository's OKF specs rather than ad-hoc YAML.

## Automation boundary

GitHub Actions may execute deterministic collectors, validators and detectors. Skill evolution itself must remain evidence-driven and reviewable: an automated run may propose a skill change, but acceptance requires repository validation and a traceable git change.

The public repo must never accumulate private newsroom material.
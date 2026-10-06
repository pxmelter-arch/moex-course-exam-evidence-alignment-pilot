# Phase 2.7 Formal Identity Bridge Audit

## Scope

```text
formal projection = 176
normalized exam outlines = 542
duplicate subject_name groups = 36
```

## Identity status

| Status | Records |
|---|---:|
| Exact unique | 13 |
| Ambiguous | 20 |
| Weak | 143 |

The 20 ambiguous records include exact subject-name matches with duplicate outline variants and strong machine alias candidates. The 143 weak records do not have a unique exact title or a sufficiently strong deterministic alias signal.

## Candidate-generation recovery

```text
exact subject records recovered from the previous course-level gate = 3
```

All three recovered records are titled `計算機概論` and point to the same deterministic outline record. They are added to the expanded candidate pool only; no truth label or promotion is created.

## Policy

Machine aliases are:

```text
machine_candidate_review_required
human_adjudication = not_available
promotion = blocked
```

Duplicate `subject_name` values remain separate outline records. Their `type`, `applicable_exams`, content, and source evidence must be reviewed independently.

## Release state

```text
formal_alignment = not_started
qdrant_ingest = false
```

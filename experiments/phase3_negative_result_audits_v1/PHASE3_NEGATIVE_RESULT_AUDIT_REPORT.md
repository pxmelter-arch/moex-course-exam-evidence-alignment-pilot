# Phase 3 Negative-result Audits

## Scope

This audit investigates the current negative retrieval result without automatic fixes or promotion:

```text
chapter hierarchy refinement
content contamination
coverage threshold sensitivity
reranking weight ablation
independent source corroboration
human/adjudication review
```

## Results

### 1. Chapter hierarchy

```text
syllabus chunks = 4750
syllabus chapter unresolved = 4750
outline items = 2573
outline chapter unresolved = 2573
```

The current extraction has topic candidates but no reliable chapter hierarchy. This is an identified limitation, not a fabricated hierarchy.

### 2. Topic contamination

```text
syllabus flagged chunks = 632 / 4750
outline flagged items = 57 / 2573
```

Syllabus flagged categories include assessment, administrative text, schedule/note, teaching method, and textbook language. These are audit flags only; they are not silently deleted from raw artifacts.

### 3. Coverage threshold sensitivity

| Threshold | Top-1 | Top-10 |
|---:|---:|---:|
| 0.30 | 22 / 176 | 27 / 176 |
| 0.42 | 22 / 176 | 27 / 176 |
| 0.55 | 22 / 176 | 27 / 176 |
| 0.65 | 22 / 176 | 27 / 176 |

Within this range, threshold changes do not alter the exact-subject proxy ranking.

### 4. Weight ablation

| Configuration | Top-1 | Top-10 |
|---|---:|---:|
| Current | 22 / 176 | 27 / 176 |
| Coverage-heavy | 22 / 176 | 27 / 176 |
| Lexical-heavy | 22 / 176 | 27 / 176 |
| Dense-heavy | 22 / 176 | 27 / 176 |
| Identity removed | 2 / 176 | 27 / 176 |

Removing identity reduces top-1 strongly, confirming that current ranking is identity-dependent. This is a diagnostic result, not a claim that identity is ground truth.

### 5. Independent corroboration

```text
outline source path = one catalog path for 1760 packs
catalog source labels = technical 1495 / administrative 293
independent corroboration ready = 0
```

Technical versus administrative page labels are not independent source families. Same catalog provenance is not independent corroboration.

### 6. Human/adjudication review

```text
review queue = 1760
machine labels created = 0
```

The queue contains null human labels and explicit adjudication fields. No machine inference is promoted to truth.

## Status

```text
formal_alignment = not_started
promotion = blocked
qdrant_ingest = false
```

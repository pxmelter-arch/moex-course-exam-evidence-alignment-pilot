# Phase 2.5 Formal Retrieval Ablation

## Scope

```text
formal syllabus projection = 176
normalized exam outlines = 542
```

The ablation stays on the formal lane and does not use curated 600, 520, or Priority-5 373 records.

## Results

| Method | Top-1 exact subject | Top-10 exact subject |
|---|---:|---:|
| Title identity | 27 / 176 | 27 / 176 |
| Topic-only | 11 / 176 | 17 / 176 |
| Content + topic | 15 / 176 | 19 / 176 |
| Section-aware hybrid | 27 / 176 | 27 / 176 |

## Interpretation

1. The current hybrid's exact retrieval result is primarily preserved by the course-title identity signal.
2. Topic-only and content+topic signals produce candidates but do not independently recover the same exact-subject result.
3. Adding raw syllabus content without section weighting is not sufficient evidence of improved alignment.
4. The formal syllabus text remains useful for explainable candidate components and review, even when it does not improve exact-title retrieval.
5. No result is a gold label or alignment accuracy; all outputs remain candidate diagnostics.

## Release state

```text
formal_alignment = not_started
candidate_only = true
promotion_status = blocked_pending_alignment_evidence
qdrant_ingest = false
```

Artifacts:

```text
ablation_report.json
ablation_results.jsonl
```

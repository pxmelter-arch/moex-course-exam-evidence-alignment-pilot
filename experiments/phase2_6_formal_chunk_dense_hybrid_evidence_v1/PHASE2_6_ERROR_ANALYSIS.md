# Phase 2.6 Formal Error Analysis

## Stage breakdown

| Category | Records |
|---|---:|
| No exact normalized course-title subject in 542-outline catalog | 149 |
| Exact subject survives course-level top-50 gate and appears in top-10 | 24 |
| Exact subject exists but is excluded by course-level gate | 3 |
| Exact subject reranked outside top-10 after passing gate | 0 |

The 24 records include the 22 top-1 exact results and two additional top-10-only cases.

## Interpretation

The principal bottleneck is not dense reranking for this diagnostic proxy. It is identity coverage between the formal course title and the normalized outline `subject_name` catalog:

```text
176 formal courses
27 have an exact normalized subject-name proxy
149 do not
```

There are only three observable course-level gate misses among the 27 exact-title proxy records. Therefore, changing dense weights alone is unlikely to improve all 176 records. The next research step should address conservative identity/alias bridging and preserve ambiguous cases rather than automatically merging them.

This is not human alignment truth: exact normalized title is only a retrieval diagnostic proxy, and no gold labels are available.

## Release state

```text
formal_alignment = not_started
promotion_status = blocked
qdrant_ingest = false
```

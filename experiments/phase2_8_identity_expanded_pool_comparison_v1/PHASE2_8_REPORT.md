# Phase 2.8 Formal Identity-expanded Candidate Pool Comparison

## Scope

```text
formal courses = 176
normalized exam outlines = 542
local embedding = BAAI/bge-small-zh-v1.5
```

The lexical, chunk, dense, and hybrid scoring configuration is held constant. Only the candidate pool changes.

```text
original = Phase 2.6 course-level top-50 pool
expanded = original pool + exact identity candidates + top-5 machine alias candidates
```

## Paired results

| Metric | Original top-50 | Identity-expanded | Delta |
|---|---:|---:|---:|
| Top-1 exact subject | 22 / 176 | 22 / 176 | 0 |
| Top-10 exact query coverage | 24 / 176 | 27 / 176 | +3 |
| Ambiguous candidates in top-10 | 1750 | 1747 | -3 |

## Gate-miss recovery

All 3 previously identified course-level gate misses were recovered:

```text
course_title = 計算機概論
recovered outline = OUT-62b98cd63f9cf230f308
expanded rank = 6 for all three records
```

They did not become top-1 results. The expansion therefore improves recall at top-10, not top-1 ranking.

## Ambiguity finding

The identity expansion did not increase the aggregate top-10 ambiguous count. It decreased it by three because the recovered exact candidates displaced three previously ambiguous entries. This does not mean the alias candidates are validated; all machine aliases remain review-required.

## Interpretation

The original top-50 course gate was responsible for the three observed exact-title misses. Conservative exact identity expansion recovers those candidates without changing the dense/lexical scoring function. Further top-1 improvement requires ranking or evidence disambiguation, not only candidate expansion.

Exact normalized subject remains a diagnostic proxy, not human alignment truth.

## Release state

```text
retrieval_status = candidate_only
formal_alignment = not_started
promotion_status = blocked
qdrant_ingest = false
```

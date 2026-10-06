# Curated 600 Section-aware Hybrid Retrieval

## Scope

```text
curated packet: 600
content-bearing retrieval: 520
partial abstention: 80
normalized exam outlines: 542
```

Input packet:

```text
commit: a22f8e7
path: release/curated_experiment_20261006/experiment_projection.jsonl
release_status: experimental_only
```

## Section extraction

Curated records contain parser contamination: `objectives` may include `Course Outline` and `Course schedule`, while the raw `outline` field may contain only a header fragment. The runner therefore extracts labeled sections from the objectives blob and records fallback usage instead of trusting one field blindly.

Views:

```text
topic_text = extracted outline + objectives + schedule
content_text = extracted objectives + outline + schedule
```

No missing section is imputed.

## Retrieval

Only `content_status=content_bearing` records are retrieved. `partial` records are abstained by default and written to a separate queue.

Weights:

```text
title_identity       0.30
title_similarity      0.20
topic_score           0.20
content_bm25         0.20
remarks               0.10
```

Topic score:

```text
core_knowledge       0.60
outline              0.40
```

## Results

| Metric | Result |
|---|---:|
| Curated records | 600 |
| Content-bearing retrieval records | 520 |
| Partial records abstained | 80 |
| Normalized outlines | 542 |
| Top candidate exact | 12 |
| Top candidate ambiguous | 491 |
| Top candidate weak | 17 |

## Interpretation

- Most candidates remain `ambiguous`; this is expected because title variants, incomplete identity and outline-source duplication have not been human-adjudicated.
- The 80 partial records are not silently imputed and are excluded from the content retrieval score.
- This is an experimental candidate retrieval result, not alignment accuracy or a source truth score.
- The curated packet remains outside formal/default/Qdrant release boundaries.

## Artifacts

```text
retrieval_report.json
content_bearing_results.jsonl
partial_abstention_queue.jsonl
```

## Release state

```text
retrieval_status = candidate_only
promotion_status = blocked_experimental_only
qdrant_ingest = false
```

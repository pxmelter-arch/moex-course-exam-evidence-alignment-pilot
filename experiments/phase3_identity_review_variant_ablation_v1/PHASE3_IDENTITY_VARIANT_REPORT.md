# Phase 3 Identity Review and Variant-aware Ranking

## Identity review lane

```text
failure-focused identity review queue = 149
weak identity = 143
ambiguous alias = 6
machine decisions created = 0
```

The 5 ranker-miss cases are kept in a separate variant experiment and are not mixed into the 149 identity-coverage queue.

## Variant-aware ranking experiment

Scope:

```text
ranker miss cases = 5
course title = 計算機概論
exact candidate exists in expanded top-10
current exact candidate rank = 5–6
```

Diagnostic proxy metrics over all 176 records:

| Configuration | Top-1 | Top-10 |
|---|---:|---:|
| Current coverage reranking | 22 / 176 | 27 / 176 |
| Title boost 0.20 | 27 / 176 | 27 / 176 |
| Title boost 0.50 | 27 / 176 | 27 / 176 |
| Hard exact-first | 27 / 176 | 27 / 176 |

The improvement is proxy-driven because `title_exact` is a diagnostic feature. It is not evidence of formal alignment truth. The experiment shows that identity-aware ranking can recover the five cases after candidate recall, but it does not establish that exact title is the correct exam variant.

```text
formal_alignment = not_started
promotion = blocked
qdrant_ingest = false
```

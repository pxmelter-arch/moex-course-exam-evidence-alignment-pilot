# Phase 3 Failure Localization

## Scope

```text
formal records = 176
candidate pool = identity-expanded top-10
proxy = exact normalized subject name
```

The proxy is diagnostic only; it is not a human alignment label.

## Localization result

| Failure class | Count |
|---|---:|
| Proxy top-1 exact | 22 |
| Proxy ranker miss: exact candidate exists in expanded top-10 but is not top-1 | 5 |
| Proxy identity/catalog coverage miss: no exact candidate in expanded top-10 | 149 |

## Identity status cross-tab

```text
exact unique + proxy top-1 exact = 8
ambiguous duplicate + proxy top-1 exact = 14
exact unique + proxy ranker miss = 5
ambiguous alias + identity/catalog coverage miss = 6
weak / no unique exact or strong alias + identity/catalog coverage miss = 143
```

## Interpretation

### Data / identity coverage problem

The strongest observed limitation is identity/catalog coverage:

```text
143 / 176 = weak identity bridge
6 / 176 = ambiguous machine alias requiring review
```

This means the system often cannot establish a reliable course-title-to-outline identity bridge before content ranking. It does not prove that the underlying outline is absent or that the syllabus is wrong; it identifies a naming, alias, scope, or catalog-coverage gap.

Representative cases:

```text
網路安全 → 資通網路（原：電腦網路）、（原：資料通訊）
Database Systems → 資料庫應用
中文閱讀與表達(一) → 資料結構
```

These are not valid truth decisions; they are failure examples showing that the current identity proxy does not cover the course naming space.

### Method / ranking problem

The 5 ranker-miss cases all correspond to `計算機概論` records. The exact unique outline candidate exists in the expanded top-10 but appears at rank 5–6. This is evidence of a ranking / variant-selection problem after candidate recall, not a missing-candidate problem.

### Contamination

Course-side contamination is present in the failure set, but the current audit only establishes association, not causality. For example, `網路安全` has 6 contamination-lane chunks and 33 content-lane chunks; its top result has low bidirectional topic coverage (`0.137821`) and is not an exact title match. This supports a data-lane diagnostic hypothesis, but requires a contamination-excluded paired experiment before causal attribution.

## What is not proven

```text
formal alignment truth = not established
method completely correct = not established
data completely wrong = not established
human adjudication = not completed
independent corroboration = not available
```

## Next controlled experiments

```text
1. rerun with contamination lane excluded / down-weighted
2. evaluate identity-bridge recall separately from ranking
3. disambiguate duplicate outline variants using scope and content evidence
4. acquire independent source families
5. adjudicate the 5 ranker-miss cases and representative weak-identity cases
```

```text
promotion = blocked
qdrant_ingest = false
```

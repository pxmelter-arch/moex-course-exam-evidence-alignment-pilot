# Phase 3 Contamination-aware Paired Ablation

## Fixed scope

```text
formal records = 176
expanded candidates = 1760
local embedding = BAAI/bge-small-zh-v1.5
coverage threshold = 0.42
```

## Results

| Lane | Top-1 | Top-10 | Top-1 changed vs all-content |
|---|---:|---:|---:|
| All-content | 22 / 176 | 27 / 176 | baseline |
| Content-only | 22 / 176 | 27 / 176 | 12 / 176 |
| Downweight contamination to 0.25 | 22 / 176 | 27 / 176 | 2 / 176 |

Content-only changes individual top-1 candidates but does not improve aggregate diagnostic proxy performance. Downweighting is more conservative and changes fewer cases.

## Interpretation

Contamination is a real data-lane property and affects local ranking in some records, but this paired experiment does not establish it as the dominant cause of the negative result. Identity/catalog coverage remains the dominant observed limitation.

```text
formal_alignment = not_started
promotion = blocked
qdrant_ingest = false
```

# Candidate Text Normalization / Chunking Pilot

## Input

```text
candidate: structured_content_600_candidate_v1
source_commit: 6454e22c2ad00087d62481171352738eb3396bad
source_path: output/unified_dataset/round26_20261004/structured_content_600.json
```

## Actual result

```text
records: 600
primary content_bearing records: 520
partial sensitivity records: 80
chunks: 2661
primary chunks: 2429
partial chunks: 232
```

Section counts:

```text
objectives: 379
outline: 529
assessment: 347
textbook: 311
reference: 449
prerequisite: 108
course_description: 497
document fallback: 41
```

Character statistics after deterministic NFKC and whitespace normalization:

```text
min: 10
max: 4935
mean: 339.23
```

## Interpretation

這是 metadata-only chunk manifest，不將 source text 複製到 experiment repository。每個 chunk 保留 `normalized_text_sha256`、`source_raw_sha256`、lane、section、content status 與 hash status。

`partial` lane 不與 `content_bearing` lane 合併計算。此 pilot 尚未執行 embedding、hybrid retrieval、exam alignment 或 human adjudication，因此 `promotion_status=blocked`。

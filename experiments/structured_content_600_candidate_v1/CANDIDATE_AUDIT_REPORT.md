# Structured Content 600 Candidate Audit

## 定位

```text
candidate_name: structured_content_600_candidate_v1
source_commit: 6454e22c2ad00087d62481171352738eb3396bad
source_file_sha256: f0f6197c0eb33ceee03a9e2ff08d2e403f60e0609cdd263964a3542b57c9d2e0
records: 600
```

本資料是 additive structured-content candidate overlay，不取代 Phase 0 的 176 筆 GitHub formal scope，也不代表 exam alignment truth。

## 實際 lane

```text
content_bearing: 520
partial: 80
zero_content_chars: 5
hash_verified: 511
hash_mismatch: 89
provenance_status_null: 568
official_url_missing: 32
provenance_review_queue: 600
```

## Source record status

```text
quarantine: 370
staged_course_evidence: 150
staged: 57
quarantine_candidate_provenance_pending: 23
```

## 可使用範圍

`content_bearing` 520 筆可進入 NLP normalization、chunking 與 content retrieval diagnostic；`partial` 80 筆必須作為獨立 sensitivity lane，不可與完整內容 lane 混合計算單一結果。

## 必須保持 blocked 的部分

```text
formal promotion
Default replacement
Qdrant formal ingest
formal exam alignment
human truth claim
evidence-grade release
```

原因包括：89 筆 declared hash mismatch、600 筆均未達 provenance verified、370 筆 quarantine、150 筆 staged course evidence，以及 32 筆缺少 official URL。

## Audit policy

```text
record_scope = candidate_overlay
machine_output_is_truth = false
human_adjudication_available = false
promotion_status = blocked
```

`content_text` 存在不等於 source identity 已解析；`hash_status=verified` 也不等於 exam alignment 已驗證。所有 provenance 非 `verified` 的 record 均進入 review queue。

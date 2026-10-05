# Phase 2.3B Priority-5 Staged Input Freeze and Lane Comparison

## 1. Frozen source composition

固定 source commit：

```text
1f2a2e635d61e01b5788a3c8c5b66adeb5c7e9db
```

| Source | Pinned path | Selection rule | Count |
|---|---|---|---:|
| SCH022 | `output/acquisition/round26_20261005_formal_retry5/structured.jsonl` | `content_status=content_bearing` | 17 |
| SCH026 | `output/acquisition/sch026_pu_114_bounded_acquisition.json` | all official detail records | 89 |
| SCH006 | `output/fresh/live_20261005/SCH006_live_closeout.json` | `content_status=content_bearing` | 6 |
| SCH014 | `output/crawler_rebuild_2026-10-04/course_acquisition/sch014_ntu_1141_candidate_review.json` | `content_signal=true` | 261 |
| **Total** |  |  | **373** |

## 2. Freeze audit

```text
staged records: 373
outline records: 542
primary content-bearing records: 520
overlap with primary: 302
duplicate within staged: 54
quarantine: 251
provenance incomplete: 0
formal promotions: 0
```

`302 overlap` 表示這批 Priority-5 records 不能被當成 373 筆全新資料；它們仍可作 staged evidence / retrieval diagnostic，但不應直接計入 canonical document delta。

`251 quarantine` 保留 upstream identity/provenance gate 狀態；quarantine 不等於內容不存在，也不被自動移除。

## 3. Manifest fields

每筆 manifest 保留：

```text
record_id
source_id
source_native_id
school_id
course_title
content_status
raw_sha256
raw_artifact_path
source_record_status
source_native_status
quarantine
provenance_status
identity_status
deduplication_decision
official_url
```

## 4. Staged retrieval: 373 × 542

| Method | Top-10 有結果 | Top-1 exact subject | Top-10 exact subject |
|---|---:|---:|---:|
| Exact title | 79 / 373 | 79 / 373 | 79 / 373 |
| TF-IDF | 373 / 373 | 70 / 373 | 79 / 373 |
| BM25 | 373 / 373 | 63 / 373 | 79 / 373 |

## 5. Primary vs staged comparison

| Lane | Query count | Exact title Top-1 | TF-IDF Top-1 | BM25 Top-1 |
|---|---:|---:|---:|---:|
| Primary content-bearing | 520 | 35 | 16 | 17 |
| Priority-5 staged | 373 | 79 | 70 | 63 |

這不是公平的 model generalization comparison，因為兩個 lane 的 population、source composition、duplicate overlap 與 quarantine 狀態不同。結果只能作 lane diagnostics。

## 6. Release state

```text
staged input freeze: pass
373 × 542 retrieval: pass
formal alignment: not_started
human adjudication: not_available
promotion: blocked
```

Priority-5 仍然是 `staged_experiment_only`，沒有寫入 formal dataset、default runtime 或 Qdrant。

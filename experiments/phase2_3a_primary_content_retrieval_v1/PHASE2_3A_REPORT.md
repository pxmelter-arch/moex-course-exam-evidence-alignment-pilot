# Phase 2.3A Primary Content Retrieval

## Scope

```text
structured-content snapshot total: 600
content-bearing primary records: 520
partial records: 80
exam-outline records: 542
```

本輪只使用 pinned 600-record structured-content artifact 中的 520 筆 `content_status=content_bearing`。Priority-5 validation 的 373 筆是 aggregate count，目前沒有單一可重現的 materialized staged artifact，因此不猜測拼接，也不混入本輪。

## Query / document

```text
query = course_title + department + school_name + content_text
document = subject_name + core_knowledge + outline + remarks
top-k = 10
```

## Results

| Method | Top-10 有結果 | Top-1 exact subject | Top-10 exact subject |
|---|---:|---:|---:|
| Exact title | 35 / 520 | 35 / 520 | 35 / 520 |
| TF-IDF + content | 520 / 520 | 16 / 520 | 21 / 520 |
| BM25 + content | 520 / 520 | 17 / 520 | 20 / 520 |

## Interpretation

- content-bearing query 讓所有 records 都能產生 lexical candidate，但不代表所有 records 都有可靠 exam alignment。
- Exact title 由 27 / 176（formal metadata lane）增加到 35 / 520；這只是不同 input population 的字面命中差異，不是效能提升比較。
- TF-IDF / BM25 的 exact subject 指標仍是 machine diagnostic，不是人工 alignment accuracy。
- 目前 query content 來自 structured-content candidate lane；不得把 candidate retrieval 結果寫回 formal dataset。

## Gates

```text
candidate retrieval: pass
formal alignment: not_started
human adjudication: not_available
Priority-5 373 lane: blocked_pending_materialized_pinned_artifact
promotion: blocked
Qdrant ingest: false
```

## 下一步

先建立 Priority-5 staged records 的單一 pinned materialized artifact 與 record-level manifest，確認 373 筆的實際 identity、content status、source provenance 與去重規則；完成後才能以相同 runner 執行 staged diagnostic lane，並與 520 primary 結果分開報告。

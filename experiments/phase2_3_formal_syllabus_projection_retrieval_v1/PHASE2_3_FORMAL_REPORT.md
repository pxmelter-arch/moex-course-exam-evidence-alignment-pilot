# Phase 2.3 Formal Syllabus Projection Retrieval

## Input correction

本輪改用正式 syllabus projection，而不是先前的 520 content-bearing diagnostic lane：

```text
formal projection records: 176
formal_gate=passed: 176
content_status=full: 176
normalized exam outlines: 542
```

Formal projection source：

```text
commit: 8922edc
path: output/canonical/round26_formal_syllabus_projection.json
```

Projection 保留 `content_text`、`content_sha256`、`raw_artifact_path`、`raw_sha256`、`official_url` 與 formal gate/provenance 欄位。

## Query / document

```text
query = course_title + department_name + school_name + content_text
document = subject_name + core_knowledge + outline + remarks
top-k = 10
```

## Results

| Method | Top-10 有結果 | Top-1 exact subject | Top-10 exact subject |
|---|---:|---:|---:|
| Exact title | 27 / 176 | 27 / 176 | 27 / 176 |
| TF-IDF + full syllabus | 176 / 176 | 14 / 176 | 18 / 176 |
| BM25 + full syllabus | 176 / 176 | 7 / 176 | 18 / 176 |

## 與舊 formal metadata-only lane 比較

舊 lane 只使用 `course_title + department_name`：

```text
TF-IDF top-1 exact: 25 / 176
BM25 top-1 exact: 18 / 176
```

加入 full syllabus 後：

```text
TF-IDF top-1 exact: 14 / 176
BM25 top-1 exact: 7 / 176
```

這不是表示 syllabus 無價值，而是表示目前把整段 syllabus 以等權重字元 n-gram 直接加入 query，會引入大量通用詞彙、教學流程、評量與行政文字，稀釋 course identity/topic signal。

## Interpretation

- Formal projection 已有完整內容，因此現在可以正式進入 content-based retrieval development。
- 目前 full-text TF-IDF/BM25 沒有改善 exact subject top-1，反而低於 metadata-only diagnostic。
- `exact_title` 不受全文 query 影響，仍為 27 / 176。
- 結果是 retrieval diagnostic，不是 alignment accuracy；沒有人工 gold labels。
- 下一步不應直接 promotion，而應做 section-aware field weighting、course identity/title boost、topic-only extraction 與 candidate reranking。

## Release state

```text
formal projection input: pass
formal gate passed: 176 / 176
content retrieval: pass
formal alignment: not_started
human adjudication: not_available
promotion: blocked
Qdrant ingest: false
```

520 primary 與 373 Priority-5 staged artifacts 保持獨立，不被本輪正式 projection 結果覆寫。

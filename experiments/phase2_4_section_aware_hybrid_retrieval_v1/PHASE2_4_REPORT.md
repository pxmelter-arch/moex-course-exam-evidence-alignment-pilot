# Phase 2.4 Section-aware Syllabus Processing and Hybrid Retrieval

## Scope

```text
formal syllabus projection: 176
formal_gate=passed: 176
normalized exam outlines: 542
```

Input:

```text
commit: 8922edc
path: output/canonical/round26_formal_syllabus_projection.json
```

## Section-aware processing

每筆 record 保留：

```text
raw_content_sections
raw_syllabus_field_names
section_presence
```

並建立分離的 views：

```text
topic_text = outline + course_description
content_text = course_description + outline + objectives
metadata_text = assessment + textbook + prerequisite
```

`assessment`、`textbook`、`prerequisite` 不被當作主要 exam-topic evidence；缺失欄位保持空值與 presence metadata，不做 silent imputation。

欄位 presence：

| Field | Records |
|---|---:|
| outline | 175 |
| textbook | 158 |
| prerequisite | 153 |
| objectives | 126 |
| assessment | 104 |
| course_description | 22 |

## Explainable hybrid score

```text
title_identity       0.30
title_similarity      0.20
topic_score           0.20
content_bm25         0.20
remarks               0.10
```

Topic score：

```text
core_knowledge       0.60
outline              0.40
```

`subject_name`、`core_knowledge` 與 `outline` 分開計算；remarks 僅低權重，避免 generic exam note 主導結果。

## Results

| Metric | Result |
|---|---:|
| Formal records processed | 176 |
| Outline records | 542 |
| Hybrid top-1 exact subject | 27 / 176 |
| Hybrid top-10 exact subject | 27 / 176 |
| Top candidate exact | 10 |
| Top candidate ambiguous | 157 |
| Top candidate weak | 9 |
| Review queue | 166 |

## Interpretation

- Hybrid top-1 exact 為 27 / 176，與 exact title baseline 相同；title identity boost 保留了明確課名 evidence。
- 只有 10 筆 top candidate 能保守標記為 `exact`；同名 outline variants 會被標記 `ambiguous`，即使課名文字完全相同。
- 157 筆 ambiguous 與 9 筆 weak 必須進入 review queue，不能自動 promotion。
- 目前結果仍是 candidate retrieval diagnostic，不是 course–exam alignment accuracy。
- `content_bm25` 與 topic scores 已輸出到每筆 candidate 的 component scores，可供後續調整 section weights 與 review。

## Artifacts

```text
section_aware_manifest.jsonl
retrieval_results.jsonl
review_queue.jsonl
retrieval_report.json
```

## Release state

```text
section-aware processing: pass
formal alignment: not_started
human adjudication: not_available
promotion: blocked_pending_alignment_evidence
qdrant ingest: false
```

# Phase 2.2 Candidate Identity and Alias Audit

## Scope

```text
formal course records: 176
exam-outline records: 542
Priority-5 content/detail records: not included in this phase
```

本 phase 處理 identity、duplicate subject name、machine alias candidate 與 advisory department-aware scoring；不把 machine inference 當成 truth，也不執行 formal promotion。

## Results

```text
unique deterministic outline_record_id: 542 / 542
duplicate subject_name groups: 36
exact candidates: 11
ambiguous candidates: 35
weak candidates: 130
machine alias candidates: 151
```

## Identity policy

`outline_record_id` 使用下列欄位的 deterministic SHA-256 projection：

```text
subject_name
type
applicable_exams
core_knowledge
outline
remarks
source provenance
```

因此同名但不同考試、不同內容或不同 source page 的 outline 不會只因 `subject_name` 相同而合併。

## Candidate status policy

| Status | 條件 | 意義 |
|---|---|---|
| `exact` | unique exact title 且不屬於 duplicate variant | 可進入優先 review，但不是 truth |
| `ambiguous` | duplicate variant、或候選分數接近 | 必須保留多個候選與 source evidence |
| `weak` | 沒有 unique exact 或可靠 alias evidence | 僅保留為低信心候選 |

`department-aware` score 只作 advisory reranking。缺 department 不代表 record 無效，也不會被當成負面 evidence。

## Alias policy

151 筆 machine alias candidates 已產生，但全部標記：

```text
alias_status = machine_candidate_review_required
human_review_status = not_human_adjudicated
promotion_status = blocked
```

這些 alias 不會自動寫入 canonical truth、formal dataset 或 default runtime。

## Evidence policy

每個 identity / alias / review candidate 都保留：

```text
outline_record_id
source file
source page range
applicable_exams
type
```

## Current gate

```text
candidate audit = pass
formal alignment = not_started
human adjudication = not_available
Priority-5 mixed into formal = false
promotion = blocked
```

下一步才將通過 identity contract 的 candidate structure 接到：

```text
176 formal course lane
+
373 Priority-5 content/detail staged lane
```

並分開報告 formal 與 staged diagnostic retrieval。

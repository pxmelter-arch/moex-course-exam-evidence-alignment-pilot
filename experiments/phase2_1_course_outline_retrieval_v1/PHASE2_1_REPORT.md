# Phase 2.1 Course–Exam Outline Lexical Retrieval

## 實驗設定

```text
formal course records: 176
exam outline records: 542
query fields: course_title + department_name
document fields: subject_name + core_knowledge + outline + remarks
top-k: 10
```

目前 formal course manifest 沒有 syllabus full text，只有 `content_sections`，因此這一輪是：

```text
title / metadata candidate retrieval
```

不是 syllabus content alignment。

## 結果

| Method | Top-10 有結果 | Top-1 exact subject | Top-10 exact subject |
|---|---:|---:|---:|
| Exact title | 27 / 176 | 27 / 176 | 27 / 176 |
| TF-IDF | 176 / 176 | 25 / 176 | 25 / 176 |
| BM25 | 176 / 176 | 18 / 176 | 25 / 176 |

## 解讀

- `Exact title` 只對 27 筆產生 exact candidate；其餘不是錯誤，而是沒有同名官方 outline。
- TF-IDF 與 BM25 都能為 176 筆產生 lexical candidates，但 `top-1_exact_subject` 只是字面一致診斷，不是人工 alignment truth。
- BM25 的 top-1 exact subject 少於 TF-IDF，表示目前 char-bigram BM25 對部分課名會偏向 outline 內容相似、但 subject title 不完全相同的候選。
- 目前沒有人工 gold labels，因此不能報 accuracy、precision、recall 或正式 course–exam alignment rate。

## 狀態與限制

```text
retrieval_status: candidate_only
formal_alignment: not_started
human_adjudication: not_available
promotion: blocked
Qdrant ingest: false
```

每個候選保留：

```text
outline_record_id
subject_name
type
applicable_exams
score
source file / page range
```

下一步應建立 deterministic `outline_record_id` review contract，並對 duplicate-name / no-applicable-exam records 產生 review sheet；之後才進行 syllabus content lane 的 candidate retrieval。

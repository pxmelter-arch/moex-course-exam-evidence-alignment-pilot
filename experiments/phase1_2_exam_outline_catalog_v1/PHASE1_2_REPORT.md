# Phase 1.2 Exam Outline Catalog Input Freeze

## Inputs

本 experiment 將課程 corpus 與 exam outline catalog 維持兩個獨立 input lane：

```text
course formal input:
  commit 1f2a2e635d61e01b5788a3c8c5b66adeb5c7e9db
  176 formal records

Priority-5 acquisition:
  same main commit
  532 staged records / acquisition evidence
  formal promotions = 0

exam outline catalog:
  branch add-exam-outline-catalog
  commit 4cb1b5a7155a052450354cdff2e7e00a66728b89
  542 normalized subjects
```

## Exam outline catalog result

```text
行政 subjects: 202
技術 subjects: 328
行政／技術 shared subjects: 12
outline items: 14,022
missing applicable exam mappings: 15
source page provenance: present
```

Catalog record structure preserves:

```text
subject_name
type
applicable_exams
core_knowledge
outline[level, text]
remarks
source[file, page_start, page_end]
```

`applicable_exams` 缺失的 15 筆保留為原始來源狀態，不補值；這不代表科目沒有內容。

## Validation

The committed normalization pipeline was executed against the committed intermediate artifacts:

```text
行政：32 differences，全部為已知可忽略的類科陣列化分隔符差異；real differences = 0
技術：30 differences；28 為可忽略差異；2 筆為 validator 已知的備註標籤誤報（生物材料學、醫學工程概論）
```

## Promotion policy

```text
formal course dataset remains 176
Priority-5 remains staged evidence
exam outline catalog is catalog-only
subject IDs are not generated
course-to-exam alignment has not started
Qdrant ingest = false
human adjudication = not available
promotion = blocked
```

下一步可以在不改變 formal dataset 的前提下，建立：

```text
outline canonical projection
subject alias / identity audit
course title ↔ outline candidate retrieval
source page evidence package
```

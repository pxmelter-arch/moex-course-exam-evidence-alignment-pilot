# Phase 1 審計報告：NLP、Schema、Identity、Provenance

## 狀態

```text
Phase: 1
Status: completed with provenance limitations
Input: GitHub pinned formal dataset only
Records: 176
Pinned commit: 5accc1e300d4a6d94c7d1475e44c352b6bf5e54b
```

## 1. NLP normalization

本階段只執行 deterministic normalization candidate，不執行語義合併：

```text
Unicode NFKC
全形／半形與標點 canonicalization
連續空白整理
casefold
semester notation normalization
course code formatting normalization
degree label normalization
```

保留欄位：

```text
course_title_raw
course_title_normalized
course_title_canonical_key
course_code_raw
course_code_normalized
department_name_raw
department_name_normalized
semester_raw
semester_normalized
degree_level_raw
degree_level_normalized
```

重要限制：現有 GitHub record 沒有獨立的 `raw_course_title` 欄位，因此 `course_title_raw` 是保留既有 `course_title` source field 的 audit representation，不宣稱它一定是原始 HTML／原始 artifact 的原文欄位。

同義詞、翻譯、縮寫與語義近似課名只保留為後續 candidate，不在 Phase 1 自動合併。

## 2. Schema normalization

```text
record_count = 176
field_count = 48
```

主要 schema issues：

| 欄位 | 發現 |
|---|---|
| `course_code` | 149/176 有值；27 筆缺失 |
| `candidate_id` | 124/176 有值；52 筆缺失 |
| `semester` | `上學期`、`1`、`2` 混用 |
| `candidate_match` | bool 與 string `"True"` 混用 |
| `independent_candidate_evidence` | bool 與 string `"False"` 混用 |
| `degree_level` | `bachelor`、`master`、`Undergraduate Programme` 混用 |
| `department_name` / `department` / `program` | 語義重疊，尚未統一 |
| `http_status` / `syllabus_http_status` | 兩套 provenance 欄位並存 |
| `content_sections` | 只有 1 筆為 list，其餘為 null |

原始 record 的 schema 允許 additional properties，因此這些型別漂移不會被 source schema 阻擋；本階段以 audit artifact 明確記錄。

## 3. Course identity audit

沒有完全相同的 JSON record duplicate：

```text
exact_json_duplicate_count = 0
```

但 composite key 存在大量 collisions：

| Key | Unique groups | Duplicate groups | Duplicate records |
|---|---:|---:|---:|
| school/year/semester/department/course_code | 150 | 12 | 38 |
| school/year/semester/department/course_title | 131 | 22 | 67 |
| school/year/semester/course_code/course_title | 152 | 11 | 35 |
| school/year/semester/department/course_code/course_title | 153 | 11 | 34 |

因此不能使用：

```text
school + department + course_title
```

直接去重，也不能把同名課程直接視為同一門課。

建議 identity 分層：

```text
course_instance_key:
school_id + academic_year + canonical_semester
+ canonical_department + canonical_course_code
+ canonical_section_or_class_code + canonical_course_title
```

當 course code 或 class code 缺失時：

```text
identity_resolution_status = ambiguous_missing_code
human_review_status = unreviewed
```

fallback：

```text
school_id + academic_year + canonical_semester
+ official_url + raw_sha256
```

## 4. Provenance audit

### 宣告欄位

```text
official_url: 176 / 176
raw_artifact_path: 176 / 176
raw_sha256: 176 / 176
formal_gate: 176 / 176
promotion_status: 176 / 176
```

### HTTP／content 欄位

```text
syllabus_http_status = 200: 122
syllabus_http_status = null: 54
syllabus_content_bearing = true: 122
syllabus_content_bearing = null: 54
```

null 不會被推論為 HTTP 200 或內容成功。

### pinned clone 實體檔案檢查

```text
raw artifact physically exists: 1 / 176
raw hash verified: 1 / 1
raw artifact missing: 175 / 176
hash mismatch: 0
```

因此本階段必須區分：

```text
declared_provenance_status
actual_local_artifact_status
```

不能把 record 中宣告的 path/hash 當成目前 clone 已重新驗證的 raw bytes。

## 5. Phase 1 outputs

```text
phase1_schema_profile.json
phase1_identity_audit.json
phase1_identity_collisions.jsonl
phase1_provenance_completeness.json
phase1_title_normalization_candidates.jsonl
phase1_schema_normalized_records.jsonl
phase1_input_freeze_receipt.json
```

## 6. 限制

1. 這是 176 筆 bounded GitHub formal corpus，不是全國母體。
2. 沒有 human adjudication，也沒有 validated exam alignment labels。
3. `formal_gate=passed` 不是 exam alignment truth。
4. normalized title 與 identity key 是 machine-generated candidate，不是人工確認。
5. pinned clone 缺少 175 個 raw artifact 實體檔案，因此 provenance completeness 仍有 blocker。
6. 本階段不執行 Exact／TF-IDF／BM25、embedding、chunking benchmark 或 exam alignment promotion。
7. 所有 identity collision 都保留 review queue，不自動 deduplicate。

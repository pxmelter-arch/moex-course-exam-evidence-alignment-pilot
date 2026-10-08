# 2026-10-08 實體會議確認版研究流程 v1

## 0. 文件定位

本文件是目前研究流程的 source-of-truth。它取代「直接以 176 筆 formal syllabus 對 542 筆 exam outline 做 alignment」作為研究起點，但不刪除舊實驗。舊 Phase 1–3 artifacts 只保留為歷史 diagnostic、方法比較與 failure analysis，不得直接當成本研究的新母體或 formal alignment 結果。

```text
舊流程：176 課綱 → 542 命題大綱 → candidate retrieval
新流程：近三年考試母體 → 類科統計篩選 → 學校/學系篩選 → 人工課程篩選 → alignment analysis
```

---

## 1. 10/08 會議確認事項

### 1.1 研究範圍

本研究僅納入近三年實際有辦理考試的類科。

```text
study_years = {{recent_three_years}}
```

實際年度必須在 input freeze 時由會議決定並寫入 manifest；不可由程式自行推測。

### 1.2 考試類型

只納入：

```text
普通考試
高考三級
特考三等
```

其餘考試類型排除，不得進入正式母體、統計分母、篩選分數或 alignment metric。原始資料仍可保存於 excluded registry，作為 provenance，不參與本研究結果。

### 1.3 學校／學系篩選

不是先抓所有學校課程再讓模型決定，而是先依各類科近三年的：

```text
報考人數
到考人數
錄取人數
```

找出人數較多、具研究優先性的學校／學系，再抓取其課程資料。

「人數多」的正式門檻尚未由本文件自行決定；必須在 input freeze 前以會議決議寫入：

```text
selection_rule_type
selection_threshold
selection_unit
missing_statistic_policy
```

可選的規則包括三年平均、三年總量、指定年度排名或分位數，但不可同時混用而未記錄。

### 1.4 課程篩選

「哪些課程與類科相關」是人工篩選 gate。

LLM / retrieval 可以：

```text
產生課程候選
排序候選
整理課程與類科的理由
提供課綱 evidence span
```

但不能單獨決定正式納入。

### 1.5 Alignment 分析

對人工納入的課程，分析：

```text
課程大綱
↔ 該類科專業科目
↔ 專業科目官方命題大綱
```

分析項目包括：

```text
coverage
relatedness
matched topics
unmatched topics
課程與命題大綱的內容差異
命題科目涵蓋範圍
課程涵蓋範圍
representative evidence spans
資料缺失與限制
```

coverage 與 relatedness 必須分開。coverage 可以由 canonical topic overlap 計算；relatedness 需要 evidence-based machine assistance 加上專業人士判定，不能只用 embedding score。

### 1.6 專業人士討論

技術流程產生：

```text
candidate list
canonical topics
coverage table
relatedness rationale
source provenance
evidence spans
uncertainty
review blockers
```

專業人士負責：

```text
確認課程是否與類科相關
確認課程—專業科目關聯
確認 coverage / relatedness 是否合理
確認代表性 evidence
討論無開課類科與資料不足案例
形成正式研究解釋
```

### 1.7 A3 展示

正式結果預計以 A3 表展示，但「無開課之類科」不得硬塞進一般課程 alignment 表。

無開課、未觀察到課程、資料不足必須使用獨立狀態 lane。

---

## 2. 新研究母體與資料流

```text
近三年考試公告／統計
        ↓
考試類型篩選：普通考試、高考三級、特考三等
        ↓
類科年度統計 canonicalization
        ↓
三年人數分析與學校／學系優先篩選
        ↓
目標學校／學系課程取得
        ↓
課程 source-native / canonical normalization
        ↓
人工課程相關性篩選
        ↓
課綱 canonical topic projection
        ↓
類科專業科目與命題大綱 canonical projection
        ↓
identity candidate retrieval
        ↓
topic matching / bidirectional coverage
        ↓
relatedness evidence pack
        ↓
專業人士討論
        ↓
A3 結果與無開課獨立展示
```

---

## 3. 資料字典

### 3.1 Exam population record

```text
exam_year
exam_type
exam_type_canonical
exam_name_raw
category_id
category_name_raw
category_name_canonical
school_id / school_name（若來源提供）
department_id / department_name（若來源提供）
applicants_count
attendees_count
admitted_count
statistic_source_path
statistic_source_url
source_commit
raw_sha256
statistic_status
```

`statistic_status` 至少包括：

```text
observed
not_reported
not_applicable
parse_failed
conflicting_sources
```

缺少人數不得自動補 0。`not_reported` 不等於 0。

### 3.2 Three-year category summary

```text
category_id
category_name
exam_types_in_scope
years_observed
applicants_by_year
attendees_by_year
admitted_by_year
applicants_mean
applicants_std
applicants_min
applicants_max
attendees_mean
attendees_std
admitted_mean
admitted_std
yoy_change
three_year_change_rate
statistical_completeness
selection_priority
```

三年變化分析至少報告：

```text
平均值
標準差
最小值／最大值
年度變化量
三年變化率
資料完整性
```

### 3.3 School / department selection record

```text
category_id
school_id
school_name
department_id
department_name
selection_unit
selection_rule_version
three_year_statistic_basis
selection_rank
selection_status
selection_reason
```

`selection_status`：

```text
selected
not_selected
insufficient_statistics
out_of_scope
review_required
```

### 3.4 Course screening record

```text
course_record_id
school_id
school_name
department_id
department_name
course_title_raw
course_title_normalized
course_code_raw
academic_year
semester
course_source_path
course_provenance_status
machine_relevance_candidate
machine_relevance_reason
human_relevance_decision
human_reviewer
human_review_status
review_notes
```

`human_relevance_decision`：

```text
include
exclude
unclear
insufficient_evidence
```

machine candidate 不得直接填入 human decision。

---

## 4. 人工與自動化分工

### 4.1 可自動化

```text
考試類型過濾
年度統計整理
平均／標準差／變化率計算
source provenance / checksum
schema normalization
課程 candidate retrieval
命題大綱 parsing
canonical topic projection
topic lexical / dense matching
coverage 計算
review sheet 產生
A3 草稿產生
```

### 4.2 必須人工或專業人士確認

```text
「人數多」正式篩選規則確認
課程是否與類科相關
ambiguous course identity
課程與專業科目的實質關係
代表性 evidence 是否支持結論
coverage / relatedness 的最終解釋
無開課類科的原因與呈現方式
正式 A3 結論
promotion / formal alignment decision
```

### 4.3 LLM 的角色

LLM 可以做：

```text
課名與類科語義候選
課程相關性預審
topic / subtopic 抽取候選
matched / unmatched evidence 摘要
A3 草稿文字
衝突與不確定性標記
```

LLM 不可做：

```text
自行決定研究母體
自行決定人數門檻
自行決定課程正式納入
把語義相似當成 alignment truth
補造缺失資料
把 machine label 當 human label
```

---

## 5. 課綱與命題大綱共同 canonical topic

兩邊共用：

```text
canonical_topic_id
source_type
record_id
chapter
section
topic
subtopic
atomic_text
content_lane
contamination_lane
unresolved_lane
parse_status
source_path
source_commit
raw_sha256
evidence_span
```

課綱仍保留：

```text
school
academic_year
semester
department
course_code
course_title
```

命題大綱仍保留：

```text
subject_name
outline_record_id
type
applicable_exams
core_knowledge
outline_level
source_page
```

兩邊共用 canonical topic，不代表兩邊原始 schema 被抹平。

---

## 6. Alignment analysis design

### 6.1 Unit of analysis

正式分析單位是：

```text
人工納入的課程
×
指定類科的專業科目
×
該專業科目的官方命題大綱
```

不是：

```text
所有課程
×
所有 542 subjects
```

### 6.2 Outputs per course / subject pair

```text
course identity
category identity
exam type
professional subject
syllabus topic set
outline topic set
syllabus → outline coverage
outline → syllabus coverage
bidirectional coverage
relatedness candidate
matched evidence spans
unmatched topics
contamination / unresolved status
provenance
review status
```

### 6.3 No-course status

無法像一般 A3 顯示的類科，獨立使用：

```text
no_course_observed
no_course_in_selected_school_department
course_search_not_completed
insufficient_course_data
course_found_but_not_human_screened
out_of_scope
```

不可把這些狀態寫成：

```text
coverage = 0%
relatedness = none
course does not exist
```

因為「沒有觀察到開課」不等於「全國沒有相關課程」。

---

## 7. A3 結果規格

### 7.1 一般 alignment A3

建議欄位：

```text
類科
考試類型
年度
報考人數
到考人數
錄取人數
三年平均／標準差／趨勢
學校
學系
人工納入課程
專業科目
命題大綱 topic
課綱 topic
coverage
relatedness
代表性 evidence
資料來源
人工確認狀態
限制與 unresolved
```

### 7.2 無開課／資料不足 A3

另設表或另設區塊：

```text
類科
考試類型
三年統計
篩選學校／學系
課程搜尋範圍
課程狀態
未觀察到課程的證據範圍
是否完成人工課程篩選
不能推論的事項
後續建議
```

重點是清楚分開：

```text
no course observed
vs
no relevant course
vs
course data missing
```

---

## 8. 舊實驗的處理方式

舊有 artifacts 不刪除，但重新定位：

```text
Phase 1–3 = historical technical diagnostic
新研究流程 = meeting-scope population study
```

舊結果可用於：

```text
說明 identity / parser / contamination 問題
比較 canonical topic parser
測試 retrieval component
```

舊結果不可直接用於：

```text
新研究母體統計
學校／學系選取
正式課程相關性結論
A3 正式結果
formal alignment truth
```

---

## 9. New gates

### Gate 0：Scope freeze

```text
study years confirmed
exam types confirmed
excluded exam types recorded
```

### Gate 1：Statistics freeze

```text
all in-scope category statistics have provenance
missing statistics classified
three-year summary reproducible
selection rule versioned
```

### Gate 2：School / department selection

```text
selected schools/departments have auditable reason
not-selected and insufficient-statistics cases separated
```

### Gate 3：Human course screening

```text
course candidate review sheet generated
human include/exclude/unclear recorded
machine suggestion not treated as decision
```

### Gate 4：Canonical topic validation

```text
syllabus and outline share canonical schema
raw/source-native fields preserved
parse failures explicit
no silent imputation
```

### Gate 5：Alignment evidence

```text
topic match has source spans
coverage and relatedness separated
independent evidence status recorded
unresolved queue retained
```

### Gate 6：Professional discussion / A3

```text
A3 draft produced
no-course lane produced separately
professional review completed or explicitly pending
formal conclusion status recorded
```

---

## 10. Current status after scope reset

```text
new population definition = specified by 10/08 meeting
three-year statistics input = not yet frozen
school/department selection = not started under new scope
human course relevance screening = not started under new scope
old 176/542 retrieval = historical diagnostic only
A3 output = schema to be built
no-course output lane = defined
formal alignment = not started
promotion = blocked
Qdrant ingest = false
```

The next implementation must begin at Gate 0, not continue from the old 176 × 542 retrieval output.

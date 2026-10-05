# GitHub-Bounded Course–Exam Evidence Alignment Pilot v2

## 1. 研究定位

本研究目前為小型、可重現的技術先導實驗，不以全國代表性為目標。

本階段的任務是：

> 使用 GitHub repository `caperspeert-blip/moex-course-exam-alignment` 的 bounded dataset，建立一套可追溯的課程、課程大綱、官方命題大綱與初步 exam-subject candidate mapping 方法，產出可供後續專家會議判斷的 evidence package。

本階段成功後，才評估擴增學校、課程母體、subject scope 與資料來源。

本研究不是：

- 全國課程普查
- 正式 exam alignment gold-label 建立
- 自動決定考科刪減或整併
- 取代專家會議
- 以 machine score 取代專家判斷

---

## 2. 與原始考選部研究計畫的關係

原始研究計畫關注：

```text
大學課程
  ↔ 公務人員考試專業科目
  ↔ 官方命題大綱
  ↔ 職系說明書／工作內容
  ↔ 考試前知識與任用後訓練分際
  → 專家討論與制度建議
```

本 pilot 對應其中的技術前置階段：

```text
資料取得
→ provenance / identity validation
→ 課程與命題大綱 candidate retrieval
→ topic evidence extraction
→ 初步 coverage analysis
→ expert review package
```

因此兩者研究方向一致，但本 pilot 只負責：

1. 建立資料與 evidence pipeline。
2. 提供可解釋的 candidate mapping。
3. 產出初步技術判斷與不確定性。
4. 將結果整理成專家可審查的 review package。

最終的考科整併、刪減、保留、職前／在職分際與政策建議，不由本技術 pilot 自動決定。

---

## 3. 研究角色分工

### 3.1 技術研究團隊負責

- GitHub dataset input freeze
- schema normalization
- course identity audit
- provenance validation
- candidate retrieval
- syllabus／outline topic evidence extraction
- 初步 coverage analysis
- uncertainty 與 failure analysis
- review sheet / review queue 產生
- model / rule / threshold 的可重現記錄
- 提供專家判斷所需的 evidence package

### 3.2 技術研究團隊不負責

- 宣稱某課程正式等於某考科
- 代替專家完成 exam alignment adjudication
- 代替專家決定考科刪減或整併
- 代替考選部提出正式考試規則修正
- 將 candidate score 直接轉成政策結論

### 3.3 後續專家／委託單位負責

- 審查課程與 exam subject 的實質關係
- 判定 topic coverage 的合理性
- 判定職系能力與課程內容的關聯
- 判定哪些內容屬於職前考試核心知識
- 判定哪些內容適合任用後訓練
- 形成正式研究與政策建議

---

## 4. 本階段資料範圍

### 4.1 唯一實驗資料來源

```text
GitHub repository:
caperspeert-blip/moex-course-exam-alignment

Pinned commit:
5accc1e300d4a6d94c7d1475e44c352b6bf5e54b
```

GitHub formal corpus：

```text
formal records = 176
formal schools = 9
academic year = 114
```

資料包含：

- official course evidence
- official syllabus / course outline evidence
- course identity fields
- official URL
- raw artifact provenance
- SHA-256
- candidate subject mapping
- official outline mapping
- provisional coverage fields

### 4.2 明確排除

以下資料不進入本輪 experiment input、label、metric 或結果統計：

```text
Qdrant 已存入的 124 records
上傳 Excel 的完整大學／技專課程母體
staged records
quarantine records
blocked records
```

Qdrant 僅可作為方法與架構參考；本輪不把 Qdrant collection 當成 experiment corpus。

qmd 不使用。

---

## 5. 研究問題

### RQ1：資料與 identity

GitHub bounded formal records 是否具有足夠的學校、系所、學制、課號、學期與 syllabus provenance，可支援可重現的課程比較？

### RQ2：候選產生

Exact / alias / TF-IDF / BM25 是否能從課程與命題大綱資料產生可解釋的 candidate mapping？

### RQ3：內容 evidence

課程 syllabus 是否能提供官方命題大綱 topic 的可追溯 evidence span？

### RQ4：方法比較

在沒有人工 gold labels 的前提下，lexical retrieval 與 optional dense diagnostic 的差異為何？

### RQ5：專家支援

如何將 machine candidate、matched terms、topic evidence、provenance 與 uncertainty 整理成專家可以審查的 review package？

### RQ6：擴增判準

哪些技術 gate 通過後，才值得將 pilot 擴增至更多學校、完整課程母體或更多 subject？

---

## 6. 實驗架構

```text
GitHub formal dataset
        ↓
input freeze / checksum
        ↓
canonical normalization
        ↓
identity and provenance audit
        ↓
subject / outline registry
        ↓
exact + alias retrieval
        ↓
TF-IDF / BM25 retrieval
        ↓
syllabus topic evidence extraction
        ↓
uncertainty / failure analysis
        ↓
expert review package
        ↓
後續專家判斷
```

Dense embedding 與 Qdrant 不作為本輪必要前提；只有 lexical baseline 與資料 identity audit 完成後，才可作為隔離的 diagnostic extension。

---

## 7. 執行階段

### Phase 0：Input freeze

確認：

- GitHub repository
- pinned commit
- formal dataset path
- record count
- excluded data declaration
- checksum
- random seed
- experiment directory

主要 assertion：

```text
records_in == 176
qdrant_124_records_included == false
uploaded_excel_included == false
qmd_used == false
```

### Phase 1：Schema normalization and identity audit

保留 raw value，同時建立 normalized value：

```text
school_id
school_name
department_name
course_code
course_title
academic_year
semester
degree_level
official_url
raw_artifact_path
raw_sha256
```

檢查：

- null / missingness
- duplicate identity
- same-title collision
- same course code collision
- school / department mismatch
- degree-level heterogeneity
- syllabus content-bearing status

本 Phase 的目的不是找出每個 null 的真實成因，也不是建立學校資料完整度排名。不同學校的 source schema 差異應由 source-native schema、canonical superset schema 與 field-level eligibility 表示；缺失本身不得被解讀為課程內容不存在、不同課程或負面 evidence。只有在 identity、provenance 或特定 downstream gate 受到影響時，才保留最低必要的 status 與 unresolved queue。

### 1.1 Candidate structured-content overlay

round26 `structured_content_600.json` 是 additive candidate overlay，不取代 176 筆 formal bounded input。`content_bearing` 與 `partial` 分開作 diagnostic lane；candidate 不得直接 promotion 到 default、formal exam alignment 或 evidence-grade runtime。

### 1.2 下一步：source-aware canonical normalization

下一步聚焦於：

- source registry 與 source_schema_id
- source-native field preservation
- canonical field mapping / adapter
- identity-critical normalization
- provenance-critical gate
- school/schema variation 下的可比較性

missingness-cause audit 僅作輔助診斷；不擴張為本研究的主要工作。

### Phase 2：Subject and outline registry

使用 GitHub repository 既有 registry，不重新編號：

```text
SUBJ001–SUBJ015
```

建立：

- subject name
- alias
- official outline section
- topic group
- source provenance

第一輪可選擇少量 subject 做 pilot，但 subject selection 必須記錄為 pilot scope，不代表完整研究範圍。

### Phase 3：NLP normalization 與文字表示實驗

在 retrieval baseline 之前，先比較不同的文字前處理與表示方式。這些實驗仍只使用 GitHub formal dataset，不使用 Qdrant 已存的 124 records 作為輸入。

#### 3.1 Chinese / multilingual normalization

比較：

- raw text
- Unicode 與全半形 normalization
- 中文標點與空白 normalization
- alias／縮寫展開
- stopword 處理
- course title 與 syllabus content 分開處理
- title、outline topic、syllabus section 的欄位權重

每種設定都要保存：

```text
normalization_version
input_fields
transformation_rules
removed_token_count
changed_record_count
```

不能因為 normalization 後分數變高，就直接視為 alignment 變好；必須同時檢查 identity collision 與 evidence quality。

#### 3.2 NLP representation ablation

比較：

```text
course_title only
course_title + department
course_title + subject aliases
course_title + syllabus sections
course_title + syllabus + outline topic
```

目標是找出：

- 哪些欄位增加候選召回
- 哪些欄位只增加 boilerplate similarity
- 哪些欄位造成跨學校 identity 混淆

### Phase 4：Chunking 實驗

Chunking 只適用於 syllabus 與命題大綱等較長文字；短課名不應直接使用任意固定長度切割。

比較以下 chunking strategies：

1. section-based chunking
2. paragraph-based chunking
3. fixed character window
4. fixed token window
5. window with overlap
6. section title + content augmentation

每種 chunk 需保存：

```text
chunk_id
source_record_id
section_name
char_start
char_end
token_count
parent_raw_sha256
```

Chunking 實驗評估：

- topic evidence 是否仍保留上下文
- evidence span 是否能回查原始 syllabus
- chunk 是否過短而失去語意
- chunk 是否過長而混入不相關 topic
- duplicate chunk rate
- source record coverage

Chunking 的目標不是最大化 chunk 數量，而是保留可供專家回查的完整 evidence context。

### Phase 5：可解釋 lexical baseline

依序測試：

1. exact title match
2. alias match
3. token overlap
4. TF-IDF
5. BM25

輸出：

```text
candidate_subject_id
retrieval_method
score
matched_terms
rank
identity_fields
provenance_fields
```

### Phase 6：Embedding 與 dense retrieval 實驗

Embedding 可以納入本 pilot 的方法實驗，但必須是隔離、可比較的 diagnostic lane，不得覆寫 GitHub formal dataset，也不得把 Qdrant 124 records 當成完整實驗 corpus。

#### 6.1 Embedding experiment questions

比較：

- title-only embedding
- syllabus-chunk embedding
- section-aware embedding
- title + syllabus weighted embedding
- Chinese／multilingual embedding model
- normalized text vs raw text

#### 6.2 Embedding controls

每次實驗必須記錄：

```text
model_name
model_revision
embedding_dimension
device
batch_size
normalization_version
chunking_version
input_record_count
excluded_record_count
distance_metric
```

不能使用不可追溯的線上 embedding API，也不能把外部 SaaS 結果當成已驗證 evidence。

#### 6.3 Dense retrieval 的限制

Dense score 只表示向量空間相似度，不等於：

```text
exam equivalence
topic coverage truth
職系能力符合度
```

因此 dense retrieval 必須與以下項目一起分析：

- metadata filtering
- identity compatibility
- official provenance
- evidence-bearing status
- score margin
- false-neighbor examples

### Phase 7：Hybrid retrieval 與 optional reranking

只有在 lexical 與 dense 結果都已獨立保存後，才比較：

```text
BM25 + dense score fusion
reciprocal rank fusion
metadata-aware fusion
optional reranker
```

Hybrid 結果必須保留各 component score，不得只留下單一 final score，讓專家能了解候選如何產生。

### Phase 8：Syllabus topic evidence

對 GitHub formal records 的 syllabus evidence 做：

- section-aware extraction
- topic matching
- evidence span preservation
- official outline mapping
- coverage state assignment

coverage state：

```text
covered
partially_covered
not_found
unknown
review_required
```

不能直接輸出：

```text
aligned = true
```

### Phase 9：初步判斷與 failure analysis

技術團隊可以做：

- candidate ranking
- topic coverage provisional analysis
- confidence / margin analysis
- ambiguous case identification
- missing evidence identification
- out-of-scope / unresolved classification

技術團隊不能做：

- final alignment truth
- formal exam equivalence
- policy recommendation

### Phase 10：Expert Review Package

每個 review item 應包含：

```text
review_id
course_record_id
course_identity
subject_id
subject_name
outline_topic_id
retrieval_method
candidate_score
score_margin
matched_terms
evidence_span
official_url
raw_artifact_path
raw_sha256
provenance_status
identity_strength
machine_status
review_question
known_limitations
```

machine status：

```text
machine_provisional
review_required
not_human_adjudicated
promotion_blocked
```

### Phase 11：擴增決策

只有在下列 gate 通過後，才評估擴增：

- input manifest 可重現
- identity collision 可解釋
- provenance 欄位完整
- lexical baseline 可重跑
- evidence span 可回查
- review sheet 可供專家使用
- failure buckets 已整理
- no-human-label 限制已明確記錄

擴增選項：

- 更多 GitHub formal schools
- 更多 subject
- 更完整 syllabus content
- 上傳 Excel 作為獨立 inventory lane
- dense embedding diagnostic
- Qdrant isolated candidate collection

---

## 8. Evaluation 設計

由於本階段沒有人工 gold labels，不報告正式 accuracy、F1 或 exam-equivalence accuracy。

### 8.1 Data quality metrics

- formal records in/out
- school count
- missing field counts
- duplicate identity count
- same-title collision count
- syllabus content-bearing rate
- provenance completeness
- raw artifact availability

### 8.2 Retrieval diagnostic metrics

- no-result count
- top-k candidate count
- candidate yield
- rank stability
- score margin
- duplicate candidate rate
- identity-compatible result rate
- evidence-bearing result rate

### 8.3 Topic evidence metrics

- covered topic count
- partially covered topic count
- not-found count
- unresolved count
- evidence span availability
- outline section coverage

### 8.4 Expert-support metrics

- review item completeness
- official source click-through availability
- evidence span recoverability
- ambiguous case rate
- review blocker rate
- machine／human decision separation compliance

---

## 9. 成功定義

本 pilot 成功，不是代表模型已經正確判定所有課程對應考科，而是代表：

1. GitHub 176 筆 formal input 可重現讀取。
2. 排除 Qdrant 124 records 的規則可機械驗證。
3. 課程 identity 與 provenance 可追溯。
4. lexical baseline 可重跑且結果可解釋。
5. syllabus evidence 可以回到官方來源。
6. candidate 與 truth label 沒有被混淆。
7. 技術團隊能產出完整 review package。
8. 可以清楚列出哪些問題需要專家判斷。
9. 可以根據 failure analysis 決定是否值得擴增。

---

## 10. 最終輸出

```text
experiments/round26_github_bounded_pilot_v2/
├── README.md
├── input_manifest.json
├── exclusion_manifest.json
├── normalized_records.jsonl
├── identity_audit.json
├── retrieval_candidates.jsonl
├── topic_evidence.jsonl
├── review_queue.jsonl
├── expert_review_sheet.csv
├── evaluation_report.json
├── failure_analysis.json
├── expansion_gate_report.json
└── figures/
```

每個 artifact 必須記錄：

```text
input path
GitHub commit SHA
filter condition
excluded sources
method version
model / retriever version
random seed
record counts
known limitations
```

---

## 11. 一句話總結

```text
本階段不是替專家決定哪些考科應保留或刪除；
本階段是用 GitHub bounded dataset 建立一套可驗證、可追溯、可解釋的技術方法，
讓後續專家能根據課程 identity、官方 syllabus、命題大綱 topic 與 evidence span 做出判斷。
```

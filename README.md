# 課程—考試命題大綱 Evidence Alignment Pilot

本 repository 是一個小型、可重現的技術先導實驗專案。

## 研究定位

本專案不追求目前階段的全國代表性，也不自動替專家決定考科保留、刪減或整併。技術團隊負責建立：

```text
GitHub bounded dataset
→ identity / provenance validation
→ NLP normalization
→ chunking experiments
→ Exact / Alias / TF-IDF / BM25
→ embedding / hybrid retrieval diagnostics
→ syllabus topic evidence
→ expert review package
```

最終 exam alignment、職系能力判斷與政策建議保留給後續專家與委託單位。

## 唯一實驗資料來源

```text
Repository: caperspeert-blip/moex-course-exam-alignment
Pinned commit: 5accc1e300d4a6d94c7d1475e44c352b6bf5e54b
Formal records: 176
Formal schools: 9
Academic year: 114
```

## 明確排除

- Qdrant 已存入的 124 records
- 上傳的 Excel 完整課程母體
- staged / quarantine / blocked records
- qmd

Qdrant 僅作為方法與架構參考，不作為本輪 experiment corpus。

## 目錄

```text
docs/       研究計畫、scope 與環境文件
configs/    可重現設定與 exclusion policy
src/        實驗程式碼
scripts/    validation 與執行入口
tests/      fast contract tests
experiments/ 只保存小型 metadata / reports，不保存原始敏感資料
```

## 建立環境

```bash
uv venv .venv --python python3
uv pip install --python .venv/bin/python -r requirements-dev.txt
uv pip install --python .venv/bin/python -r requirements.txt
```

## 執行 Phase 0 input freeze

Pinned GitHub clone 必須是唯讀且 checkout 到固定 commit：

```bash
/home/aelix/.hermes/profiles/ml-expert/workspace/ml-expert-workspace/.venv/bin/python \
  scripts/run_phase0_freeze.py \
  --source-repo /tmp/moex-course-exam-alignment-inspect \
  --output-dir experiments/phase0_input_freeze_v1
```

產出：

```text
experiments/phase0_input_freeze_v1/input_manifest.json
experiments/phase0_input_freeze_v1/exclusion_manifest.json
experiments/phase0_input_freeze_v1/validation_report.json
```

## 執行 Phase 1 audit

使用 Phase 0 pinned source 執行 schema、NLP normalization candidate、identity 與 provenance audit：

```bash
/home/aelix/.hermes/profiles/ml-expert/workspace/ml-expert-workspace/.venv/bin/python \
  scripts/run_phase1_audit.py \
  --source-repo /tmp/moex-course-exam-alignment-inspect \
  --output-dir experiments/phase1_audit_v1
```

產出：

```text
experiments/phase1_audit_v1/PHASE1_REPORT.md
experiments/phase1_audit_v1/phase1_schema_profile.json
experiments/phase1_audit_v1/phase1_identity_audit.json
experiments/phase1_audit_v1/phase1_identity_collisions.jsonl
experiments/phase1_audit_v1/phase1_provenance_completeness.json
experiments/phase1_audit_v1/phase1_title_normalization_candidates.jsonl
experiments/phase1_audit_v1/phase1_schema_normalized_records.jsonl
experiments/phase1_audit_v1/phase1_input_freeze_receipt.json
```

Phase 1 不會覆蓋 source raw fields，也不會將 machine normalization 或 identity inference 當成人工 truth。

## 執行驗證

```bash
/home/aelix/.hermes/profiles/ml-expert/workspace/ml-expert-workspace/.venv/bin/python scripts/validate_project.py
/home/aelix/.hermes/profiles/ml-expert/workspace/ml-expert-workspace/.venv/bin/python -m pytest -q
```

## 資料與安全規則

- 不將原始課程資料、個人資料、token、API key 或私鑰提交到 repository。
- 實驗結果必須標記為 `machine_provisional`、`review_required` 或 `not_human_adjudicated`。
- 不將 candidate score 改名為 truth label。
- 所有 dense / embedding 結果必須記錄模型、版本、dimension、device、chunking 與 normalization 版本。

# 實驗記錄：Project Setup and Scope Validation

## 執行日期

```text
2026-10-03
```

## 實驗名稱

```text
moex-course-exam-evidence-alignment-pilot
```

## 目的

確認 GitHub-bounded pilot 的 repository、資料範圍、排除政策、實驗設定與基本 validation 可以重現執行。

本記錄是專案初始化與 scope validation，不宣稱已完成 course–exam alignment，也不宣稱 embedding、chunking 或 NLP benchmark 已完成。

## 輸入範圍

```text
GitHub repository:
caperspeert-blip/moex-course-exam-alignment

Pinned commit:
5accc1e300d4a6d94c7d1475e44c352b6bf5e54b

Formal records:
176

Formal schools:
9

Academic year:
114
```

## 排除範圍

| 項目 | 狀態 |
|---|---|
| Qdrant 已存入 124 records | 排除 |
| 上傳 Excel 課程母體 | 排除 |
| qmd | 不使用 |
| staged records | 排除 |
| quarantine records | 排除 |
| blocked records | 排除 |
| machine output 作為 truth | 禁止 |
| promotion | blocked |

## 已建立的技術實驗軌道

```text
NLP normalization
text representation ablation
section-based chunking
paragraph-based chunking
fixed-window chunking
exact / alias
TF-IDF
BM25
embedding diagnostic
hybrid retrieval diagnostic
optional reranking
syllabus topic evidence
expert review package
```

## 執行環境

```text
Python: 3.12.3
PyTorch: 2.5.1+cu121
sentence-transformers: 6.0.0
GPU: GTX 1660 6GB
```

本專案使用 ml-expert workspace 的已驗證 environment：

```text
/home/aelix/.hermes/profiles/ml-expert/workspace/ml-expert-workspace/.venv
```

## 實際執行命令

```bash
/home/aelix/.hermes/profiles/ml-expert/workspace/ml-expert-workspace/.venv/bin/python scripts/validate_project.py
/home/aelix/.hermes/profiles/ml-expert/workspace/ml-expert-workspace/.venv/bin/python -m pytest -q
```

## 實際結果

```text
project_scope=PASS
formal_records=176
qdrant_124_records_included=false
uploaded_excel_included=false
qmd_used=false
promotion_status=blocked

2 passed in 0.03s
```

## GitHub upload verification

```text
GitHub account: pxmelter-arch
SSH alias: github-ml-expert
Repository: pxmelter-arch/moex-course-exam-evidence-alignment-pilot
Visibility: public
Default branch: main
Commit: 8469850ca4709ede8763628aa7e4b98ccc4df3f5
```

## 本記錄的限制

本次只完成：

```text
repository initialization
research plan organization
environment documentation
scope policy
basic validation
```

尚未完成：

```text
actual chunking benchmark
actual embedding benchmark
actual NLP ablation
TF-IDF / BM25 retrieval run
hybrid retrieval comparison
expert adjudication
```

所有後續結果必須新增獨立 run manifest、input checksum、method version、metrics、failure analysis 與 review status；不得把本次 setup validation 當作模型效果結果。

# Phase 1.1 School-Specific Schema Profile

## 實驗目的

確認不同學校的欄位差異是否可能是 source schema 差異，而不是把它們直接視為不同資料類型、資料品質排名或模型特徵。

## 實際結果

```text
records: 600
schools: 7
fields profiled: 29
schema absence candidates: 11
imputation: false
missingness as model feature: false
school quality ranking: false
```

Schema absence candidates:

```text
assessment
course_code
department
objectives
official_url
prerequisite
provenance_status
school_name
target_program
teacher
textbook
```

## 解讀規則

`schema_absence_candidate` 只表示某一 source school 在目前 snapshot 中沒有提供該欄位；它不是：

```text
負面 label
資料品質分數
課程內容不存在的證據
學校排名
模型輸入特徵
```

實驗保留 source-native fields，canonical null 不做 silent imputation。欄位 availability matrix 只用於選擇適合的 downstream gate。

## 下一步

```text
1. 為每個 source family 建立 canonical adapter
2. 對 identity-critical fields 執行 source-aware normalization
3. 將 content-bearing / partial 依 source schema 分層評估
4. 不把 schema absence 混入 retrieval score 或 truth label
5. 只有在 provenance / identity gate 通過後，才進 evidence-grade pipeline
```

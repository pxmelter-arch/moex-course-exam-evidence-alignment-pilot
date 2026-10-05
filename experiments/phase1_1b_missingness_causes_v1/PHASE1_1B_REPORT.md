# Phase 1.1b Multi-Cause Missingness Audit

## 實驗目的

不把所有 null 都歸因於學校 schema 差異。每個缺失事件保留多個可能原因、證據與不確定性，沒有直接證據時標記 `cause_unresolved`。

## 實際結果

```text
records: 600
missingness events: 3007
structural_schema_candidate: 1772
source_not_published_or_not_available_or_unresolved: 32
cause_unresolved: 1235
```

`structural_schema_candidate` 只表示該欄位在該學校的目前 snapshot 中全部缺失；它不排除來源未公開、抓取失敗、解析失敗或其他原因。

`cause_unresolved` 表示目前 snapshot 沒有足夠證據判斷原因，不能自動補值，也不能把它當成內容不存在。

## Policy

```text
school schema difference is only one candidate cause
null is not content absence
cause inference is advisory
source check is required
imputation = false
missingness as model feature = false
school quality ranking = false
release = blocked pending cause resolution
```

## 下一步

針對 `cause_unresolved` 建立 source-level acquisition evidence：HTTP status、response content type、raw artifact existence、parser result、source-native field declaration，然後再更新 missingness reason；未取得直接證據前維持 unresolved。

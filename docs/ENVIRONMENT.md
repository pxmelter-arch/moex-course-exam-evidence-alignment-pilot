# 實驗環境

## 已驗證的主工作區

本專案使用外層 ml-expert workspace 的 Python environment：

```text
/home/aelix/.hermes/profiles/ml-expert/workspace/ml-expert-workspace/.venv
Python 3.12.3
PyTorch 2.5.1+cu121
sentence-transformers 6.0.0
CUDA GPU: GTX 1660 6GB
```

## 原則

- 使用 `.venv/bin/python`，不要依賴 shell 中未確認的 `python`。
- GPU embedding 必須記錄實際 `model.device` 與 `nvidia-smi` 結果。
- CPU 與 GPU embedding artifact 分開命名。
- 不使用外部 SaaS embedding API。
- Qdrant 僅作為本地方法／架構參考，不寫入本輪正式資料。

## 建議安裝

```bash
uv venv .venv --python python3
uv pip install --python .venv/bin/python -r requirements-dev.txt
uv pip install --python .venv/bin/python -r requirements.txt
```

## 驗證

```bash
.venv/bin/python scripts/validate_project.py
.venv/bin/python -m pytest -q
```

## 不可提交

```text
.env
*.key
*.pem
credentials*
raw data
PII
API tokens
```

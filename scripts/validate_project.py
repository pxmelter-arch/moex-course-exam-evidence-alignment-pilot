"""Validate project scope and required experiment configuration."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Run deterministic project contract checks / 執行專案契約檢查。"""
    scope = json.loads((ROOT / "configs/experiment_scope.json").read_text(encoding="utf-8"))
    policy = scope["data_policy"]
    assert policy["allowed_source"] == "GitHub repository only"
    assert policy["formal_record_count"] == 176
    assert policy["qdrant_124_records_included"] is False
    assert policy["uploaded_excel_included"] is False
    assert policy["qmd_used"] is False
    assert scope["label_policy"]["machine_outputs_are_truth"] is False
    assert scope["label_policy"]["promotion_status"] == "blocked"
    print("project_scope=PASS")
    print("formal_records=176")
    print("qdrant_124_records_included=false")
    print("uploaded_excel_included=false")
    print("qmd_used=false")
    print("promotion_status=blocked")


if __name__ == "__main__":
    main()

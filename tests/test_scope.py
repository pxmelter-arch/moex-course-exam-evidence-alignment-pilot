"""Contract tests for the GitHub-only experiment scope."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_github_only_scope() -> None:
    """Ensure only the pinned GitHub formal corpus is allowed."""
    scope = json.loads((ROOT / "configs/experiment_scope.json").read_text(encoding="utf-8"))
    policy = scope["data_policy"]
    assert policy["repository"] == "caperspeert-blip/moex-course-exam-alignment"
    assert policy["pinned_commit"] == "5accc1e300d4a6d94c7d1475e44c352b6bf5e54b"
    assert policy["formal_record_count"] == 176
    assert policy["qdrant_124_records_included"] is False
    assert policy["uploaded_excel_included"] is False
    assert policy["qmd_used"] is False


def test_machine_labels_are_not_truth() -> None:
    """Ensure machine output remains advisory / 確保機器輸出僅供參考。"""
    scope = json.loads((ROOT / "configs/experiment_scope.json").read_text(encoding="utf-8"))
    labels = scope["label_policy"]
    assert labels["validated_exam_subject_ids_available"] is False
    assert labels["human_adjudication_available"] is False
    assert labels["machine_outputs_are_truth"] is False
    assert labels["promotion_status"] == "blocked"

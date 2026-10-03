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


def test_phase0_freeze_artifacts() -> None:
    """Validate generated Phase 0 artifacts / 驗證 Phase 0 freeze 產物。"""
    artifact_dir = ROOT / "experiments/phase0_input_freeze_v1"
    input_manifest = json.loads(
        (artifact_dir / "input_manifest.json").read_text(encoding="utf-8")
    )
    exclusion_manifest = json.loads(
        (artifact_dir / "exclusion_manifest.json").read_text(encoding="utf-8")
    )
    report = json.loads(
        (artifact_dir / "validation_report.json").read_text(encoding="utf-8")
    )
    assert input_manifest["source"]["pinned_commit"] == (
        "5accc1e300d4a6d94c7d1475e44c352b6bf5e54b"
    )
    assert input_manifest["input_contract"]["formal_record_count"] == 176
    assert input_manifest["integrity"]["git_head_matches_pinned_commit"] is True
    assert exclusion_manifest["included_input"]["count"] == 176
    excluded_names = {item["name"] for item in exclusion_manifest["excluded_inputs"]}
    assert excluded_names == {
        "qdrant_existing_124_records",
        "uploaded_excel_course_corpus",
        "qmd",
        "staged_records",
        "quarantine_records",
        "blocked_records",
    }
    assert report["status"] == "pass"
    assert report["claims"]["qdrant_124_records_included"] is False
    assert report["claims"]["promotion_status"] == "blocked"

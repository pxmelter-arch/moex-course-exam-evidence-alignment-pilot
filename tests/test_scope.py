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


def test_structured_content_candidate_audit() -> None:
    """Validate candidate overlay gates / 驗證 structured candidate gate。"""
    artifact_dir = ROOT / "experiments" / "structured_content_600_candidate_v1"
    manifest = json.loads((artifact_dir / "candidate_input_manifest.json").read_text(encoding="utf-8"))
    report = json.loads((artifact_dir / "candidate_status_report.json").read_text(encoding="utf-8"))
    mismatch_lines = (artifact_dir / "hash_mismatch_quarantine.jsonl").read_text(encoding="utf-8").splitlines()
    provenance_lines = (artifact_dir / "provenance_gap_review_queue.jsonl").read_text(encoding="utf-8").splitlines()

    assert manifest["candidate_name"] == "structured_content_600_candidate_v1"
    assert manifest["record_count"] == 600
    assert manifest["promotion_status"] == "blocked"
    assert manifest["content_lanes"]["content_bearing"] == 520
    assert manifest["content_lanes"]["partial"] == 80
    assert manifest["integrity_lanes"]["hash_mismatch"] == 89
    assert report["provenance_gap_count"] == 600
    assert len(mismatch_lines) == 89
    assert len(provenance_lines) == 600


def test_candidate_text_chunk_pilot() -> None:
    """Validate chunk pilot lanes / 驗證 chunk pilot 分層。"""
    artifact_dir = ROOT / "experiments" / "structured_content_600_candidate_v1" / "text_chunk_pilot"
    report = json.loads((artifact_dir / "candidate_text_chunk_pilot_report.json").read_text(encoding="utf-8"))
    chunk_lines = (artifact_dir / "candidate_chunk_manifest.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["record_count"] == 600
    assert report["record_lane_counts"]["primary_content_bearing"] == 520
    assert report["record_lane_counts"]["partial_sensitivity"] == 80
    assert report["chunk_count"] == 2661
    assert report["chunk_lane_counts"]["primary_content_bearing"] == 2429
    assert report["chunk_lane_counts"]["partial_sensitivity"] == 232
    assert len(chunk_lines) == 2661
    assert report["embedding_executed"] is False
    assert report["promotion_status"] == "blocked"


def test_school_specific_schema_profile() -> None:
    """Validate structural missingness policy / 驗證 source schema 缺失政策。"""
    artifact_dir = ROOT / "experiments/phase1_1_school_schema_v1"
    summary = json.loads((artifact_dir / "school_schema_profile_summary.json").read_text(encoding="utf-8"))
    profile = json.loads((artifact_dir / "school_schema_profile.json").read_text(encoding="utf-8"))

    assert summary["record_count"] == 600
    assert summary["school_count"] == 7
    assert summary["fields_profiled"] == 29
    assert summary["schema_absence_candidates"] == 11
    assert summary["imputation_performed"] is False
    assert summary["model_feature_missingness"] is False
    assert profile["missingness_policy"]["school_schema_difference_is_not_a_different_data_type"] is True
    assert profile["missingness_policy"]["school_quality_ranking_performed"] is False


def test_phase1_audit_artifacts() -> None:
    """Validate Phase 1 audit outputs / 驗證 Phase 1 審計輸出。"""
    artifact_dir = ROOT / "experiments/phase1_audit_v1"
    schema = json.loads(
        (artifact_dir / "phase1_schema_profile.json").read_text(encoding="utf-8")
    )
    identity = json.loads(
        (artifact_dir / "phase1_identity_audit.json").read_text(encoding="utf-8")
    )
    provenance = json.loads(
        (artifact_dir / "phase1_provenance_completeness.json").read_text(encoding="utf-8")
    )
    receipt = json.loads(
        (artifact_dir / "phase1_input_freeze_receipt.json").read_text(encoding="utf-8")
    )
    assert schema["record_count"] == 176
    assert schema["field_count"] == 48
    assert identity["record_count"] == 176
    assert identity["exact_json_duplicate_count"] == 0
    assert identity["key_summaries"]["school_year_semester_department_title"]["duplicate_groups"] == 22
    assert provenance["record_count"] == 176
    assert provenance["declared_provenance"]["local_artifact"]["artifact_missing_count"] == 175
    assert receipt["pinned_commit"] == "5accc1e300d4a6d94c7d1475e44c352b6bf5e54b"
    assert receipt["scope"]["qdrant_124_records_included"] is False
    assert receipt["promotion_status"] == "blocked"

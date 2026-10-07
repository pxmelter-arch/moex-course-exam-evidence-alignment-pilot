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


def test_multi_cause_missingness_audit() -> None:
    """Validate conservative missingness causes / 驗證多原因缺失審計。"""
    artifact_dir = ROOT / "experiments/phase1_1b_missingness_causes_v1"
    report = json.loads((artifact_dir / "missingness_cause_report.json").read_text(encoding="utf-8"))
    queue_lines = (artifact_dir / "missingness_cause_review_queue.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["record_count"] == 600
    assert report["missingness_event_count"] == 3007
    assert report["cause_candidate_counts"]["structural_schema_candidate"] == 1772
    assert report["cause_candidate_counts"]["cause_unresolved"] == 1235
    assert report["cause_candidate_counts"]["source_not_published_or_not_available_or_unresolved"] == 32
    assert len(queue_lines) == 3007
    assert report["policy"]["school_schema_is_only_one_candidate_cause"] is True
    assert report["policy"]["imputation_performed"] is False
    assert report["release_status"] == "blocked_pending_cause_resolution"


def test_exam_outline_catalog_input_freeze() -> None:
    """Validate formal/staged/catalog separation / 驗證 formal、staged、catalog 分離。"""
    artifact_dir = ROOT / "experiments/phase1_2_exam_outline_catalog_v1"
    manifest = json.loads((artifact_dir / "exam_outline_input_manifest.json").read_text(encoding="utf-8"))

    assert manifest["formal_course_input"]["record_count"] == 176
    assert manifest["formal_course_input"]["promotion_status"] == "formal_unchanged"
    assert manifest["priority5_acquisition_input"]["formal_promotions"] == 0
    assert manifest["priority5_acquisition_input"]["promotion_status"] == "staged_not_formal"
    assert manifest["exam_outline_catalog_input"]["subject_count"] == 542
    assert manifest["exam_outline_catalog_input"]["outline_item_count"] == 14022
    assert manifest["exam_outline_catalog_input"]["formal_alignment_status"] == "not_started"
    assert manifest["scope_policy"]["priority5_mixed_into_formal"] is False
    assert manifest["scope_policy"]["qdrant_ingest"] is False
    assert manifest["scope_policy"]["formal_promotion"] == "blocked_pending_identity_provenance_and_expert_review"


def test_phase2_1_course_outline_retrieval() -> None:
    """Validate lexical retrieval diagnostic / 驗證 lexical retrieval 診斷。"""
    artifact_dir = ROOT / "experiments/phase2_1_course_outline_retrieval_v1"
    report = json.loads((artifact_dir / "retrieval_report.json").read_text(encoding="utf-8"))
    result_lines = (artifact_dir / "retrieval_results.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_record_count"] == 176
    assert report["outline_record_count"] == 542
    assert report["top_k"] == 10
    assert report["methods"]["exact_title"]["top1_exact_subject"] == 27
    assert report["methods"]["tfidf"]["top1_exact_subject"] == 25
    assert report["methods"]["bm25"]["top1_exact_subject"] == 18
    assert len(result_lines) == 176
    assert report["candidate_only"] is True
    assert report["formal_alignment"] == "not_started"
    assert report["promotion_status"] == "blocked"


def test_phase2_2_identity_alias_audit() -> None:
    """Validate identity and alias audit / 驗證 identity 與 alias audit。"""
    artifact_dir = ROOT / "experiments/phase2_2_identity_alias_audit_v1"
    report = json.loads((artifact_dir / "audit_report.json").read_text(encoding="utf-8"))
    identity_lines = (artifact_dir / "outline_identity_manifest.jsonl").read_text(encoding="utf-8").splitlines()
    duplicate_groups = json.loads((artifact_dir / "duplicate_subject_groups.json").read_text(encoding="utf-8"))
    review_lines = (artifact_dir / "candidate_review_queue.jsonl").read_text(encoding="utf-8").splitlines()
    alias_lines = (artifact_dir / "course_title_alias_candidates.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["outline_record_id_count"] == 542
    assert report["duplicate_subject_name_group_count"] == 36
    assert report["candidate_review_counts"] == {"ambiguous": 35, "exact": 11, "weak": 130}
    assert report["alias_candidate_count"] == 151
    assert len(identity_lines) == 542
    assert len(duplicate_groups) == 36
    assert len(review_lines) == 176
    assert len(alias_lines) == 151
    assert report["department_scoring"] == "advisory_only"
    assert report["promotion_status"] == "blocked"


def test_phase2_3_formal_syllabus_projection_retrieval() -> None:
    """Validate formal syllabus projection retrieval / 驗證正式 projection retrieval。"""
    artifact_dir = ROOT / "experiments/phase2_3_formal_syllabus_projection_retrieval_v1"
    report = json.loads((artifact_dir / "retrieval_report.json").read_text(encoding="utf-8"))
    result_lines = (artifact_dir / "retrieval_results.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_record_count"] == 176
    assert report["formal_gate_passed_count"] == 176
    assert report["outline_record_count"] == 542
    assert report["methods"]["exact_title"]["top1_exact_subject"] == 27
    assert report["methods"]["tfidf"]["top1_exact_subject"] == 14
    assert report["methods"]["bm25"]["top1_exact_subject"] == 7
    assert len(result_lines) == 176
    assert report["replaces_formal_metadata_only_lane"] is True
    assert report["promotion_status"] == "blocked_pending_alignment_evidence"


def test_phase2_4_section_aware_hybrid_retrieval() -> None:
    """Validate section-aware hybrid retrieval / 驗證 section-aware hybrid。"""
    artifact_dir = ROOT / "experiments/phase2_4_section_aware_hybrid_retrieval_v1"
    report = json.loads((artifact_dir / "retrieval_report.json").read_text(encoding="utf-8"))
    result_lines = (artifact_dir / "retrieval_results.jsonl").read_text(encoding="utf-8").splitlines()
    manifest_lines = (artifact_dir / "section_aware_manifest.jsonl").read_text(encoding="utf-8").splitlines()
    review_lines = (artifact_dir / "review_queue.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_record_count"] == 176
    assert report["formal_gate_passed_count"] == 176
    assert report["outline_record_count"] == 542
    assert report["methods"]["hybrid"]["top1_exact_subject"] == 27
    assert report["methods"]["hybrid"]["top10_exact_subject"] == 27
    assert report["top_candidate_status_counts"] == {"ambiguous": 157, "exact": 10, "weak": 9}
    assert report["review_queue_count"] == 166
    assert len(result_lines) == 176
    assert len(manifest_lines) == 176
    assert len(review_lines) == 166
    assert report["qdrant_ingest"] is False
    assert report["promotion_status"] == "blocked_pending_alignment_evidence"


def test_formal_vs_curated_replacement_audit() -> None:
    """Validate formal replacement audit / 驗證 formal replacement audit。"""
    artifact_dir = ROOT / "experiments/formal_vs_curated_replacement_audit_v1"
    report = json.loads((artifact_dir / "replacement_audit_report.json").read_text(encoding="utf-8"))
    review_lines = (artifact_dir / "curated_replacement_review_queue.jsonl").read_text(encoding="utf-8").splitlines()
    lineage = json.loads((artifact_dir / "input_lineage_manifest.json").read_text(encoding="utf-8"))

    assert report["decision"] == "do_not_replace_formal_176"
    assert lineage["formal"]["records"] == 176
    assert lineage["curated"]["records"] == 600
    assert report["overlap"]["exact_composite_identity_key_count"] == 2
    assert report["overlap"]["exact_raw_sha256_count"] == 2
    assert report["overlap"]["school_title_key_count"] == 7
    assert report["duplicates"]["curated_duplicate_structured_id_groups"] == 0
    assert report["duplicates"]["curated_duplicate_raw_sha256_groups"] == 75
    assert report["curated_quality_partition"]["content_status"] == {"content_bearing": 520, "partial": 80}
    assert report["formal_quality_partition"]["formal_gate"] == {"passed": 176}
    assert len(review_lines) == 600
    assert report["replacement_gate"]["formal_lane_unchanged"] is True
    assert report["replacement_gate"]["curated_can_replace_formal_without_reformalization"] is False


def test_curated_600_section_aware_hybrid() -> None:
    """Validate curated experimental retrieval / 驗證 curated 實驗 retrieval。"""
    artifact_dir = ROOT / "experiments/curated_600_section_aware_hybrid_v1"
    report = json.loads((artifact_dir / "retrieval_report.json").read_text(encoding="utf-8"))
    result_lines = (artifact_dir / "content_bearing_results.jsonl").read_text(encoding="utf-8").splitlines()
    partial_lines = (artifact_dir / "partial_abstention_queue.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["curated_records"] == 600
    assert report["content_bearing_records"] == 520
    assert report["partial_records"] == 80
    assert report["retrieval_records"] == 520
    assert report["outline_records"] == 542
    assert report["top_candidate_status_counts"] == {"ambiguous": 491, "exact": 12, "weak": 17}
    assert report["partial_abstention_count"] == 80
    assert len(result_lines) == 520
    assert len(partial_lines) == 80
    assert report["qdrant_ingest"] is False
    assert report["promotion_status"] == "blocked_experimental_only"


def test_phase2_5_formal_retrieval_ablation() -> None:
    """Validate formal ablation / 驗證 formal ablation。"""
    artifact_dir = ROOT / "experiments/phase2_5_formal_retrieval_ablation_v1"
    report = json.loads((artifact_dir / "ablation_report.json").read_text(encoding="utf-8"))
    rows = (artifact_dir / "ablation_results.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_records"] == 176
    assert report["outline_records"] == 542
    assert report["methods"]["title_identity"] == {"query_count": 176, "top1_exact_subject": 27, "top10_exact_subject": 27}
    assert report["methods"]["topic_only"] == {"query_count": 176, "top1_exact_subject": 11, "top10_exact_subject": 17}
    assert report["methods"]["content_topic_only"] == {"query_count": 176, "top1_exact_subject": 15, "top10_exact_subject": 19}
    assert report["methods"]["section_hybrid"] == {"query_count": 176, "top1_exact_subject": 27, "top10_exact_subject": 27}
    assert len(rows) == 176
    assert report["qdrant_ingest"] is False
    assert report["promotion_status"] == "blocked_pending_alignment_evidence"


def test_phase2_6_formal_chunk_dense_hybrid_evidence() -> None:
    """Validate formal chunk/dense/evidence pipeline / 驗證 formal pipeline。"""
    artifact_dir = ROOT / "experiments/phase2_6_formal_chunk_dense_hybrid_evidence_v1"
    report = json.loads((artifact_dir / "pipeline_report.json").read_text(encoding="utf-8"))
    chunks = (artifact_dir / "section_chunks.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in (artifact_dir / "course_chunk_hybrid_results.jsonl").read_text(encoding="utf-8").splitlines()]

    assert report["formal_records"] == 176
    assert report["outline_records"] == 542
    assert report["chunk_count"] == 1490
    assert report["metrics"]["top1_exact_subject"] == 22
    assert report["metrics"]["top10_exact_subject"] == 24
    assert report["metrics"]["top_candidate_status_counts"] == {"ambiguous": 168, "exact": 8, "weak": 0}
    assert len(chunks) == 1490
    assert len(rows) == 176
    assert all(len(row["candidates"]) == 10 for row in rows)
    assert all(candidate["evidence_span"]["chunk_id"] for row in rows for candidate in row["candidates"])
    assert all(candidate["evidence_span"]["source_path"] for row in rows for candidate in row["candidates"])
    assert report["embedding"]["local_only"] is True
    assert report["qdrant_ingest"] is False
    assert report["promotion_status"] == "blocked_pending_alignment_evidence"


def test_phase2_6_formal_error_analysis() -> None:
    """Validate formal error stages / 驗證 formal error stages。"""
    artifact_dir = ROOT / "experiments/phase2_6_formal_chunk_dense_hybrid_evidence_v1"
    report = json.loads((artifact_dir / "error_analysis_report.json").read_text(encoding="utf-8"))
    rows = (artifact_dir / "error_analysis_records.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_records"] == 176
    assert report["catalog_exact_title_records"] == 27
    assert report["summary"] == {
        "exact_excluded_by_course_gate": 3,
        "exact_survives_gate_and_top10": 24,
        "no_exact_title_in_catalog": 149,
    }
    assert report["top1_exact_subject"] == 22
    assert len(rows) == 176
    assert report["interpretation"]["promotion_status"] == "blocked"


def test_phase2_7_formal_identity_bridge() -> None:
    """Validate identity bridge / 驗證 formal identity bridge。"""
    artifact_dir = ROOT / "experiments/phase2_7_formal_identity_bridge_v1"
    report = json.loads((artifact_dir / "identity_bridge_report.json").read_text(encoding="utf-8"))
    candidates = (artifact_dir / "identity_bridge_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    review = (artifact_dir / "identity_review_queue.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_records"] == 176
    assert report["outline_records"] == 542
    assert report["duplicate_subject_name_groups"] == 36
    assert report["identity_status_counts"] == {"ambiguous": 20, "exact": 13, "weak": 143}
    assert report["course_gate_exact_recovered"] == 3
    assert len(candidates) == 176
    assert len(review) == 163
    assert report["promotion_status"] == "blocked"
    assert report["qdrant_ingest"] is False


def test_phase2_8_identity_expanded_pool_comparison() -> None:
    """Validate paired candidate-pool comparison / 驗證 paired comparison。"""
    artifact_dir = ROOT / "experiments/phase2_8_identity_expanded_pool_comparison_v1"
    report = json.loads((artifact_dir / "comparison_report.json").read_text(encoding="utf-8"))
    rows = (artifact_dir / "paired_comparison.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_records"] == 176
    assert report["outline_records"] == 542
    assert report["original_pool"]["metrics"] == {"ambiguous_top10": 1750, "top1_exact": 22, "top10_exact": 24}
    assert report["expanded_pool"]["metrics"] == {"ambiguous_top10": 1747, "top1_exact": 22, "top10_exact": 27}
    assert report["gate_miss_recovery"]["count"] == 3
    assert len(rows) == 176
    assert sum(json.loads(row)["recovered_top10"] for row in rows) == 3
    assert report["promotion_status"] == "blocked"
    assert report["qdrant_ingest"] is False


def test_phase2_completion_audit() -> None:
    """Validate Phase 2 completion gates / 驗證 Phase 2 completion gates。"""
    artifact = ROOT / "experiments/phase2_completion_v1/phase2_completion_report.json"
    report = json.loads(artifact.read_text(encoding="utf-8"))
    assert report["phase2_status"] == "complete_for_candidate_retrieval_diagnostic"
    assert report["formal_alignment_status"] == "not_started"
    assert report["all_diagnostic_gates_pass"] is True
    assert report["results"] == {
        "ambiguous_delta": -3,
        "expanded_top10_exact": 27,
        "formal_records": 176,
        "gate_miss_recovery": 3,
        "identity_status_counts": {"ambiguous": 20, "exact": 13, "weak": 143},
        "original_top10_exact": 24,
        "outline_records": 542,
        "phase2_6_top10_exact": 24,
        "phase2_6_top1_exact": 22,
        "section_chunks": 1490,
    }


def test_phase3_independent_evidence_audit() -> None:
    """Validate Phase 3 evidence packs / 驗證 Phase 3 evidence packs。"""
    artifact_dir = ROOT / "experiments/phase3_independent_evidence_audit_v1"
    report = json.loads((artifact_dir / "phase3_evidence_audit_report.json").read_text(encoding="utf-8"))
    packs = (artifact_dir / "evidence_packs.jsonl").read_text(encoding="utf-8").splitlines()
    blockers = (artifact_dir / "promotion_blocker_queue.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_records"] == 176
    assert report["expanded_top10_evidence_packs"] == 1760
    assert report["status_counts"] == {"blocked": 1760}
    assert report["blocker_counts"] == {
        "ambiguous_candidate_requires_review": 1747,
        "chunk_evidence_span_missing_from_phase2_6_top10": 5,
        "human_adjudication_required": 1760,
        "independent_cross_source_validation_missing": 1760,
    }
    assert len(packs) == 1760
    assert len(blockers) == 1760
    assert report["promotion_status"] == "blocked"
    assert report["qdrant_ingest"] is False


def test_phase3_topic_refinement_extraction() -> None:
    """Validate topic extraction pilot / 驗證 topic extraction pilot。"""
    artifact_dir = ROOT / "experiments/phase3_retrieval_refinement_v1"
    report = json.loads((artifact_dir / "refinement_report.json").read_text(encoding="utf-8"))
    syllabus = (artifact_dir / "syllabus_section_parse.jsonl").read_text(encoding="utf-8").splitlines()
    chunks = (artifact_dir / "syllabus_atomic_topic_chunks.jsonl").read_text(encoding="utf-8").splitlines()
    outline_items = (artifact_dir / "outline_atomic_items.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_records"] == 176
    assert report["outline_records"] == 542
    assert report["syllabus_sections"] == 176
    assert report["syllabus_atomic_topic_chunks"] == 4750
    assert report["outline_atomic_items"] == 2573
    assert report["raw_preserved"] is True
    assert report["machine_inference_only"] is True
    assert len(syllabus) == 176
    assert len(chunks) == 4750
    assert len(outline_items) == 2573
    assert report["promotion_status"] == "blocked"


def test_phase3_topic_coverage_reranking() -> None:
    """Validate topic coverage reranking / 驗證 topic coverage reranking。"""
    artifact_dir = ROOT / "experiments/phase3_topic_coverage_reranking_v1"
    report = json.loads((artifact_dir / "topic_coverage_reranking_report.json").read_text(encoding="utf-8"))
    results = (artifact_dir / "coverage_reranked_results.jsonl").read_text(encoding="utf-8").splitlines()
    matches = (artifact_dir / "topic_match_evidence.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["formal_records"] == 176
    assert report["syllabus_atomic_chunks"] == 4750
    assert report["outline_atomic_items"] == 2573
    assert report["candidate_rows"] == 1760
    assert report["baseline_expanded"] == {"top1_exact": 22, "top10_exact": 27}
    assert report["coverage_reranked"] == {"top1_exact": 22, "top10_exact": 27}
    assert report["delta"] == {"top1": 0, "top10": 0}
    assert len(results) == 176
    assert len(matches) == 1760
    assert report["promotion_status"] == "blocked"
    assert report["qdrant_ingest"] is False


def test_phase3_negative_result_audits() -> None:
    """Validate negative-result audits / 驗證 negative-result audits。"""
    artifact_dir = ROOT / "experiments/phase3_negative_result_audits_v1"
    report = json.loads((artifact_dir / "negative_result_audit_report.json").read_text(encoding="utf-8"))
    queue = (artifact_dir / "human_review_queue.jsonl").read_text(encoding="utf-8").splitlines()
    assert report["hierarchy"]["syllabus_chapter_unresolved"] == 4750
    assert report["hierarchy"]["outline_chapter_unresolved"] == 2573
    assert report["contamination"]["syllabus_flagged_chunks"] == 632
    assert report["contamination"]["outline_flagged_items"] == 57
    assert all(metrics == {"top1_exact": 22, "top10_exact": 27} for metrics in report["threshold_sensitivity"].values())
    assert report["weight_ablation"]["identity_removed"]["top1_exact"] == 2
    assert report["independent_corroboration"]["independent_corroboration_ready"] == 0
    assert report["human_review"]["queue_size"] == 1760
    assert report["human_review"]["machine_labels_created"] == 0
    assert len(queue) == 1760
    assert report["promotion_status"] == "blocked"
    assert report["qdrant_ingest"] is False


def test_phase2_3a_primary_content_retrieval() -> None:
    """Validate primary content retrieval / 驗證 primary content retrieval。"""
    artifact_dir = ROOT / "experiments/phase2_3a_primary_content_retrieval_v1"
    report = json.loads((artifact_dir / "retrieval_report.json").read_text(encoding="utf-8"))
    result_lines = (artifact_dir / "retrieval_results.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["content_total_count"] == 600
    assert report["primary_content_bearing_count"] == 520
    assert report["outline_record_count"] == 542
    assert report["methods"]["exact_title"]["top1_exact_subject"] == 35
    assert report["methods"]["tfidf"]["top1_exact_subject"] == 16
    assert report["methods"]["bm25"]["top1_exact_subject"] == 17
    assert len(result_lines) == 520
    assert report["priority5_373_lane"] == "blocked_pending_materialized_pinned_artifact"
    assert report["promotion_status"] == "blocked"


def test_phase2_3b_priority5_freeze() -> None:
    """Validate 373-record staged freeze / 驗證 373 筆 staged freeze。"""
    artifact_dir = ROOT / "experiments/phase2_3b_priority5_staged_freeze_v1"
    report = json.loads((artifact_dir / "freeze_report.json").read_text(encoding="utf-8"))
    manifest_lines = (artifact_dir / "priority5_staged_manifest.jsonl").read_text(encoding="utf-8").splitlines()
    overlap = json.loads((artifact_dir / "overlap_audit.json").read_text(encoding="utf-8"))
    duplicates = json.loads((artifact_dir / "duplicate_audit.json").read_text(encoding="utf-8"))

    assert report["source_counts"] == {"SCH006": 6, "SCH014": 261, "SCH022": 17, "SCH026": 89}
    assert report["staged_record_count"] == 373
    assert report["overlap_with_primary_count"] == 302
    assert report["duplicate_within_staged_count"] == 54
    assert report["quarantine_count"] == 251
    assert report["provenance_incomplete_count"] == 0
    assert len(manifest_lines) == 373
    assert len(overlap) == 302
    assert len(duplicates) == 54
    assert report["promotion_status"] == "blocked"


def test_phase2_3b_priority5_retrieval_and_comparison() -> None:
    """Validate staged retrieval and lane comparison / 驗證 staged retrieval。"""
    retrieval_dir = ROOT / "experiments/phase2_3b_priority5_staged_retrieval_v1"
    comparison_dir = ROOT / "experiments/phase2_3_lane_comparison_v1"
    report = json.loads((retrieval_dir / "retrieval_report.json").read_text(encoding="utf-8"))
    comparison = json.loads((comparison_dir / "lane_comparison.json").read_text(encoding="utf-8"))
    result_lines = (retrieval_dir / "retrieval_results.jsonl").read_text(encoding="utf-8").splitlines()

    assert report["staged_record_count"] == 373
    assert report["outline_record_count"] == 542
    assert report["methods"]["exact_title"]["top1_exact_subject"] == 79
    assert report["methods"]["tfidf"]["top1_exact_subject"] == 70
    assert report["methods"]["bm25"]["top1_exact_subject"] == 63
    assert len(result_lines) == 373
    assert comparison["primary"]["query_count"] == 520
    assert comparison["staged"]["query_count"] == 373
    assert comparison["staged"]["overlap_query_count"] == 302
    assert comparison["staged"]["quarantine_query_count"] == 251
    assert comparison["promotion_status"] == "blocked"


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

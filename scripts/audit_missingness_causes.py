"""Audit multiple possible missingness causes conservatively.

A school-specific schema difference is only one candidate cause. This script
never treats a null as proof of non-publication, extraction failure, or absent
content without direct evidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

SOURCE_PATH = "output/unified_dataset/round26_20261004/structured_content_600.json"
EXPECTED_COMMIT = "6454e22c2ad00087d62481171352738eb3396bad"

FIELD_CLASSES = {
    "school_id": "identity_critical",
    "school_name": "identity_critical",
    "course_title": "identity_critical",
    "course_code": "identity_critical",
    "academic_year": "identity_critical",
    "semester": "identity_critical",
    "department": "conditional_identity",
    "official_url": "provenance_critical",
    "raw_artifact_path": "provenance_critical",
    "raw_sha256": "provenance_critical",
    "content_text": "content_critical",
    "content_sections": "content_critical",
    "content_status": "content_critical",
    "teacher": "descriptive",
    "assessment": "descriptive",
    "textbook": "descriptive",
    "reference": "descriptive",
    "prerequisite": "conditional",
    "target_program": "conditional",
}


def nonempty(value: Any) -> bool:
    """Return whether a value is meaningfully present / 判斷是否有實質值。"""
    return value not in (None, "", [], {})


def read_records(repo: Path, commit: str) -> list[dict[str, Any]]:
    """Read the pinned dataset / 讀取固定版本資料集。"""
    raw = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{commit}:{SOURCE_PATH}"]
    )
    records = json.loads(raw)
    if not isinstance(records, list):
        raise ValueError("expected JSON array")
    return records


def main() -> int:
    """Generate conservative missingness classifications / 產生保守缺失分類。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--commit", default=EXPECTED_COMMIT)
    parser.add_argument("--schema-profile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = read_records(args.source_repo, args.commit)
    schema_profile = json.loads(args.schema_profile.read_text(encoding="utf-8"))
    school_profiles = schema_profile["school_profiles"]
    fields = sorted({key for record in records for key in record})
    events = []
    cause_counts = Counter()
    field_counts = Counter()

    for record in records:
        school_id = str(record.get("school_id"))
        for field in fields:
            if nonempty(record.get(field)):
                continue
            profile = school_profiles[school_id]["field_profile"].get(field, {})
            availability_class = profile.get("availability_class")
            reasons = []
            evidence = []
            if availability_class == "schema_absence_candidate":
                reasons.append("structural_schema_candidate")
                evidence.append("field_absent_for_all_records_in_this_school_snapshot")
            if field == "official_url":
                reasons.append("source_not_published_or_not_available_or_unresolved")
                evidence.append("official_url_missing_in_candidate_record")
            if field in {"content_text", "content_sections"}:
                reasons.append("extraction_or_content_unresolved")
                evidence.append("content_field_empty_or_null")
            if record.get("hash_status") == "mismatch" and field in {
                "raw_artifact_path", "raw_sha256", "content_text", "content_sections"
            }:
                reasons.append("integrity_conflict")
                evidence.append("hash_status_mismatch")
            if not reasons:
                reasons.append("cause_unresolved")
                evidence.append("no_direct_cause_evidence_in_snapshot")
            # A schema candidate is never allowed to suppress other possible causes.
            if "structural_schema_candidate" in reasons:
                reasons.append("other_causes_not_excluded")
            event = {
                "structured_id": record.get("structured_id"),
                "school_id": school_id,
                "field_name": field,
                "field_semantic_class": FIELD_CLASSES.get(field, "unclassified"),
                "source_schema_availability": availability_class,
                "missingness_reason_candidates": sorted(set(reasons)),
                "evidence": evidence,
                "cause_confidence": "advisory",
                "requires_source_check": True,
                "imputation_performed": False,
                "model_feature_created": False,
            }
            events.append(event)
            field_counts[field] += 1
            for reason in event["missingness_reason_candidates"]:
                cause_counts[reason] += 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "missingness_cause_review_queue.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    report = {
        "experiment": "phase1_1b_multi_cause_missingness_audit",
        "source_path": SOURCE_PATH,
        "source_commit": args.commit,
        "record_count": len(records),
        "missingness_event_count": len(events),
        "cause_candidate_counts": dict(cause_counts),
        "field_missingness_event_counts": dict(field_counts),
        "policy": {
            "school_schema_is_only_one_candidate_cause": True,
            "null_is_not_treated_as_content_absence": True,
            "cause_inference_is_advisory": True,
            "direct_source_check_required": True,
            "imputation_performed": False,
            "missingness_as_model_feature": False,
            "school_quality_ranking": False,
        },
        "release_status": "blocked_pending_cause_resolution",
    }
    (args.output_dir / "missingness_cause_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "pass",
        "records": len(records),
        "missingness_events": len(events),
        "cause_candidates": dict(cause_counts),
        "release_status": report["release_status"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

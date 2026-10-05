"""Profile source-specific schema availability without treating it as data quality.

This experiment separates source-schema absence from record-level nulls. It does
not impute values, add missingness as a model feature, or rank schools by data
completeness.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
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
    """Return whether a value contains data / 判斷欄位是否有實質內容。"""
    return value not in (None, "", [], {})


def read_records(repo: Path, commit: str) -> list[dict[str, Any]]:
    """Read records from the pinned Git object / 讀取固定 commit 資料。"""
    raw = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{commit}:{SOURCE_PATH}"]
    )
    records = json.loads(raw)
    if not isinstance(records, list):
        raise ValueError("expected JSON array")
    return records


def classify_rate(rate: float) -> str:
    """Classify availability without quality ranking / 分類欄位可用性。"""
    if rate == 0:
        return "schema_absence_candidate"
    if rate == 1:
        return "source_consistently_present"
    return "source_heterogeneous_or_record_missing"


def main() -> int:
    """Generate school schema profiles / 產生學校特定 schema profile。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--commit", default=EXPECTED_COMMIT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = read_records(args.source_repo, args.commit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for record in records for key in record})
    by_school: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_school[str(record.get("school_id"))].append(record)

    school_profiles: dict[str, Any] = {}
    matrix: dict[str, Any] = {}
    for school_id, school_records in sorted(by_school.items()):
        field_profile = {}
        for field in fields:
            present = sum(nonempty(record.get(field)) for record in school_records)
            rate = present / len(school_records)
            field_profile[field] = {
                "record_count": len(school_records),
                "present_count": present,
                "absent_count": len(school_records) - present,
                "presence_rate": round(rate, 6),
                "availability_class": classify_rate(rate),
                "semantic_class": FIELD_CLASSES.get(field, "unclassified"),
            }
        school_profiles[school_id] = {
            "record_count": len(school_records),
            "field_profile": field_profile,
        }
        matrix[school_id] = {
            field: field_profile[field]["availability_class"] for field in fields
        }

    # These are schema observations, not school quality scores.
    source_schema_candidates = {}
    for field in fields:
        classes = Counter(
            school_profiles[school_id]["field_profile"][field]["availability_class"]
            for school_id in school_profiles
        )
        source_schema_candidates[field] = {
            "field_semantic_class": FIELD_CLASSES.get(field, "unclassified"),
            "school_availability_class_counts": dict(classes),
            "interpretation": (
                "schema-level observation only; do not use as a school quality score "
                "or model feature"
            ),
        }

    report = {
        "experiment": "phase1_1_school_specific_schema_profile",
        "source_path": SOURCE_PATH,
        "source_commit": args.commit,
        "record_count": len(records),
        "school_count": len(school_profiles),
        "missingness_policy": {
            "school_schema_difference_is_not_a_different_data_type": True,
            "schema_absence_is_not_a_negative_label": True,
            "missingness_added_as_model_feature": False,
            "imputation_performed": False,
            "school_quality_ranking_performed": False,
            "source_native_fields_preserved": True,
            "canonical_nulls_preserved": True,
        },
        "field_semantic_classes": FIELD_CLASSES,
        "source_schema_candidates": source_schema_candidates,
        "school_profiles": school_profiles,
        "availability_matrix": matrix,
    }
    (args.output_dir / "school_schema_profile.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "experiment": report["experiment"],
        "record_count": len(records),
        "school_count": len(school_profiles),
        "fields_profiled": len(fields),
        "schema_absence_candidates": sum(
            1
            for field in source_schema_candidates.values()
            if field["school_availability_class_counts"].get("schema_absence_candidate", 0)
        ),
        "imputation_performed": False,
        "model_feature_missingness": False,
        "status": "pass",
    }
    (args.output_dir / "school_schema_profile_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

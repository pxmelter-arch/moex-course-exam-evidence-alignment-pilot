"""Run Phase 1 schema, NLP, identity, and provenance audits.

The script reads the Phase 0 pinned GitHub dataset and writes metadata-only
artifacts. It never writes to the source clone and never uses Qdrant/qmd.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

EXPECTED_COMMIT = "5accc1e300d4a6d94c7d1475e44c352b6bf5e54b"
EXPECTED_RECORD_COUNT = 176
DATASET_RELATIVE_PATH = "output/dataset/round26_formal_dataset_2026-10-02.json"
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
WHITESPACE_RE = re.compile(r"\s+")
PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "（": "(",
        "）": ")",
        "［": "[",
        "］": "]",
        "【": "[",
        "】": "]",
        "，": ",",
        "：": ":",
        "；": ";",
        "／": "/",
        "－": "-",
        "–": "-",
        "—": "-",
    }
)


def run_git(source_repo: Path, *args: str) -> str:
    """Run a read-only Git command / 執行唯讀 Git 指令。"""
    result = subprocess.run(
        ["git", "-C", str(source_repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    """Return a file SHA-256 / 計算檔案 SHA-256。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    """Convert values to JSON-safe deterministic values / 轉為可序列化值。"""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return str(value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write stable UTF-8 JSON / 寫入穩定格式 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    """Write UTF-8 JSONL / 寫入 UTF-8 JSONL。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def raw_text(value: Any) -> str:
    """Return a trimmed source string / 取得來源字串。"""
    if value is None:
        return ""
    return str(value).strip()


def normalize_text(value: Any) -> str:
    """Apply deterministic text normalization / 執行可重現文字正規化。"""
    text = unicodedata.normalize("NFKC", raw_text(value))
    text = text.translate(PUNCTUATION_TRANSLATION)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text.casefold()


def canonical_key(value: Any) -> str:
    """Build a conservative comparison key / 建立保守比對鍵。"""
    text = normalize_text(value)
    return re.sub(r"[\s\-_,;:()\[\]/]+", "", text)


def normalize_semester(value: Any) -> str:
    """Normalize semester notation without dropping term information."""
    text = normalize_text(value)
    mapping = {
        "上學期": "1",
        "第一學期": "1",
        "1": "1",
        "下學期": "2",
        "第二學期": "2",
        "2": "2",
    }
    return mapping.get(text, text)


def normalize_degree(value: Any) -> str:
    """Normalize degree labels conservatively / 保守統一學制標籤。"""
    text = normalize_text(value)
    mapping = {
        "bachelor": "bachelor",
        "undergraduate programme": "bachelor",
        "undergraduate program": "bachelor",
        "master": "master",
        "碩士": "master",
        "學士": "bachelor",
    }
    return mapping.get(text, text)


def normalize_code(value: Any) -> str:
    """Normalize course code formatting without inferring missing codes."""
    return re.sub(r"\s+", "", normalize_text(value)).upper()


def parse_bool(value: Any) -> bool | None:
    """Parse explicit boolean values / 解析明確布林值。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.casefold() in {"true", "false"}:
        return value.casefold() == "true"
    return None


def value_type(value: Any) -> str:
    """Return a compact type label / 回傳欄位型別標籤。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def key_value(record: dict[str, Any], key_fields: list[str]) -> tuple[str, ...]:
    """Build a normalized identity key / 建立正規化 identity key。"""
    result: list[str] = []
    for field in key_fields:
        value = record.get(field)
        if field == "semester":
            result.append(normalize_semester(value))
        elif field == "course_code":
            result.append(normalize_code(value))
        else:
            result.append(canonical_key(value))
    return tuple(result)


def group_records(records: list[dict[str, Any]], key_fields: list[str]) -> dict[str, list[int]]:
    """Group records by normalized key / 依正規化 key 分組。"""
    groups: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        key = "|".join(key_value(record, key_fields))
        groups[key].append(index)
    return dict(groups)


def collision_rows(
    records: list[dict[str, Any]], key_fields: list[str]
) -> list[dict[str, Any]]:
    """Return duplicate groups with ambiguity metadata / 輸出 collision 群組。"""
    groups = group_records(records, key_fields)
    rows: list[dict[str, Any]] = []
    for key, indexes in groups.items():
        if len(indexes) < 2:
            continue
        comparable_fields = [
            "school_id",
            "academic_year",
            "semester",
            "department_name",
            "course_code",
            "course_title",
            "class_code",
            "class_label",
            "section",
            "official_url",
            "raw_sha256",
            "target_program",
        ]
        differences = {
            field: sorted({raw_text(records[index].get(field)) for index in indexes})
            for field in comparable_fields
            if len({raw_text(records[index].get(field)) for index in indexes}) > 1
        }
        rows.append(
            {
                "key_fields": key_fields,
                "normalized_key": key,
                "record_indexes": indexes,
                "record_count": len(indexes),
                "difference_fields": differences,
                "identity_resolution_status": "ambiguous_collision",
                "machine_inference": True,
                "human_review_status": "unreviewed",
            }
        )
    return rows


def resolve_artifact_path(source_repo: Path, value: Any) -> Path | None:
    """Resolve a declared raw path against the pinned clone."""
    path_text = raw_text(value)
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_absolute():
        path = source_repo / path
    return path


def build_audit(source_repo: Path, output_dir: Path) -> dict[str, Any]:
    """Run all Phase 1 audits and write artifacts / 執行 Phase 1 審計。"""
    source_repo = source_repo.resolve()
    output_dir = output_dir.resolve()
    head = run_git(source_repo, "rev-parse", "HEAD")
    if head != EXPECTED_COMMIT:
        raise RuntimeError(f"Pinned commit mismatch: expected {EXPECTED_COMMIT}, got {head}")
    dataset_path = source_repo / DATASET_RELATIVE_PATH
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    records = dataset["records"]
    if len(records) != EXPECTED_RECORD_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_RECORD_COUNT}, got {len(records)}")

    generated_at = datetime.now(timezone.utc).isoformat()
    field_names = sorted({field for record in records for field in record})
    schema_profile: dict[str, Any] = {
        "report_version": "phase1-schema-profile-v1",
        "generated_at_utc": generated_at,
        "record_count": len(records),
        "field_count": len(field_names),
        "fields": {},
        "schema_drift": {
            "additional_properties_allowed_by_source_schema": True,
            "type_inconsistency_fields": [],
        },
    }
    for field in field_names:
        values = [record.get(field) for record in records]
        non_null = [value for value in values if value is not None]
        type_counts = Counter(value_type(value) for value in non_null)
        blank_count = sum(isinstance(value, str) and not value.strip() for value in values)
        distinct_values = {json.dumps(json_safe(value), ensure_ascii=False, sort_keys=True) for value in non_null}
        schema_profile["fields"][field] = {
            "type_counts": dict(sorted(type_counts.items())),
            "null_count": sum(value is None for value in values),
            "blank_string_count": blank_count,
            "non_null_count": len(non_null),
            "distinct_count": len(distinct_values),
        }
        if len(type_counts) > 1:
            schema_profile["schema_drift"]["type_inconsistency_fields"].append(field)

    key_specs = {
        "school_year_semester_department_code": [
            "school_id", "academic_year", "semester", "department_name", "course_code"
        ],
        "school_year_semester_department_title": [
            "school_id", "academic_year", "semester", "department_name", "course_title"
        ],
        "school_year_semester_code_title": [
            "school_id", "academic_year", "semester", "course_code", "course_title"
        ],
        "school_year_semester_department_code_title": [
            "school_id", "academic_year", "semester", "department_name", "course_code", "course_title"
        ],
    }
    identity_summary: dict[str, Any] = {
        "report_version": "phase1-identity-audit-v1",
        "generated_at_utc": generated_at,
        "record_count": len(records),
        "exact_json_duplicate_count": len(records)
        - len({json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records}),
        "key_summaries": {},
        "identity_policy": {
            "course_instance_key": [
                "school_id", "academic_year", "canonical_semester", "canonical_department",
                "canonical_course_code", "canonical_section_or_class_code", "canonical_course_title"
            ],
            "source_instance_fallback": ["school_id", "academic_year", "canonical_semester", "official_url", "raw_sha256"],
            "missing_code_status": "ambiguous_missing_code",
            "machine_inference_is_not_truth": True,
        },
    }
    all_collision_rows: list[dict[str, Any]] = []
    for name, fields in key_specs.items():
        rows = collision_rows(records, fields)
        groups = group_records(records, fields)
        duplicate_records = sum(len(indexes) for indexes in groups.values() if len(indexes) > 1)
        identity_summary["key_summaries"][name] = {
            "key_fields": fields,
            "unique_groups": len(groups),
            "duplicate_groups": len(rows),
            "duplicate_records": duplicate_records,
        }
        for row in rows:
            row["key_name"] = name
        all_collision_rows.extend(rows)

    provenance_fields = [
        "official_url", "raw_artifact_path", "raw_sha256", "syllabus_http_status",
        "syllabus_content_bearing", "formal_gate", "promotion_status",
    ]
    declared: dict[str, Any] = {"fields": {}, "local_artifact": {}}
    for field in provenance_fields:
        values = [record.get(field) for record in records]
        declared["fields"][field] = {
            "non_null_count": sum(value is not None for value in values),
            "blank_count": sum(isinstance(value, str) and not value.strip() for value in values),
        }
    local_exists = 0
    local_hash_verified = 0
    local_hash_mismatch = 0
    missing_local = []
    for index, record in enumerate(records):
        artifact = resolve_artifact_path(source_repo, record.get("raw_artifact_path"))
        exists = artifact is not None and artifact.is_file()
        if exists and artifact is not None:
            local_exists += 1
            actual_hash = sha256_file(artifact)
            if actual_hash == raw_text(record.get("raw_sha256")):
                local_hash_verified += 1
            else:
                local_hash_mismatch += 1
        else:
            missing_local.append(index)
    declared["local_artifact"] = {
        "artifact_exists_count": local_exists,
        "artifact_missing_count": len(missing_local),
        "artifact_hash_verified_count": local_hash_verified,
        "artifact_hash_mismatch_count": local_hash_mismatch,
        "missing_record_indexes": missing_local,
    }
    provenance_report = {
        "report_version": "phase1-provenance-completeness-v1",
        "generated_at_utc": generated_at,
        "record_count": len(records),
        "declared_provenance": declared,
        "interpretation": {
            "declared_fields_are_not_equivalent_to_local_raw_byte_verification": True,
            "null_http_status_is_not_inferred_as_success": True,
            "formal_gate_is_not_exam_alignment_truth": True,
        },
        "limitations": [
            "The pinned clone contains only the raw artifacts physically available in that clone.",
            "Missing local artifacts remain provenance gaps even when the record declares a path and hash.",
            "No human adjudication is available in this phase.",
        ],
    }

    normalized_rows: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        title_raw = raw_text(record.get("course_title"))
        code_raw = raw_text(record.get("course_code"))
        department_raw = raw_text(record.get("department_name"))
        normalized_rows.append(
            {
                "record_index": index,
                "record_identity": {
                    "school_id": raw_text(record.get("school_id")),
                    "academic_year": raw_text(record.get("academic_year")),
                    "semester_raw": raw_text(record.get("semester")),
                    "semester_normalized": normalize_semester(record.get("semester")),
                    "degree_level_raw": raw_text(record.get("degree_level")),
                    "degree_level_normalized": normalize_degree(record.get("degree_level")),
                    "department_name_raw": department_raw,
                    "department_name_normalized": normalize_text(department_raw),
                    "course_code_raw": code_raw,
                    "course_code_normalized": normalize_code(code_raw),
                    "class_code_raw": raw_text(record.get("class_code")),
                    "class_code_normalized": normalize_code(record.get("class_code")),
                    "course_title_raw": title_raw,
                    "course_title_normalized": normalize_text(title_raw),
                    "course_title_canonical_key": canonical_key(title_raw),
                },
                "provenance_reference": {
                    "candidate_id": raw_text(record.get("candidate_id")),
                    "official_url": raw_text(record.get("official_url")),
                    "raw_artifact_path": raw_text(record.get("raw_artifact_path")),
                    "raw_sha256": raw_text(record.get("raw_sha256")),
                },
                "normalization": {
                    "operations": [
                        "unicode_nfkc",
                        "unicode_whitespace_collapse",
                        "punctuation_canonicalization",
                        "casefold",
                    ],
                    "machine_inference": False,
                    "review_status": "unreviewed",
                    "raw_semantics_note": "course_title is retained as the existing source field; raw-origin semantics are not independently proven",
                },
                "identity_resolution_status": (
                    "missing_course_code_review_required" if not code_raw else "candidate_only_unreviewed"
                ),
                "machine_inference": True,
                "human_review_status": "unreviewed",
            }
        )

    input_receipt = {
        "receipt_version": "phase1-input-freeze-receipt-v1",
        "generated_at_utc": generated_at,
        "repository": "caperspeert-blip/moex-course-exam-alignment",
        "pinned_commit": EXPECTED_COMMIT,
        "dataset_relative_path": DATASET_RELATIVE_PATH,
        "dataset_sha256": sha256_file(dataset_path),
        "record_count": len(records),
        "read_only_source_confirmation": True,
        "scope": {
            "qdrant_124_records_included": False,
            "uploaded_excel_included": False,
            "qmd_used": False,
            "staged_included": False,
            "quarantine_included": False,
            "blocked_included": False,
        },
        "human_adjudication_available": False,
        "promotion_status": "blocked",
    }
    write_json(output_dir / "phase1_schema_profile.json", schema_profile)
    write_json(output_dir / "phase1_identity_audit.json", identity_summary)
    write_jsonl(output_dir / "phase1_identity_collisions.jsonl", all_collision_rows)
    write_json(output_dir / "phase1_provenance_completeness.json", provenance_report)
    write_jsonl(output_dir / "phase1_title_normalization_candidates.jsonl", normalized_rows)
    write_jsonl(output_dir / "phase1_schema_normalized_records.jsonl", normalized_rows)
    write_json(output_dir / "phase1_input_freeze_receipt.json", input_receipt)
    return {
        "status": "pass",
        "record_count": len(records),
        "field_count": len(field_names),
        "identity_collision_rows": len(all_collision_rows),
        "local_artifact_exists": local_exists,
        "local_artifact_hash_verified": local_hash_verified,
        "local_artifact_missing": len(missing_local),
    }


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/phase1_audit_v1"),
    )
    return parser.parse_args()


def main() -> None:
    """Run the Phase 1 audit / 執行 Phase 1 審計。"""
    args = parse_args()
    summary = build_audit(args.source_repo, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

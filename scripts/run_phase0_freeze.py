"""Create the reproducible Phase 0 input freeze artifacts.

This script reads the pinned GitHub dataset clone in read-only mode and writes
only metadata/checksum reports into the experiment repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_REPOSITORY = "caperspeert-blip/moex-course-exam-alignment"
EXPECTED_COMMIT = "5accc1e300d4a6d94c7d1475e44c352b6bf5e54b"
DATASET_RELATIVE_PATH = "output/dataset/round26_formal_dataset_2026-10-02.json"
EXPECTED_RECORD_COUNT = 176


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write stable UTF-8 JSON / 寫入穩定格式 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_artifacts(source_repo: Path, output_dir: Path) -> dict[str, Any]:
    """Validate the pinned source and write Phase 0 artifacts."""
    source_repo = source_repo.resolve()
    output_dir = output_dir.resolve()
    head = run_git(source_repo, "rev-parse", "HEAD")
    origin = run_git(source_repo, "remote", "get-url", "origin")
    if head != EXPECTED_COMMIT:
        raise RuntimeError(f"Pinned commit mismatch: expected {EXPECTED_COMMIT}, got {head}")
    if EXPECTED_REPOSITORY not in origin:
        raise RuntimeError(f"Unexpected source repository remote: {origin}")

    dataset_path = source_repo / DATASET_RELATIVE_PATH
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    records = dataset.get("records")
    if not isinstance(records, list):
        raise RuntimeError("Dataset records is not a list")
    if len(records) != EXPECTED_RECORD_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_RECORD_COUNT} records, got {len(records)}")
    if dataset.get("formal_record_count") != EXPECTED_RECORD_COUNT:
        raise RuntimeError("Dataset formal_record_count does not match records length")
    if dataset.get("qdrant_ingest_performed") is not False:
        raise RuntimeError("Dataset indicates Qdrant ingest was performed")
    if dataset.get("validated_exam_subject_ids_generated") is not False:
        raise RuntimeError("Dataset indicates validated subject IDs were generated")

    formal_gate_counts: dict[str, int] = {}
    raw_hash_count = 0
    raw_path_count = 0
    for record in records:
        gate = str(record.get("formal_gate"))
        formal_gate_counts[gate] = formal_gate_counts.get(gate, 0) + 1
        raw_hash_count += bool(record.get("raw_sha256"))
        raw_path_count += bool(record.get("raw_artifact_path"))
    if formal_gate_counts != {"passed": EXPECTED_RECORD_COUNT}:
        raise RuntimeError(f"Unexpected formal_gate distribution: {formal_gate_counts}")
    if raw_hash_count != EXPECTED_RECORD_COUNT or raw_path_count != EXPECTED_RECORD_COUNT:
        raise RuntimeError("Formal records are missing raw provenance fields")

    generated_at = datetime.now(timezone.utc).isoformat()
    dataset_sha256 = sha256_file(dataset_path)
    input_manifest = {
        "manifest_version": "phase0-input-freeze-v1",
        "generated_at_utc": generated_at,
        "source": {
            "repository": EXPECTED_REPOSITORY,
            "remote": origin,
            "pinned_commit": EXPECTED_COMMIT,
            "local_clone": str(source_repo),
            "dataset_relative_path": DATASET_RELATIVE_PATH,
            "dataset_sha256": dataset_sha256,
            "dataset_version": dataset.get("dataset_version"),
            "scope": dataset.get("scope"),
        },
        "input_contract": {
            "formal_record_count": len(records),
            "formal_gate_distribution": formal_gate_counts,
            "raw_sha256_count": raw_hash_count,
            "raw_artifact_path_count": raw_path_count,
            "sampling": "none",
            "random_seed": None,
            "random_seed_status": "not_applicable_no_sampling",
        },
        "integrity": {
            "git_head_matches_pinned_commit": True,
            "remote_matches_expected_repository": True,
            "qdrant_ingest_performed": dataset.get("qdrant_ingest_performed"),
            "validated_exam_subject_ids_generated": dataset.get(
                "validated_exam_subject_ids_generated"
            ),
        },
    }
    exclusions = {
        "manifest_version": "phase0-exclusion-v1",
        "generated_at_utc": generated_at,
        "policy": "Only the pinned GitHub formal corpus is an experiment input.",
        "excluded_inputs": [
            {
                "name": "qdrant_existing_124_records",
                "count": 124,
                "condition": "existing local Qdrant points are not read as experiment input",
                "status": "excluded",
            },
            {
                "name": "uploaded_excel_course_corpus",
                "count": None,
                "condition": "uploaded Excel files are outside GitHub-only scope",
                "status": "excluded",
            },
            {
                "name": "qmd",
                "count": None,
                "condition": "qmd is not used for collection, retrieval, or evaluation",
                "status": "excluded",
            },
            {
                "name": "staged_records",
                "count": len(dataset.get("staged_school_ids", [])),
                "condition": "staged school IDs are not formal records",
                "status": "excluded",
            },
            {
                "name": "quarantine_records",
                "count": len(dataset.get("quarantine_school_ids", [])),
                "condition": "quarantine school IDs are not formal records",
                "status": "excluded",
            },
            {
                "name": "blocked_records",
                "count": len(dataset.get("blocked_school_ids", [])),
                "condition": "blocked school IDs are not formal records",
                "status": "excluded",
            },
        ],
        "included_input": {
            "name": "github_formal_dataset",
            "count": len(records),
            "dataset_sha256": dataset_sha256,
            "status": "included",
        },
    }
    report = {
        "report_version": "phase0-validation-v1",
        "generated_at_utc": generated_at,
        "status": "pass",
        "claims": {
            "input_freeze": "pass",
            "github_only_scope": "pass",
            "formal_record_count": len(records),
            "qdrant_124_records_included": False,
            "uploaded_excel_included": False,
            "qmd_used": False,
            "staged_included": False,
            "quarantine_included": False,
            "blocked_included": False,
            "human_adjudication_available": False,
            "machine_outputs_are_truth": False,
            "promotion_status": "blocked",
        },
        "known_limitations": [
            "This freezes a bounded GitHub corpus, not a national population.",
            "No human adjudication or validated exam alignment labels are present.",
            "The source dataset is evidence/provenance input, not alignment truth.",
        ],
    }
    write_json(output_dir / "input_manifest.json", input_manifest)
    write_json(output_dir / "exclusion_manifest.json", exclusions)
    write_json(output_dir / "validation_report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    """Parse CLI options / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/phase0_input_freeze_v1"),
    )
    return parser.parse_args()


def main() -> None:
    """Run the Phase 0 freeze / 執行 Phase 0 freeze。"""
    args = parse_args()
    report = build_artifacts(args.source_repo, args.output_dir)
    print(json.dumps(report["claims"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

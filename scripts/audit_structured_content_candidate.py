"""Audit the round26 structured-content candidate overlay.

This script reads the exact pinned file from a Git repository via ``git show``
and writes metadata-only audit artifacts. It does not promote the candidate,
rewrite the Phase 0 formal input, or ingest Qdrant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_COMMIT = "6454e22c2ad00087d62481171352738eb3396bad"
EXPECTED_PATH = "output/unified_dataset/round26_20261004/structured_content_600.json"
EXPECTED_SHA256 = "f0f6197c0eb33ceee03a9e2ff08d2e403f60e0609cdd263964a3542b57c9d2e0"
EXPECTED_RECORDS = 600


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument(
        "--commit", default=EXPECTED_COMMIT, help="Pinned source commit."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def git_show(source_repo: Path, commit: str, path: str) -> bytes:
    """Read one exact Git object / 讀取指定 commit 的檔案物件。"""
    result = subprocess.run(
        ["git", "-C", str(source_repo), "show", f"{commit}:{path}"],
        check=True,
        capture_output=True,
    )
    return result.stdout


def write_json(path: Path, payload: Any) -> None:
    """Write deterministic JSON / 寫入 UTF-8 JSON。"""
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write JSON Lines / 寫入 JSONL。"""
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def nonempty(value: Any) -> bool:
    """Return whether a value is meaningfully populated / 判斷是否有實質值。"""
    return value not in (None, "", [], {})


def main() -> int:
    """Build candidate manifest and audit queues / 建立 candidate 審計產物。"""
    args = parse_args()
    raw_bytes = git_show(args.source_repo, args.commit, EXPECTED_PATH)
    observed_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if observed_sha256 != EXPECTED_SHA256:
        raise SystemExit(
            f"candidate checksum mismatch: {observed_sha256} != {EXPECTED_SHA256}"
        )

    records = json.loads(raw_bytes)
    if not isinstance(records, list) or len(records) != EXPECTED_RECORDS:
        raise SystemExit(f"unexpected candidate record count: {len(records)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    content_status = Counter(str(r.get("content_status")) for r in records)
    hash_status = Counter(str(r.get("hash_status")) for r in records)
    provenance_status = Counter(
        "null" if r.get("provenance_status") is None else str(r["provenance_status"])
        for r in records
    )
    source_status = Counter(str(r.get("source_record_status")) for r in records)

    hash_mismatch = [
        {
            "structured_id": r.get("structured_id"),
            "school_id": r.get("school_id"),
            "course_title": r.get("course_title"),
            "raw_artifact_path": r.get("raw_artifact_path"),
            "raw_sha256": r.get("raw_sha256"),
            "hash_status": r.get("hash_status"),
            "review_status": "review_required",
            "release_status": "blocked",
        }
        for r in records
        if r.get("hash_status") == "mismatch"
    ]
    provenance_gaps = []
    for record in records:
        reasons = []
        if not nonempty(record.get("official_url")):
            reasons.append("missing_official_url")
        if record.get("provenance_status") is None:
            reasons.append("provenance_status_null")
        elif record.get("provenance_status") != "verified":
            reasons.append("provenance_not_verified")
        if record.get("hash_status") == "mismatch":
            reasons.append("hash_mismatch")
        if reasons:
            provenance_gaps.append(
                {
                    "structured_id": record.get("structured_id"),
                    "school_id": record.get("school_id"),
                    "course_title": record.get("course_title"),
                    "official_url_present": nonempty(record.get("official_url")),
                    "provenance_status": record.get("provenance_status"),
                    "source_record_status": record.get("source_record_status"),
                    "identity_status": "unresolved" if record.get("provenance_status") else "unknown",
                    "gap_reason_codes": reasons,
                    "review_status": "review_required",
                    "release_status": "blocked",
                }
            )

    field_presence = {}
    for field in sorted({key for record in records for key in record}):
        field_presence[field] = {
            "nonempty_count": sum(nonempty(r.get(field)) for r in records),
            "empty_count": sum(not nonempty(r.get(field)) for r in records),
        }

    manifest = {
        "candidate_name": "structured_content_600_candidate_v1",
        "source_repository": "caperspeert-blip/moex-course-exam-alignment",
        "source_commit": args.commit,
        "source_path": EXPECTED_PATH,
        "source_file_sha256": observed_sha256,
        "record_count": len(records),
        "scope_status": "candidate_overlay",
        "promotion_status": "blocked",
        "qdrant_ingest": False,
        "formal_exam_alignment": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "content_lanes": {
            "content_bearing": content_status.get("content_bearing", 0),
            "partial": content_status.get("partial", 0),
            "zero_content_chars": sum(r.get("content_chars") == 0 for r in records),
        },
        "integrity_lanes": {
            "hash_verified": hash_status.get("verified", 0),
            "hash_mismatch": hash_status.get("mismatch", 0),
            "official_url_missing": sum(not nonempty(r.get("official_url")) for r in records),
            "provenance_status_null": provenance_status.get("null", 0),
        },
        "method_policy": {
            "machine_output_is_truth": False,
            "human_adjudication_available": False,
            "content_bearing_is_not_formal": True,
            "candidate_does_not_replace_176_formal_scope": True,
        },
    }
    report = {
        "report_version": "structured-content-candidate-audit-v1",
        "candidate_name": manifest["candidate_name"],
        "record_count": len(records),
        "field_count": len(field_presence),
        "content_status_counts": dict(content_status),
        "hash_status_counts": dict(hash_status),
        "provenance_status_counts": dict(provenance_status),
        "source_record_status_counts": dict(source_status),
        "hash_mismatch_count": len(hash_mismatch),
        "provenance_gap_count": len(provenance_gaps),
        "official_url_missing_count": sum(not nonempty(r.get("official_url")) for r in records),
        "unique_structured_id_count": len({r.get("structured_id") for r in records}),
        "unique_raw_sha256_count": len({r.get("raw_sha256") for r in records}),
        "field_presence": field_presence,
        "release_decision": "blocked_pending_provenance_and_identity_review",
    }

    write_json(args.output_dir / "candidate_input_manifest.json", manifest)
    write_json(args.output_dir / "candidate_status_report.json", report)
    write_jsonl(args.output_dir / "hash_mismatch_quarantine.jsonl", hash_mismatch)
    write_jsonl(args.output_dir / "provenance_gap_review_queue.jsonl", provenance_gaps)
    print(json.dumps({
        "status": "pass",
        "candidate": manifest["candidate_name"],
        "records": len(records),
        "content_bearing": content_status.get("content_bearing", 0),
        "partial": content_status.get("partial", 0),
        "hash_mismatch": len(hash_mismatch),
        "provenance_gaps": len(provenance_gaps),
        "promotion": "blocked",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

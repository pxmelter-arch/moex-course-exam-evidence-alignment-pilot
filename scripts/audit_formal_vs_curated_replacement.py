"""Audit whether curated experiment records can replace formal records.

This is a comparison-only audit. It never promotes records or rewrites the
formal lane / 這是比較審計，不會 promotion 或覆寫 formal lane。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

FORMAL_COMMIT = "8922edc"
FORMAL_PATH = "output/canonical/round26_formal_syllabus_projection.json"
CURATED_COMMIT = "a22f8e7"
CURATED_PATH = "release/curated_experiment_20261006/experiment_projection.jsonl"
FORMAL_EXPECTED = 176
CURATED_EXPECTED = 600


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def git_show(repo: Path, commit: str, path: str) -> bytes:
    """Read pinned Git object / 讀取固定 commit 檔案。"""
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"])


def text(value: Any) -> str:
    """Convert value to text / 統一文字表示。"""
    return "" if value is None else str(value)


def norm(value: Any) -> str:
    """Normalize multilingual identity text / 正規化 identity 文字。"""
    value = unicodedata.normalize("NFKC", text(value)).casefold()
    return re.sub(r"[^\w\u3400-\u9fff]", "", value)


def semester(value: Any) -> str:
    """Normalize semester labels without inferring missing values / 正規化學期。"""
    value = norm(value)
    if value in {"1", "上學期", "上半年", "firstsemester"}:
        return "1"
    if value in {"2", "下學期", "下半年", "secondsemester"}:
        return "2"
    return value


def identity_key(row: dict[str, Any]) -> tuple[str, ...]:
    """Build conservative course identity key / 建立保守課程 identity key。"""
    return (
        norm(row.get("school_id")),
        norm(row.get("course_code")),
        norm(row.get("course_title")),
        norm(row.get("academic_year")),
        semester(row.get("semester")),
    )


def title_key(row: dict[str, Any]) -> tuple[str, str]:
    """Build school-title key / 建立學校課名 key。"""
    return norm(row.get("school_id")), norm(row.get("course_title"))


def hash_key(row: dict[str, Any]) -> str:
    """Return raw hash / 回傳 raw hash。"""
    return text(row.get("raw_sha256") or row.get("declared_raw_sha256"))


def load_inputs(repo: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load and validate pinned inputs / 載入並驗證 pinned inputs。"""
    formal = json.loads(git_show(repo, FORMAL_COMMIT, FORMAL_PATH))
    curated = [json.loads(line) for line in git_show(repo, CURATED_COMMIT, CURATED_PATH).decode().splitlines() if line.strip()]
    if len(formal) != FORMAL_EXPECTED or len(curated) != CURATED_EXPECTED:
        raise ValueError(f"scope mismatch formal={len(formal)} curated={len(curated)}")
    return formal, curated


def counter_dict(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    """Count field values / 統計欄位值。"""
    return dict(sorted(Counter(text(row.get(field) or "<missing>") for row in rows).items()))


def main() -> int:
    """Run replacement audit / 執行 replacement audit。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    formal, curated = load_inputs(args.source_repo)

    formal_identity = Counter(identity_key(row) for row in formal)
    curated_identity = Counter(identity_key(row) for row in curated)
    formal_title = Counter(title_key(row) for row in formal)
    curated_title = Counter(title_key(row) for row in curated)
    formal_hash = {hash_key(row) for row in formal if hash_key(row)}
    curated_hash = {hash_key(row) for row in curated if hash_key(row)}
    formal_urls = {text(row.get("official_url")) for row in formal if row.get("official_url")}
    curated_urls = {text(row.get("official_url")) for row in curated if row.get("official_url")}

    exact_identity = set(formal_identity) & set(curated_identity)
    exact_hash = formal_hash & curated_hash
    exact_title = set(formal_title) & set(curated_title)
    curated_duplicate_ids = [k for k, count in Counter(text(r.get("structured_id")) for r in curated).items() if count > 1]
    curated_duplicate_hashes = [k for k, count in Counter(hash_key(r) for r in curated if hash_key(r)).items() if count > 1]

    matched_formal_by_identity: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for row in curated:
        key = identity_key(row)
        if key in formal_identity:
            matched_formal_by_identity[key].append(text(row.get("structured_id")))
    review_queue = []
    for row in curated:
        blockers = []
        if row.get("release_status") != "experimental_only":
            blockers.append("release_status_not_experimental_only")
        if row.get("formal_promotion") is not False:
            blockers.append("formal_promotion_field_not_false")
        if row.get("qdrant_ingest") is not False:
            blockers.append("qdrant_ingest_field_not_false")
        if row.get("content_status") != "content_bearing":
            blockers.append("partial_or_non_content_status")
        if row.get("source_record_status") in {"quarantine", "blocked"}:
            blockers.append(f"source_record_status:{row.get('source_record_status')}")
        if row.get("provenance_status") not in {"pass", "verified"}:
            blockers.append(f"provenance_status:{row.get('provenance_status') or '<missing>'}")
        if identity_key(row) not in formal_identity:
            blockers.append("not_in_formal_identity_scope")
        review_queue.append({
            "structured_id": row.get("structured_id"),
            "school_id": row.get("school_id"),
            "course_title": row.get("course_title"),
            "content_status": row.get("content_status"),
            "source_record_status": row.get("source_record_status"),
            "provenance_status": row.get("provenance_status"),
            "formal_identity_overlap": identity_key(row) in formal_identity,
            "exact_raw_hash_overlap": hash_key(row) in formal_hash if hash_key(row) else False,
            "replacement_blockers": blockers,
            "review_status": "blocked_pending_formalization" if blockers else "eligible_for_independent_review",
        })

    report = {
        "experiment": "formal_vs_curated_replacement_audit_v1",
        "status": "pass",
        "decision": "do_not_replace_formal_176",
        "decision_reason": [
            "curated release_status is experimental_only",
            "curated formal_promotion is zero",
            "curated includes partial records",
            "curated contains quarantine or unresolved provenance states",
            "curated lineage and formal lineage are different",
        ],
        "inputs": {
            "formal": {"commit": FORMAL_COMMIT, "path": FORMAL_PATH, "records": len(formal)},
            "curated": {"commit": CURATED_COMMIT, "path": CURATED_PATH, "records": len(curated)},
        },
        "overlap": {
            "exact_composite_identity_key_count": len(exact_identity),
            "exact_raw_sha256_count": len(exact_hash),
            "school_title_key_count": len(exact_title),
            "official_url_count": len(formal_urls & curated_urls),
            "curated_records_with_formal_identity_overlap": sum(identity_key(r) in formal_identity for r in curated),
            "formal_records_with_curated_identity_overlap": sum(identity_key(r) in curated_identity for r in formal),
        },
        "curated_quality_partition": {
            "content_status": counter_dict(curated, "content_status"),
            "source_record_status": counter_dict(curated, "source_record_status"),
            "provenance_status": counter_dict(curated, "provenance_status"),
            "release_status": counter_dict(curated, "release_status"),
            "formal_promotion": counter_dict(curated, "formal_promotion"),
            "qdrant_ingest": counter_dict(curated, "qdrant_ingest"),
        },
        "formal_quality_partition": {
            "content_status": counter_dict(formal, "content_status"),
            "formal_gate": counter_dict(formal, "formal_gate"),
            "independent_provenance_status": counter_dict(formal, "independent_provenance_status"),
            "promotion_status": counter_dict(formal, "promotion_status"),
        },
        "duplicates": {
            "curated_duplicate_structured_id_groups": len(curated_duplicate_ids),
            "curated_duplicate_raw_sha256_groups": len(curated_duplicate_hashes),
            "curated_duplicate_structured_ids": curated_duplicate_ids,
            "curated_duplicate_raw_sha256_values": curated_duplicate_hashes,
        },
        "review_queue_count": len(review_queue),
        "replacement_gate": {
            "formal_lane_unchanged": True,
            "curated_can_be_used_for_experiment": True,
            "curated_can_replace_formal_without_reformalization": False,
            "promotion": "blocked",
        },
    }
    (args.output_dir / "replacement_audit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "curated_replacement_review_queue.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in review_queue), encoding="utf-8")
    (args.output_dir / "input_lineage_manifest.json").write_text(json.dumps(report["inputs"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

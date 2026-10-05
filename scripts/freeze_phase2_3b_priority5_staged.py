"""Freeze the 373-record Priority-5 staged input lane.

The upstream validation aggregate is materialized from four source-specific
artifacts. This script selects records using explicit source rules, preserves
native status/provenance, audits overlap with the 520-record primary artifact,
and emits a reproducible manifest. It does not promote any record.
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

COMMIT = "1f2a2e635d61e01b5788a3c8c5b66adeb5c7e9db"
PRIMARY_PATH = "output/unified_dataset/round26_20261004/structured_content_600.json"
SCH022_PATH = "output/acquisition/round26_20261005_formal_retry5/structured.jsonl"
SCH026_PATH = "output/acquisition/sch026_pu_114_bounded_acquisition.json"
SCH006_PATH = "output/fresh/live_20261005/SCH006_live_closeout.json"
SCH014_PATH = "output/crawler_rebuild_2026-10-04/course_acquisition/sch014_ntu_1141_candidate_review.json"
EXPECTED = {"SCH022": 17, "SCH026": 89, "SCH006": 6, "SCH014": 261}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def git_show(repo: Path, path: str) -> Any:
    """Read pinned JSON/JSONL / 讀取固定 commit 的資料。"""
    text = subprocess.check_output(["git", "-C", str(repo), "show", f"{COMMIT}:{path}"], text=True)
    if path.endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def normalize(value: Any) -> str:
    """Normalize identity text / 正規化 identity 文字。"""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^\w\u3400-\u9fff]", "", text)


def sha(value: Any) -> str | None:
    """Return normalized SHA if present / 回傳 SHA。"""
    value = str(value or "").strip()
    return value.lower() if value else None


def url(value: Any) -> str | None:
    """Normalize URL-like identity / 正規化 URL identity。"""
    value = str(value or "").strip()
    return value or None


def composite(record: dict[str, Any]) -> str:
    """Build conservative course identity key / 建立保守課程 identity key。"""
    return "|".join(normalize(record.get(key)) for key in ("school_id", "course_title", "academic_year", "semester", "course_code"))


def first_text(record: dict[str, Any]) -> str:
    """Collect available content fields without imputation / 收集現有內容欄位。"""
    fields = ("content_text", "row_text", "course_description", "objectives", "outline", "assessment", "textbook", "reference", "prerequisite")
    return " ".join(str(record.get(field) or "") for field in fields if record.get(field))


def make_row(source_id: str, record: dict[str, Any]) -> dict[str, Any]:
    """Map source-native row to unified staged manifest / 映射 staged manifest。"""
    raw_hash = sha(record.get("raw_sha256") or record.get("detail_sha256") or record.get("word_sha256"))
    raw_path = record.get("raw_artifact_path") or record.get("detail_raw_artifact") or record.get("word_raw_artifact")
    source_native_id = record.get("structured_id") or record.get("candidate_id") or record.get("seqno")
    if source_id == "SCH026":
        source_native_id = source_native_id or record.get("official_detail_url") or record.get("course_title")
    stable = f"{source_id}|{source_native_id}|{raw_hash or ''}|{record.get('official_detail_url') or record.get('official_url') or ''}"
    record_id = f"P5-{source_id}-{hashlib.sha256(stable.encode()).hexdigest()[:20]}"
    native_status = record.get("record_state") or record.get("acquisition_status")
    quarantine = native_status in {"quarantine", "quarantine_candidate_provenance_pending"}
    content_status = record.get("content_status")
    if source_id == "SCH026":
        content_status = "content_bearing_detail" if record.get("syllabus_content") else "detail_artifact"
    elif source_id == "SCH014":
        content_status = "content_bearing_signal"
    elif source_id == "SCH006":
        content_status = record.get("content_status") or "content_bearing"
    return {
        "record_id": record_id,
        "source_id": source_id,
        "source_native_id": source_native_id,
        "school_id": record.get("school_id"),
        "course_title": record.get("course_title"),
        "academic_year": record.get("academic_year"),
        "semester": record.get("semester"),
        "course_code": record.get("course_code"),
        "department": record.get("department") or record.get("department_name"),
        "content_status": content_status,
        "raw_sha256": raw_hash,
        "raw_artifact_path": raw_path,
        "source_record_status": "staged_priority5",
        "source_native_status": native_status,
        "quarantine": quarantine,
        "provenance_status": "declared_hash_and_artifact_path" if raw_hash and raw_path else "provenance_incomplete",
        "identity_status": "deterministic_source_identity",
        "deduplication_decision": "pending_cross_lane_identity_audit",
        "official_url": url(record.get("official_detail_url") or record.get("official_url")),
        "content_chars": record.get("content_chars") or record.get("detail_content_chars") or record.get("word_content_chars"),
        "content_text": first_text(record),
        "source_evidence": {"source_commit": COMMIT},
    }


def main() -> int:
    """Build freeze manifest and audit / 建立 freeze manifest 與 audit。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    primary = git_show(args.source_repo, PRIMARY_PATH)
    retry5 = git_show(args.source_repo, SCH022_PATH)
    sch026 = git_show(args.source_repo, SCH026_PATH)["records"]
    sch006 = git_show(args.source_repo, SCH006_PATH)["records"]
    sch014 = git_show(args.source_repo, SCH014_PATH)["records"]
    selected = {
        "SCH022": [r for r in retry5 if r.get("school_id") == "SCH022" and r.get("content_status") == "content_bearing"],
        "SCH026": sch026,
        "SCH006": [r for r in sch006 if r.get("content_status") == "content_bearing"],
        "SCH014": [r for r in sch014 if r.get("content_signal") is True],
    }
    counts = {sid: len(rows) for sid, rows in selected.items()}
    if counts != EXPECTED:
        raise SystemExit(f"Priority-5 selection mismatch: {counts} != {EXPECTED}")
    staged = [make_row(sid, row) for sid, rows in selected.items() for row in rows]
    if len(staged) != 373 or len({r["record_id"] for r in staged}) != 373:
        raise SystemExit("staged record identity count mismatch")
    primary_rows = [r for r in primary if r.get("content_status") == "content_bearing"]
    primary_hashes = {sha(r.get("raw_sha256")) for r in primary_rows if sha(r.get("raw_sha256"))}
    primary_urls = {url(r.get("official_url")) for r in primary_rows if url(r.get("official_url"))}
    primary_composites = {composite(r) for r in primary_rows}
    staged_hashes = Counter(r["raw_sha256"] for r in staged if r["raw_sha256"])
    staged_urls = Counter(r["official_url"] for r in staged if r["official_url"])
    staged_composites = Counter(composite(r) for r in staged)
    overlap_rows = []
    duplicate_rows = []
    for row in staged:
        matches = []
        if row["raw_sha256"] and row["raw_sha256"] in primary_hashes:
            matches.append("raw_sha256")
        if row["official_url"] and row["official_url"] in primary_urls:
            matches.append("official_url")
        if composite(row) in primary_composites:
            matches.append("school_title_term_code")
        if matches:
            row["deduplication_decision"] = "overlap_primary_review_required"
            overlap_rows.append({"record_id": row["record_id"], "match_keys": matches})
        elif (row["raw_sha256"] and staged_hashes[row["raw_sha256"]] > 1) or (row["official_url"] and staged_urls[row["official_url"]] > 1) or staged_composites[composite(row)] > 1:
            row["deduplication_decision"] = "duplicate_within_staged_review_required"
            duplicate_rows.append({"record_id": row["record_id"], "duplicate_keys": [k for k, v in (("raw_sha256", row["raw_sha256"] and staged_hashes[row["raw_sha256"]] > 1), ("official_url", row["official_url"] and staged_urls[row["official_url"]] > 1), ("school_title_term_code", staged_composites[composite(row)] > 1)) if v]})
        else:
            row["deduplication_decision"] = "unique_against_primary_and_staged_keys"
    quarantine = [r for r in staged if r["quarantine"]]
    report = {
        "experiment": "phase2_3b_priority5_staged_input_freeze_v1",
        "status": "pass",
        "source_commit": COMMIT,
        "source_paths": {"primary": PRIMARY_PATH, "SCH022": SCH022_PATH, "SCH026": SCH026_PATH, "SCH006": SCH006_PATH, "SCH014": SCH014_PATH},
        "selection_rules": {"SCH022": "content_status=content_bearing", "SCH026": "all official detail records", "SCH006": "content_status=content_bearing", "SCH014": "content_signal=true"},
        "source_counts": counts,
        "staged_record_count": len(staged),
        "primary_content_bearing_count": len(primary_rows),
        "overlap_with_primary_count": len(overlap_rows),
        "duplicate_within_staged_count": len(duplicate_rows),
        "quarantine_count": len(quarantine),
        "provenance_incomplete_count": sum(r["provenance_status"] != "declared_hash_and_artifact_path" for r in staged),
        "formal_promotions": 0,
        "release_partition": "staged_experiment_only",
        "retrieval_gate": "pass_for_373_staged_diagnostic_with_status_preservation",
        "promotion_status": "blocked",
    }
    manifest_path = args.output_dir / "priority5_staged_manifest.jsonl"
    manifest_path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in staged), encoding="utf-8")
    (args.output_dir / "overlap_audit.json").write_text(json.dumps(overlap_rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "duplicate_audit.json").write_text(json.dumps(duplicate_rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "freeze_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

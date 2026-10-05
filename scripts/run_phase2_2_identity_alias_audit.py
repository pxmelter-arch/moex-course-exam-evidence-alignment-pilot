"""Run Phase 2.2 candidate identity and alias audit.

This is a machine-audit layer. It creates deterministic outline identities,
keeps duplicate subject variants separate, generates review-required alias
candidates, and applies department-aware scoring only as an advisory signal.
It never promotes an alias to truth or modifies the formal/staged datasets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

FORMAL_COMMIT = "1f2a2e635d61e01b5788a3c8c5b66adeb5c7e9db"
FORMAL_PATH = "output/dataset/round26_formal_dataset_2026-10-02.json"
OUTLINE_COMMIT = "4cb1b5a7155a052450354cdff2e7e00a66728b89"
OUTLINE_PATH = "data/raw/exam_outlines/exam_outline_catalog/output/exam_outline_catalog.json"
EXPECTED_FORMAL = 176
EXPECTED_OUTLINES = 542

ADMIN_TERMS = ("行政", "法律", "政治", "經濟", "財政", "會計", "人事", "社會", "教育", "公共", "地政", "外交", "新聞", "文化", "勞工", "金融")
TECH_TERMS = ("資工", "資訊", "電機", "電子", "機械", "土木", "化學", "生物", "醫", "環境", "材料", "建築", "工程", "農", "食品", "物理", "數學", "統計", "地質")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--retrieval-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def git_show(repo: Path, commit: str, path: str) -> bytes:
    """Read a pinned Git object / 讀取固定 commit 檔案。"""
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"])


def normalize_text(value: Any) -> str:
    """Normalize text for identity only / 僅供 identity 使用的文字正規化。"""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^\w\u3400-\u9fff]", "", text)


def outline_record_id(record: dict[str, Any]) -> str:
    """Create deterministic content/provenance-aware ID / 建立 deterministic ID。"""
    payload = {
        "subject_name": record.get("subject_name"),
        "type": record.get("type"),
        "applicable_exams": record.get("applicable_exams"),
        "core_knowledge": record.get("core_knowledge"),
        "outline": record.get("outline"),
        "remarks": record.get("remarks"),
        "source": record.get("source"),
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return f"OUT-{digest[:20]}"


def title_similarity(left: str, right: str) -> float:
    """Calculate deterministic character similarity / 計算字元相似度。"""
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def inferred_department_family(department: str) -> str:
    """Infer an advisory department family / 推斷 advisory department family。"""
    if any(term in department for term in TECH_TERMS):
        return "technical_candidate"
    if any(term in department for term in ADMIN_TERMS):
        return "administrative_candidate"
    return "unknown"


def candidate_type_family(types: Any) -> set[str]:
    """Normalize catalog type values / 正規化命題大綱 type。"""
    values = types if isinstance(types, list) else [types]
    result = set()
    for value in values:
        text = str(value)
        if "技術" in text:
            result.add("technical_candidate")
        if "行政" in text:
            result.add("administrative_candidate")
    return result


def main() -> int:
    """Run identity/alias audit and write review artifacts / 執行 audit。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    formal = json.loads(git_show(args.source_repo, FORMAL_COMMIT, FORMAL_PATH))["records"]
    outlines = json.loads(git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH))
    if len(formal) != EXPECTED_FORMAL or len(outlines) != EXPECTED_OUTLINES:
        raise SystemExit("pinned input record count mismatch")

    for record in outlines:
        record["outline_record_id"] = outline_record_id(record)
        record["normalized_subject_name"] = normalize_text(record.get("subject_name"))
    assert len({r["outline_record_id"] for r in outlines}) == len(outlines)

    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in outlines:
        groups[record["normalized_subject_name"]].append(record)
    duplicate_groups = []
    for normalized_name, records in sorted(groups.items()):
        if len(records) < 2:
            continue
        duplicate_groups.append({
            "normalized_subject_name": normalized_name,
            "subject_name_values": sorted({str(r.get("subject_name") or "") for r in records}),
            "variant_count": len(records),
            "variants": [
                {
                    "outline_record_id": r["outline_record_id"],
                    "subject_name": r.get("subject_name"),
                    "type": r.get("type"),
                    "applicable_exams": r.get("applicable_exams", []),
                    "source": r.get("source", []),
                    "content_signature": hashlib.sha256(
                        json.dumps({"core_knowledge": r.get("core_knowledge"), "outline": r.get("outline")}, ensure_ascii=False, sort_keys=True).encode()
                    ).hexdigest()[:16],
                }
                for r in records
            ],
            "resolution_status": "review_required",
        })

    retrieval_rows = [json.loads(line) for line in args.retrieval_results.read_text(encoding="utf-8").splitlines() if line]
    if len(retrieval_rows) != EXPECTED_FORMAL:
        raise SystemExit("retrieval result count mismatch")
    outline_by_id = {r["outline_record_id"]: r for r in outlines}
    duplicate_ids = {variant["outline_record_id"] for group in duplicate_groups for variant in group["variants"]}

    alias_rows = []
    review_rows = []
    status_counts = defaultdict(int)
    for row in retrieval_rows:
        course_title = row.get("course_title", "")
        department = row.get("department_name", "") or ""
        department_family = inferred_department_family(department)
        candidates = row["methods"]["tfidf"]
        scored = []
        for candidate in candidates:
            outline = outline_by_id[candidate["outline_record_id"]]
            exact_title = normalize_text(course_title) == normalize_text(outline.get("subject_name"))
            compatibility = department_family in candidate_type_family(outline.get("type"))
            advisory_score = float(candidate["score"]) + (0.05 if compatibility else 0.0) + (0.02 if exact_title else 0.0)
            scored.append({
                **candidate,
                "title_similarity": round(title_similarity(course_title, outline.get("subject_name", "")), 6),
                "title_exact": exact_title,
                "department_family": department_family,
                "department_type_compatibility": compatibility,
                "department_adjustment": 0.05 if compatibility else 0.0,
                "advisory_score": round(advisory_score, 8),
            })
        scored.sort(key=lambda item: (-item["advisory_score"], item["outline_record_id"]))
        top = scored[0] if scored else None
        second = scored[1] if len(scored) > 1 else None
        exact_matches = [candidate for candidate in scored if candidate["title_exact"]]
        top_margin = round((top["advisory_score"] - second["advisory_score"]) if second else top["advisory_score"], 8) if top else 0.0
        if len(exact_matches) == 1 and exact_matches[0]["outline_record_id"] not in duplicate_ids:
            status = "exact"
            reason = "unique_exact_title_match"
        elif exact_matches or (top and top["title_similarity"] >= 0.7 and top_margin < 0.05) or (top and top["outline_record_id"] in duplicate_ids):
            status = "ambiguous"
            reason = "duplicate_variant_or_close_candidate_margin"
        else:
            status = "weak"
            reason = "no_unique_exact_or_strong_alias_evidence"
        status_counts[status] += 1
        review_rows.append({
            "course_record_id": row.get("course_record_id"),
            "school_id": row.get("school_id"),
            "course_title": course_title,
            "department_name": department,
            "department_family": department_family,
            "candidate_status": status,
            "status_reason": reason,
            "top_margin": top_margin,
            "candidates": scored,
            "human_review_status": "not_human_adjudicated",
            "promotion_status": "blocked",
            "source_evidence_required": True,
        })
        if top and normalize_text(course_title) != normalize_text(top["subject_name"]):
            alias_rows.append({
                "course_record_id": row.get("course_record_id"),
                "course_title_raw": course_title,
                "course_title_normalized": normalize_text(course_title),
                "candidate_subject_name": top["subject_name"],
                "candidate_outline_record_id": top["outline_record_id"],
                "title_similarity": top["title_similarity"],
                "department_adjusted_score": top["advisory_score"],
                "alias_status": "machine_candidate_review_required",
                "human_review_status": "not_human_adjudicated",
                "source": top.get("source", []),
            })

    identity_manifest = [
        {
            "outline_record_id": record["outline_record_id"],
            "subject_name": record.get("subject_name"),
            "normalized_subject_name": record["normalized_subject_name"],
            "type": record.get("type"),
            "applicable_exams": record.get("applicable_exams", []),
            "source": record.get("source", []),
            "identity_status": "duplicate_name_review_required" if record["outline_record_id"] in duplicate_ids else "deterministic_candidate_id",
        }
        for record in outlines
    ]
    report = {
        "experiment": "phase2_2_candidate_identity_alias_audit_v1",
        "status": "pass",
        "formal_record_count": len(formal),
        "outline_record_count": len(outlines),
        "outline_record_id_count": len(identity_manifest),
        "duplicate_subject_name_group_count": len(duplicate_groups),
        "duplicate_subject_name_group_expected": 36,
        "candidate_review_counts": dict(sorted(status_counts.items())),
        "alias_candidate_count": len(alias_rows),
        "department_scoring": "advisory_only",
        "source_page_evidence_preserved": True,
        "human_adjudication": "not_available",
        "formal_alignment": "not_started",
        "priority5_content_lane": "not_included_in_this_phase",
        "promotion_status": "blocked",
    }
    (args.output_dir / "outline_identity_manifest.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in identity_manifest), encoding="utf-8")
    (args.output_dir / "duplicate_subject_groups.json").write_text(json.dumps(duplicate_groups, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "course_title_alias_candidates.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in alias_rows), encoding="utf-8")
    (args.output_dir / "candidate_review_queue.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in review_rows), encoding="utf-8")
    (args.output_dir / "audit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

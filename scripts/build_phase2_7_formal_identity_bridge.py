"""Build a conservative identity bridge for the current formal 176 lane.

Exact names are added deterministically to the candidate pool; fuzzy aliases
remain review-required and never become truth or promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORMAL_COMMIT = "8922edc"
FORMAL_PATH = "output/canonical/round26_formal_syllabus_projection.json"
OUTLINE_COMMIT = "4cb1b5a7155a052450354cdff2e7e00a66728b89"
OUTLINE_PATH = "data/raw/exam_outlines/exam_outline_catalog/output/exam_outline_catalog.json"
EXPECTED_FORMAL = 176
EXPECTED_OUTLINES = 542
RESULTS_PATH = "experiments/phase2_6_formal_chunk_dense_hybrid_evidence_v1/course_chunk_hybrid_results.jsonl"


def norm(value: Any) -> str:
    """Normalize identity text / 正規化 identity text。"""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^\w\u3400-\u9fff]", "", text)


def git_json(repo: Path, commit: str, path: str) -> Any:
    """Read pinned JSON / 讀取 pinned JSON。"""
    return json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"]))


def outline_id(row: dict[str, Any]) -> str:
    """Create deterministic outline ID / 建立 deterministic outline ID。"""
    payload = {key: row.get(key) for key in ("subject_name", "type", "applicable_exams", "core_knowledge", "outline", "remarks", "source")}
    return "OUT-" + hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]


def similarity(left: str, right: str) -> float:
    """Compute advisory title similarity / 計算 advisory title similarity。"""
    return SequenceMatcher(None, norm(left), norm(right)).ratio()


def source_evidence(row: dict[str, Any]) -> dict[str, Any]:
    """Retain outline source evidence / 保留 outline source evidence。"""
    return {"source": row.get("source", []), "applicable_exams": row.get("applicable_exams", []), "type": row.get("type")}


def main() -> int:
    """Build identity bridge artifacts / 建立 identity bridge artifacts。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    formal = git_json(args.source_repo, FORMAL_COMMIT, FORMAL_PATH)
    outlines = git_json(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH)
    result_rows = [json.loads(line) for line in (ROOT / RESULTS_PATH).read_text(encoding="utf-8").splitlines()]
    if len(formal) != EXPECTED_FORMAL or len(outlines) != EXPECTED_OUTLINES or len(result_rows) != EXPECTED_FORMAL:
        raise SystemExit("identity bridge scope mismatch")
    for row in outlines:
        row["outline_record_id"] = outline_id(row)
        row["normalized_subject_name"] = norm(row.get("subject_name"))
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in outlines:
        by_name.setdefault(row["normalized_subject_name"], []).append(row)
    duplicate_names = {name for name, rows in by_name.items() if name and len(rows) > 1}
    bridge_rows = []
    review_rows = []
    counts = Counter()
    gate_recovered = []
    for record, current in zip(formal, result_rows):
        title = str(record.get("course_title") or "")
        normalized_title = norm(title)
        exact_rows = by_name.get(normalized_title, [])
        current_ids = set(current.get("course_candidate_outline_record_ids", []))
        exact_ids = {row["outline_record_id"] for row in exact_rows}
        if exact_ids - current_ids:
            gate_recovered.append({"record_id": current["record_id"], "course_title": title, "recovered_outline_record_ids": sorted(exact_ids - current_ids)})
        fuzzy = []
        for outline in outlines:
            score = similarity(title, outline.get("subject_name", ""))
            if score > 0:
                fuzzy.append({
                    "outline_record_id": outline["outline_record_id"],
                    "subject_name": outline.get("subject_name"),
                    "title_similarity": round(score, 6),
                    "source_evidence": source_evidence(outline),
                })
        fuzzy.sort(key=lambda row: (-row["title_similarity"], row["outline_record_id"]))
        expanded = []
        seen = set()
        for outline_id_value in list(current_ids) + list(exact_ids) + [row["outline_record_id"] for row in fuzzy[:5]]:
            if outline_id_value not in seen:
                seen.add(outline_id_value)
                expanded.append(outline_id_value)
        exact_status = "exact_unique" if len(exact_rows) == 1 else ("exact_duplicate_name" if len(exact_rows) > 1 else "no_exact_title")
        if exact_status == "exact_unique":
            status = "exact"
            reason = "unique_exact_normalized_subject"
        elif exact_status == "exact_duplicate_name":
            status = "ambiguous"
            reason = "exact_name_has_multiple_outline_variants"
        elif fuzzy and fuzzy[0]["title_similarity"] >= 0.70:
            status = "ambiguous"
            reason = "strong_machine_alias_requires_review"
        else:
            status = "weak"
            reason = "no_unique_exact_or_strong_alias"
        counts[status] += 1
        row = {
            "record_id": current["record_id"],
            "course_title": title,
            "identity_status": status,
            "identity_reason": reason,
            "exact_title_match_count": len(exact_rows),
            "existing_course_candidate_count": len(current_ids),
            "expanded_candidate_count": len(expanded),
            "expanded_candidate_outline_record_ids": expanded,
            "top_alias_candidates": fuzzy[:5],
            "human_review_status": "not_human_adjudicated",
            "promotion_status": "blocked",
        }
        bridge_rows.append(row)
        review_rows.append({**row, "review_queue": status != "exact" or len(exact_rows) > 1})
    report = {
        "experiment": "phase2_7_formal_identity_bridge_audit_v1",
        "formal_records": len(formal),
        "outline_records": len(outlines),
        "duplicate_subject_name_groups": len(duplicate_names),
        "identity_status_counts": dict(counts),
        "course_gate_exact_recovered": len(gate_recovered),
        "course_gate_exact_recovered_records": gate_recovered,
        "alias_policy": "machine_candidate_review_required",
        "human_adjudication": "not_available",
        "formal_alignment": "not_started",
        "promotion_status": "blocked",
        "qdrant_ingest": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "identity_bridge_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "identity_bridge_candidates.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in bridge_rows), encoding="utf-8")
    (args.output_dir / "identity_review_queue.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in review_rows if row["review_queue"]), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

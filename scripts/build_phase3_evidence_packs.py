"""Build Phase 3 independent evidence packs and promotion blockers.

This is machine-generated review material only. It never infers human truth or
promotes candidates / 僅產生 review material，不自動 promotion。
"""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORMAL_COMMIT = "8922edc"
FORMAL_PATH = "output/canonical/round26_formal_syllabus_projection.json"
OUTLINE_COMMIT = "4cb1b5a7155a052450354cdff2e7e00a66728b89"
OUTLINE_PATH = "data/raw/exam_outlines/exam_outline_catalog/output/exam_outline_catalog.json"
PAIRED_PATH = "experiments/phase2_8_identity_expanded_pool_comparison_v1/paired_comparison.jsonl"
P26_PATH = "experiments/phase2_6_formal_chunk_dense_hybrid_evidence_v1/course_chunk_hybrid_results.jsonl"


def git_json(repo: Path, commit: str, path: str) -> Any:
    """Read pinned JSON / 讀取 pinned JSON。"""
    return json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"]))


def first(record: dict[str, Any], *keys: str) -> Any:
    """Return first non-empty field / 取得第一個非空欄位。"""
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def main() -> int:
    """Generate evidence packs / 產生 evidence packs。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    formal = git_json(args.source_repo, FORMAL_COMMIT, FORMAL_PATH)
    outlines = git_json(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH)
    paired = [json.loads(line) for line in (ROOT / PAIRED_PATH).read_text(encoding="utf-8").splitlines()]
    p26 = [json.loads(line) for line in (ROOT / P26_PATH).read_text(encoding="utf-8").splitlines()]
    outline_by_id = {}
    for row in outlines:
        payload = {key: row.get(key) for key in ("subject_name", "type", "applicable_exams", "core_knowledge", "outline", "remarks", "source")}
        import hashlib
        row_id = "OUT-" + hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]
        outline_by_id[row_id] = row
    p26_by_record = {row["record_id"]: row for row in p26}
    packs = []
    status_counts = Counter()
    blocker_counts = Counter()
    for record, paired_row in zip(formal, paired):
        record_id = paired_row["record_id"]
        original_row = p26_by_record[record_id]
        original_evidence = {candidate["outline_record_id"]: candidate.get("evidence_span") for candidate in original_row["candidates"]}
        for pool_name in ("expanded",):
            for candidate in paired_row[pool_name]:
                outline = outline_by_id[candidate["outline_record_id"]]
                course_provenance = {
                    "source_commit": FORMAL_COMMIT,
                    "source_path": FORMAL_PATH,
                    "raw_sha256": first(record, "raw_sha256", "content_sha256"),
                    "raw_artifact_path": first(record, "raw_artifact_path", "artifact_path"),
                    "record_id": record_id,
                }
                outline_source = outline.get("source", [])
                outline_provenance = {
                    "source_commit": OUTLINE_COMMIT,
                    "source_path": OUTLINE_PATH,
                    "outline_record_id": candidate["outline_record_id"],
                    "source": outline_source,
                    "source_evidence_available": bool(outline_source),
                }
                evidence_span = original_evidence.get(candidate["outline_record_id"])
                blockers = ["human_adjudication_required", "independent_cross_source_validation_missing"]
                if candidate["candidate_status"] == "ambiguous":
                    blockers.append("ambiguous_candidate_requires_review")
                if not evidence_span:
                    blockers.append("chunk_evidence_span_missing_from_phase2_6_top10")
                if not course_provenance["raw_sha256"] or not course_provenance["raw_artifact_path"]:
                    blockers.append("course_raw_provenance_incomplete")
                if not outline_source:
                    blockers.append("outline_source_evidence_missing")
                pack_status = "blocked" if blockers else "review_ready"
                status_counts[pack_status] += 1
                for blocker in blockers:
                    blocker_counts[blocker] += 1
                packs.append({
                    "evidence_pack_id": f"EP-{record_id}-{candidate['outline_record_id']}",
                    "record_id": record_id,
                    "course_title": record.get("course_title"),
                    "outline_record_id": candidate["outline_record_id"],
                    "outline_subject_name": candidate.get("subject_name"),
                    "rank": candidate["rank"],
                    "hybrid_score": candidate["hybrid_score"],
                    "candidate_status": candidate["candidate_status"],
                    "identity_evidence": {
                        "title_exact": candidate["title_exact"],
                        "identity_status": "exact_title_proxy" if candidate["title_exact"] else "machine_candidate",
                        "truth_status": "not_established",
                    },
                    "course_provenance": course_provenance,
                    "outline_provenance": outline_provenance,
                    "content_evidence": {
                        "available": bool(evidence_span),
                        "evidence_span": evidence_span,
                        "outline_core_knowledge_present": bool(outline.get("core_knowledge")),
                        "outline_text_present": bool(outline.get("outline")),
                    },
                    "independent_evidence": {
                        "source_family_cross_check": False,
                        "independent_corroboration_status": "not_available",
                        "same_catalog_source_only": True,
                    },
                    "review": {
                        "status": pack_status,
                        "blockers": blockers,
                        "human_adjudication_status": "not_completed",
                        "promotion_status": "blocked",
                    },
                })
    report = {
        "experiment": "phase3_independent_evidence_pack_audit_v1",
        "formal_records": len(formal),
        "expanded_top10_evidence_packs": len(packs),
        "status_counts": dict(status_counts),
        "blocker_counts": dict(blocker_counts),
        "evidence_contract": {
            "course_provenance": True,
            "outline_provenance": True,
            "identity_evidence": True,
            "content_evidence_span": True,
            "independent_cross_source_evidence": False,
            "human_adjudication": False,
            "promotion": False,
        },
        "promotion_status": "blocked",
        "formal_alignment_status": "not_started",
        "qdrant_ingest": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "phase3_evidence_audit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "evidence_packs.jsonl").write_text("".join(json.dumps(pack, ensure_ascii=False, sort_keys=True) + "\n" for pack in packs), encoding="utf-8")
    (args.output_dir / "promotion_blocker_queue.jsonl").write_text("".join(json.dumps(pack, ensure_ascii=False, sort_keys=True) + "\n" for pack in packs if pack["review"]["status"] == "blocked"), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

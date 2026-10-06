"""Analyze formal chunk/dense retrieval misses by pipeline stage.

This uses exact normalized subject only as a diagnostic proxy and never labels
alignment truth / 僅作 diagnostic，不宣稱 alignment truth。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL_COMMIT = "8922edc"
FORMAL_PATH = "output/canonical/round26_formal_syllabus_projection.json"
OUTLINE_COMMIT = "4cb1b5a7155a052450354cdff2e7e00a66728b89"
OUTLINE_PATH = "data/raw/exam_outlines/exam_outline_catalog/output/exam_outline_catalog.json"
RESULT_PATH = "experiments/phase2_6_formal_chunk_dense_hybrid_evidence_v1/course_chunk_hybrid_results.jsonl"


def norm(value: object) -> str:
    """Normalize identity text / 正規化 identity text。"""
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", str(value or "").casefold())


def git_json(repo: Path, commit: str, path: str) -> object:
    """Read JSON from pinned Git / 讀取 pinned Git JSON。"""
    raw = subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"])
    return json.loads(raw)


def main() -> int:
    """Generate error analysis / 產生 error analysis。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    formal = git_json(args.source_repo, FORMAL_COMMIT, FORMAL_PATH)
    outlines = git_json(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH)
    rows = [json.loads(line) for line in (ROOT / RESULT_PATH).read_text(encoding="utf-8").splitlines()]
    details = []
    summary = Counter()
    for record, row in zip(formal, rows):
        title = norm(record.get("course_title"))
        exact = [item for item in outlines if norm(item.get("subject_name")) == title]
        gate_names = {norm(item) for item in row["course_candidate_subject_names"]}
        top_names = [norm(item["subject_name"]) for item in row["candidates"]]
        if not exact:
            category = "no_exact_title_in_catalog"
        elif title not in gate_names:
            category = "exact_excluded_by_course_gate"
        elif title not in top_names:
            category = "exact_in_course_gate_but_reranked_out_top10"
        else:
            category = "exact_survives_gate_and_top10"
        summary[category] += 1
        details.append({
            "record_id": row["record_id"],
            "course_title": record.get("course_title"),
            "category": category,
            "exact_outline_count": len(exact),
            "top1": row["candidates"][0]["subject_name"],
            "top1_exact": norm(row["candidates"][0]["subject_name"]) == title,
            "candidate_gate_contains_exact": title in gate_names,
            "top10_contains_exact": title in top_names,
        })
    report = {
        "experiment": "phase2_6_formal_error_analysis_v1",
        "formal_records": len(formal),
        "result_records": len(rows),
        "catalog_records": len(outlines),
        "summary": dict(summary),
        "top1_exact_subject": sum(item["top1_exact"] for item in details),
        "catalog_exact_title_records": sum(item["exact_outline_count"] > 0 for item in details),
        "interpretation": {
            "primary_bottleneck": "formal_course_title_to_outline_subject_identity_coverage",
            "candidate_generation_gate_cases": summary["exact_excluded_by_course_gate"],
            "alignment_truth_available": False,
            "promotion_status": "blocked",
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "error_analysis_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "error_analysis_records.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in details), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

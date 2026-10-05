"""Compare primary and frozen Priority-5 retrieval lanes."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-report", type=Path, required=True)
    parser.add_argument("--primary-results", type=Path, required=True)
    parser.add_argument("--staged-report", type=Path, required=True)
    parser.add_argument("--staged-results", type=Path, required=True)
    parser.add_argument("--freeze-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_lines(path: Path) -> list[dict[str, Any]]:
    """Load JSONL / 載入 JSONL。"""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def summarize(rows: list[dict[str, Any]], include_slices: bool = True) -> dict[str, Any]:
    """Summarize per-lane and staged slices / 產生 lane 與 staged slice 摘要。"""
    methods = ("exact_title", "tfidf", "bm25")
    result: dict[str, Any] = {"query_count": len(rows), "methods": {}}
    for method in methods:
        candidates = [row["methods"][method] for row in rows]
        result["methods"][method] = {
            "nonempty_top10": sum(bool(x) for x in candidates),
            "top1_exact_subject": sum(bool(x) and x[0]["subject_name"] == row["course_title"] for x, row in zip(candidates, rows)),
            "top10_exact_subject": sum(any(c["subject_name"] == row["course_title"] for c in x) for x, row in zip(candidates, rows)),
        }
    if include_slices and rows and rows[0].get("lane") == "priority5_staged":
        result["quarantine_query_count"] = sum(bool(row["quarantine"]) for row in rows)
        result["overlap_query_count"] = sum(row["deduplication_decision"] == "overlap_primary_review_required" for row in rows)
        by_source: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_source[row["source_id"]].append(row)
        result["source_slices"] = {source: summarize(slice_rows, include_slices=False) for source, slice_rows in sorted(by_source.items())}
    return result


def main() -> int:
    """Create comparison artifact / 建立比較 artifact。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    primary_report = json.loads(args.primary_report.read_text(encoding="utf-8"))
    staged_report = json.loads(args.staged_report.read_text(encoding="utf-8"))
    freeze_report = json.loads(args.freeze_report.read_text(encoding="utf-8"))
    primary = load_lines(args.primary_results)
    staged = load_lines(args.staged_results)
    comparison = {
        "experiment": "phase2_3_lane_comparison_v1",
        "status": "pass",
        "primary": summarize(primary),
        "staged": summarize(staged),
        "input_lineage": {
            "primary_content_commit": primary_report["content_commit"],
            "primary_content_path": primary_report["content_path"],
            "staged_source_commit": freeze_report["source_commit"],
            "staged_record_count": freeze_report["staged_record_count"],
            "staged_overlap_with_primary": freeze_report["overlap_with_primary_count"],
            "staged_quarantine": freeze_report["quarantine_count"],
            "staged_internal_duplicates": freeze_report["duplicate_within_staged_count"],
        },
        "interpretation": "Lane diagnostics only. Different populations and staged overlap/quarantine prevent direct generalization or promotion claims.",
        "formal_alignment": "not_started",
        "human_adjudication": "not_available",
        "promotion_status": "blocked",
    }
    (args.output_dir / "lane_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(comparison, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

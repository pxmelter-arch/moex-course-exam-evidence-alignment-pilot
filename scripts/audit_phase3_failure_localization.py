"""Localize retrieval failures without claiming formal truth.

Uses exact normalized subject only as a diagnostic proxy / 僅作 diagnostic proxy。
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    paired = load_jsonl(args.root / "experiments/phase2_8_identity_expanded_pool_comparison_v1/paired_comparison.jsonl")
    reranked = load_jsonl(args.root / "experiments/phase3_topic_coverage_reranking_v2/coverage_reranked_results.jsonl")
    chunks = load_jsonl(args.root / "experiments/phase3_retrieval_refinement_v1/syllabus_atomic_topic_chunks.jsonl")
    identity_rows = load_jsonl(args.root / "experiments/phase2_7_formal_identity_bridge_v1/identity_bridge_candidates.jsonl")
    identity_by_record = {row["record_id"]: row for row in identity_rows}
    chunk_by_record = {}
    for row in chunks:
        chunk_by_record.setdefault(row.get("record_id"), []).append(row)
    records = []
    counts = Counter()
    for pair, rerank in zip(paired, reranked):
        expanded = pair["expanded"]
        exact = [c for c in expanded if c.get("title_exact")]
        top1 = rerank["candidates"][0]
        top1_exact = bool(top1.get("title_exact"))
        if top1_exact:
            category = "proxy_top1_exact"
        elif exact:
            category = "proxy_ranker_miss_exact_in_top10"
        else:
            category = "proxy_identity_or_catalog_coverage_miss"
        course_id = pair["record_id"]
        course_chunks = chunk_by_record.get(course_id, [])
        contam = sum(1 for row in course_chunks if row.get("lane") == "contamination")
        content = sum(1 for row in course_chunks if row.get("lane") == "content")
        identity = identity_by_record.get(course_id, {})
        item = {
            "record_id": course_id,
            "course_title": pair["course_title"],
            "category": category,
            "identity_status": identity.get("identity_status"),
            "identity_reason": identity.get("identity_reason"),
            "exact_title_match_count": identity.get("exact_title_match_count"),
            "exact_candidates_in_expanded_top10": len(exact),
            "top1_outline_record_id": top1.get("outline_record_id"),
            "top1_subject_name": top1.get("subject_name"),
            "top1_title_exact": top1_exact,
            "top1_hybrid_score": top1.get("hybrid_score"),
            "top1_topic_coverage": top1.get("bidirectional_topic_coverage"),
            "top1_contamination_chunks": contam,
            "top1_content_chunks": content,
            "recovered_top10": pair.get("recovered_top10", []),
            "exact_candidates": [{"outline_record_id": c["outline_record_id"], "subject_name": c.get("subject_name"), "rank": c.get("rank")} for c in exact],
        }
        records.append(item)
        counts[category] += 1
    samples = {key: [row for row in records if row["category"] == key][:10] for key in counts}
    identity_counts = Counter((row.get("identity_status"), row.get("identity_reason")) for row in records)
    report = {
        "experiment": "phase3_failure_localization_v1",
        "records": len(records),
        "diagnostic_proxy": "title_exact only; not human alignment truth",
        "counts": dict(counts),
        "identity_status_counts": {f"{status}|{reason}": count for (status, reason), count in identity_counts.items()},
        "causal_boundary": {
            "proxy_ranker_miss_exact_in_top10": "identity proxy exists in expanded top10 but is not top1; inspect ranking and duplicate variant resolution",
            "proxy_identity_or_catalog_coverage_miss": "no exact identity proxy in expanded top10; inspect alias, candidate gate, naming, or catalog scope",
            "contamination_counts": "course-side flags are diagnostics and do not prove causality",
        },
        "samples": samples,
        "promotion_status": "blocked",
        "formal_alignment": "not_started",
        "qdrant_ingest": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "failure_localization_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "failure_localization.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    print(json.dumps({"counts": dict(counts), "records": len(records)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build identity review lane and variant-aware ranking ablation.

All decisions remain null; exact title is a diagnostic proxy only.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path


def load(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def metrics(rows):
    top1 = sum(bool(r["ranked"]) and r["ranked"][0].get("title_exact") for r in rows)
    top10 = sum(any(c.get("title_exact") for c in r["ranked"][:10]) for r in rows)
    return {"top1_exact": top1, "top10_exact": top10}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    failure = load(args.root / "experiments/phase3_failure_localization_v1/failure_localization.jsonl")
    bridge = {r["record_id"]: r for r in load(args.root / "experiments/phase2_7_formal_identity_bridge_v1/identity_bridge_candidates.jsonl")}
    reranked = load(args.root / "experiments/phase3_topic_coverage_reranking_v2/coverage_reranked_results.jsonl")
    failure_by_id = {r["record_id"]: r for r in failure}
    review = []
    for row in failure:
        if row["category"] != "proxy_identity_or_catalog_coverage_miss":
            continue
        identity = bridge.get(row["record_id"], {})
        review.append({
            "review_id": f"IDREV-{row['record_id']}",
            "record_id": row["record_id"],
            "course_title": row["course_title"],
            "failure_category": row["category"],
            "identity_status": identity.get("identity_status"),
            "identity_reason": identity.get("identity_reason"),
            "exact_title_match_count": identity.get("exact_title_match_count"),
            "candidate_outline_ids": [c["outline_record_id"] for c in identity.get("top_alias_candidates", [])],
            "identity_decision": None,
            "evidence_sufficiency": None,
            "notes": None,
            "promotion_status": "blocked",
        })
    ranked_rows = []
    for result in reranked:
        if result["record_id"] not in {r["record_id"] for r in failure if r["category"] == "proxy_ranker_miss_exact_in_top10"}:
            continue
        candidates = result["candidates"]
        configs = {}
        configs["current"] = sorted(candidates, key=lambda c: (-c["coverage_reranked_score"], c["outline_record_id"]))
        configs["title_boost_020"] = sorted(candidates, key=lambda c: (-(c["coverage_reranked_score"] + 0.20 * float(c.get("title_exact", False))), c["outline_record_id"]))
        configs["title_boost_050"] = sorted(candidates, key=lambda c: (-(c["coverage_reranked_score"] + 0.50 * float(c.get("title_exact", False))), c["outline_record_id"]))
        configs["hard_exact_then_score"] = sorted(candidates, key=lambda c: (-int(c.get("title_exact", False)), -c["coverage_reranked_score"], c["outline_record_id"]))
        ranked_rows.append({"record_id": result["record_id"], "course_title": result["course_title"], "configurations": {name: [{"outline_record_id": c["outline_record_id"], "subject_name": c.get("subject_name"), "title_exact": c.get("title_exact"), "score": c.get("coverage_reranked_score")} for c in rows[:10]] for name, rows in configs.items()}})
    # Full-scope ranking ablation, exact title remains a diagnostic proxy.
    all_ranked = []
    for result in reranked:
        candidates = result["candidates"]
        configs = {
            "current": sorted(candidates, key=lambda c: (-c["coverage_reranked_score"], c["outline_record_id"])),
            "title_boost_020": sorted(candidates, key=lambda c: (-(c["coverage_reranked_score"] + 0.20 * float(c.get("title_exact", False))), c["outline_record_id"])),
            "title_boost_050": sorted(candidates, key=lambda c: (-(c["coverage_reranked_score"] + 0.50 * float(c.get("title_exact", False))), c["outline_record_id"])),
            "hard_exact_then_score": sorted(candidates, key=lambda c: (-int(c.get("title_exact", False)), -c["coverage_reranked_score"], c["outline_record_id"])),
        }
        for name, rows in configs.items():
            all_ranked.append({"config": name, "ranked": rows, "course_title": result["course_title"]})
    config_metrics = {}
    for name in {row["config"] for row in all_ranked}:
        config_metrics[name] = metrics([row for row in all_ranked if row["config"] == name])
    report = {
        "experiment": "phase3_identity_review_and_variant_ranking_v1",
        "identity_review_queue": len(review),
        "ranker_miss_cases": len(ranked_rows),
        "ranker_miss_case_titles": sorted({row["course_title"] for row in ranked_rows}),
        "diagnostic_proxy": "title_exact; not human alignment truth",
        "variant_ablation_metrics": config_metrics,
        "review_decisions_created": 0,
        "promotion_status": "blocked",
        "formal_alignment": "not_started",
        "qdrant_ingest": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "identity_review_queue.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in review), encoding="utf-8")
    (args.output_dir / "variant_ranker_miss_cases.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in ranked_rows), encoding="utf-8")
    (args.output_dir / "identity_variant_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

"""Audit negative retrieval results without auto-promotion.

Produces hierarchy, contamination, threshold, weight, corroboration, and human
review artifacts / 產生負結果 audit 與人工 review queue。
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REFINE = ROOT / "experiments/phase3_retrieval_refinement_v1"
COVERAGE = ROOT / "experiments/phase3_topic_coverage_reranking_v2"
PACKS = ROOT / "experiments/phase3_independent_evidence_audit_v1/evidence_packs.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL / 讀取 JSONL。"""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def exact_metrics(rows: list[dict], score_key: str, component_weights: tuple[float, float, float, float] | None = None) -> dict[str, int]:
    """Calculate exact proxy metrics / 計算 exact proxy metrics。"""
    top1 = top10 = 0
    for row in rows:
        candidates = row["candidates"]
        if component_weights:
            wi, wl, wd, wc = component_weights
            candidates = [dict(candidate, _score=wi * candidate["hybrid_score"] + wl * candidate["lexical_topic_max"] + wd * candidate["dense_topic_max"] + wc * candidate["bidirectional_topic_coverage"]) for candidate in candidates]
        else:
            candidates = sorted(candidates, key=lambda item: (-item[score_key], item["outline_record_id"]))
        if component_weights:
            candidates.sort(key=lambda item: (-item["_score"], item["outline_record_id"]))
        title = row["course_title"]
        top1 += bool(candidates and candidates[0]["subject_name"] == title)
        top10 += any(candidate["subject_name"] == title for candidate in candidates[:10])
    return {"top1_exact": top1, "top10_exact": top10}


def main() -> int:
    """Run consolidated audit / 執行 consolidated audit。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    syllabus_sections = load_jsonl(REFINE / "syllabus_section_parse.jsonl")
    syllabus_chunks = load_jsonl(REFINE / "syllabus_atomic_topic_chunks.jsonl")
    outline_items = load_jsonl(REFINE / "outline_atomic_items.jsonl")
    coverage_rows = load_jsonl(COVERAGE / "coverage_reranked_results.jsonl")
    packs = load_jsonl(PACKS)

    # Hierarchy refinement audit / hierarchy 品質 audit
    hierarchy = {
        "syllabus_records": len(syllabus_sections),
        "syllabus_chunks": len(syllabus_chunks),
        "outline_items": len(outline_items),
        "syllabus_chapter_unresolved": sum(row.get("chapter") is None for row in syllabus_chunks),
        "outline_chapter_unresolved": sum(row.get("chapter") is None for row in outline_items),
        "syllabus_topic_present": sum(bool(row.get("topic")) for row in syllabus_chunks),
        "outline_topic_present": sum(bool(row.get("topic")) for row in outline_items),
        "section_fields": dict(Counter(row["field"] for row in syllabus_chunks)),
        "hierarchy_status": "chapter_mapping_unresolved",
    }

    # Contamination audit / contamination audit
    contamination_terms = {"assessment": r"評量|考試|assessment|exam|quiz|作業|報告", "administrative": r"office|email|電話|時間|星期|教室|授課|教師|office hour", "textbook": r"教材|教科書|textbook|參考書|handbook", "schedule_note": r"schedule|課程進度|note|備註|注意|copyright|智慧財產|週次|日期", "teaching_method": r"教學方式|講授|討論|實作|teaching approach"}
    contamination = {"terms": {}, "syllabus_flagged_chunks": 0, "outline_flagged_items": 0}
    for name, pattern in contamination_terms.items():
        s_count = sum(bool(re.search(pattern, row["text"], re.I)) for row in syllabus_chunks)
        o_count = sum(bool(re.search(pattern, row["text"], re.I)) for row in outline_items)
        contamination["terms"][name] = {"syllabus_chunks": s_count, "outline_items": o_count}
    for row in syllabus_chunks:
        if any(re.search(pattern, row["text"], re.I) for pattern in contamination_terms.values()):
            contamination["syllabus_flagged_chunks"] += 1
    for row in outline_items:
        if any(re.search(pattern, row["text"], re.I) for pattern in contamination_terms.values()):
            contamination["outline_flagged_items"] += 1

    # Threshold sensitivity / threshold sensitivity
    thresholds = ["0.3", "0.42", "0.55", "0.65"]
    threshold_metrics = {}
    for threshold in thresholds:
        rows = []
        for row in coverage_rows:
            cloned = {"course_title": row["course_title"], "candidates": []}
            for candidate in row["candidates"]:
                c = dict(candidate)
                coverage = c["coverage_by_threshold"][threshold]["bidirectional"]
                c["_threshold_score"] = 0.20 * c["hybrid_score"] + 0.25 * c["lexical_topic_max"] + 0.25 * c["dense_topic_max"] + 0.30 * coverage
                cloned["candidates"].append(c)
            rows.append(cloned)
        metrics = exact_metrics(rows, "_threshold_score")
        threshold_metrics[threshold] = metrics

    # Weight ablation / weight ablation
    weight_configs = {"current": (0.20, 0.25, 0.25, 0.30), "identity_removed": (0.0, 0.30, 0.30, 0.40), "coverage_heavy": (0.10, 0.20, 0.20, 0.50), "lexical_heavy": (0.15, 0.40, 0.30, 0.15), "dense_heavy": (0.15, 0.20, 0.45, 0.20)}
    weight_metrics = {name: {"weights": dict(zip(("identity", "lexical", "dense", "coverage"), weights)), **exact_metrics(coverage_rows, "coverage_reranked_score", weights)} for name, weights in weight_configs.items()}

    # Independent corroboration / independent source corroboration
    source_paths = Counter(pack["outline_provenance"]["source_path"] for pack in packs)
    source_labels = Counter()
    for pack in packs:
        source = pack["outline_provenance"].get("source")
        values = source if isinstance(source, list) else [source]
        for value in values:
            if isinstance(value, dict):
                source_labels[str(value.get("file", "unknown"))] += 1
            elif value:
                source_labels[str(value)] += 1
    corroboration = {"packs": len(packs), "outline_source_paths": dict(source_paths), "catalog_source_labels": dict(source_labels), "independent_corroboration_ready": 0, "status": "not_available_same_catalog_provenance_only"}

    # Human review protocol / human review protocol
    review_schema = {"label": ["supports", "partially_supports", "does_not_support", "unclear", None], "identity_decision": ["accept", "alias", "reject", "unclear", None], "evidence_sufficiency": ["sufficient", "insufficient", "unclear", None], "adjudicator": None, "adjudication_timestamp": None, "notes": None}
    review_queue = []
    for pack in packs:
        review_queue.append({"evidence_pack_id": pack["evidence_pack_id"], "record_id": pack["record_id"], "outline_record_id": pack["outline_record_id"], "rank": pack["rank"], "candidate_status": pack["candidate_status"], "identity_evidence": pack["identity_evidence"], "evidence_span_available": pack["content_evidence"]["available"], "machine_label": None, "human_review": review_schema})
    protocol = {"mode": "no-human-label", "purpose": "review machine candidates without treating machine inference as truth", "required_fields": review_schema, "promotion_rule": "no automatic promotion; explicit adjudication and independent evidence required", "queue_size": len(review_queue)}

    report = {"experiment": "phase3_negative_result_audit_v1", "hierarchy": hierarchy, "contamination": contamination, "threshold_sensitivity": threshold_metrics, "weight_ablation": weight_metrics, "independent_corroboration": corroboration, "human_review": {"queue_size": len(review_queue), "machine_labels_created": 0, "protocol": protocol}, "formal_alignment": "not_started", "promotion_status": "blocked", "qdrant_ingest": False}
    (args.output_dir / "negative_result_audit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "human_adjudication_review_protocol.json").write_text(json.dumps(protocol, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "human_review_queue.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in review_queue), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

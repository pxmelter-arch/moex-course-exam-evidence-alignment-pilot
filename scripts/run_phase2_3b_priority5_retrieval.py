"""Run the frozen 373-record Priority-5 staged retrieval diagnostic."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_phase2_1_course_outline_retrieval import (  # noqa: E402
    OUTLINE_COMMIT,
    OUTLINE_PATH,
    TOP_K,
    bm25_scores,
    build_bm25,
    candidate_payload,
    document_text,
    git_show,
    normalize_text,
    outline_record_id,
    ranked_indices,
)
from sklearn.feature_extraction.text import TfidfVectorizer


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Run staged diagnostic / 執行 staged diagnostic。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    staged = [json.loads(line) for line in args.manifest.read_text(encoding="utf-8").splitlines() if line]
    outlines = json.loads(git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH))
    if len(staged) != 373 or len(outlines) != 542:
        raise SystemExit("frozen input count mismatch")
    for outline in outlines:
        outline["outline_record_id"] = outline_record_id(outline)
    documents = [document_text(outline) for outline in outlines]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
    tfidf_matrix = vectorizer.fit_transform([normalize_text(x) for x in documents])
    tokenized, df, average_length = build_bm25(documents)
    exact_index: dict[str, list[int]] = {}
    for i, outline in enumerate(outlines):
        exact_index.setdefault(normalize_text(outline.get("subject_name")), []).append(i)
    methods = ("exact_title", "tfidf", "bm25")
    stats = {name: {"queries": 0, "nonempty_top10": 0, "top1_exact_subject": 0, "top10_exact_subject": 0} for name in methods}
    results = []
    for row in staged:
        query = " ".join(str(row.get(field) or "") for field in ("course_title", "department", "content_text") if row.get(field))
        title = normalize_text(row.get("course_title"))
        exact = exact_index.get(title, [])
        exact_scores = np.zeros(len(outlines))
        exact_scores[exact] = 1.0
        tfidf_scores = (tfidf_matrix @ vectorizer.transform([normalize_text(query)]).T).toarray().ravel()
        bm25 = bm25_scores(query, tokenized, df, average_length)
        mapping = {"exact_title": (exact_scores, exact), "tfidf": (tfidf_scores, None), "bm25": (bm25, None)}
        method_results = {}
        for method, (scores, fixed) in mapping.items():
            indices = fixed if fixed is not None else ranked_indices(scores)
            candidates = [candidate_payload(i, scores[i], outlines) for i in indices[:TOP_K]]
            method_results[method] = candidates
            current = stats[method]
            current["queries"] += 1
            current["nonempty_top10"] += bool(candidates)
            exact_flags = [normalize_text(c["subject_name"]) == title for c in candidates]
            current["top1_exact_subject"] += bool(exact_flags and exact_flags[0])
            current["top10_exact_subject"] += any(exact_flags)
        results.append({
            "record_id": row["record_id"],
            "source_id": row["source_id"],
            "school_id": row["school_id"],
            "course_title": row["course_title"],
            "content_status": row["content_status"],
            "quarantine": row["quarantine"],
            "deduplication_decision": row["deduplication_decision"],
            "query_fields": ["course_title", "department", "content_text"],
            "lane": "priority5_staged",
            "retrieval_status": "candidate_only",
            "methods": method_results,
        })
    report = {
        "experiment": "phase2_3b_priority5_staged_outline_retrieval_v1",
        "status": "pass",
        "staged_manifest": str(args.manifest),
        "staged_record_count": len(staged),
        "outline_commit": OUTLINE_COMMIT,
        "outline_path": OUTLINE_PATH,
        "outline_record_count": len(outlines),
        "methods": stats,
        "top_k": TOP_K,
        "quarantine_queries": sum(bool(row["quarantine"]) for row in staged),
        "overlap_queries": sum(row["deduplication_decision"] == "overlap_primary_review_required" for row in staged),
        "candidate_only": True,
        "formal_alignment": "not_started",
        "promotion_status": "blocked",
    }
    (args.output_dir / "retrieval_results.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in results), encoding="utf-8")
    (args.output_dir / "retrieval_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

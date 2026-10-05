"""Run content-bearing primary course to exam-outline retrieval.

This bounded lane uses only the pinned 520 content-bearing records from the
600-record structured-content artifact. Priority-5 aggregate staged counts are
not guessed or merged here; they require a separate materialized input freeze.
"""
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
    char_ngrams,
    document_text,
    git_show,
    normalize_text,
    outline_record_id,
    ranked_indices,
)
from sklearn.feature_extraction.text import TfidfVectorizer

CONTENT_COMMIT = "1f2a2e635d61e01b5788a3c8c5b66adeb5c7e9db"
CONTENT_PATH = "output/unified_dataset/round26_20261004/structured_content_600.json"
EXPECTED_TOTAL = 600
EXPECTED_PRIMARY = 520


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def content_query(record: dict[str, Any]) -> str:
    """Build content-bearing query / 建立 content-bearing query。"""
    return " ".join(
        str(record.get(field) or "")
        for field in ("course_title", "department", "school_name", "content_text")
        if record.get(field)
    )


def main() -> int:
    """Run primary content retrieval / 執行 primary content retrieval。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = json.loads(git_show(args.source_repo, CONTENT_COMMIT, CONTENT_PATH))
    outlines = json.loads(git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH))
    if len(records) != EXPECTED_TOTAL:
        raise SystemExit("structured content count mismatch")
    primary = [r for r in records if r.get("content_status") == "content_bearing"]
    if len(primary) != EXPECTED_PRIMARY:
        raise SystemExit("content-bearing primary count mismatch")
    for outline in outlines:
        outline["outline_record_id"] = outline_record_id(outline)
    documents = [document_text(outline) for outline in outlines]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
    tfidf_matrix = vectorizer.fit_transform([normalize_text(x) for x in documents])
    tokenized, df, average_length = build_bm25(documents)
    exact_index: dict[str, list[int]] = {}
    for i, outline in enumerate(outlines):
        exact_index.setdefault(normalize_text(outline.get("subject_name")), []).append(i)
    method_counts = {name: {"queries": 0, "nonempty_top10": 0, "top1_exact_subject": 0, "top10_exact_subject": 0} for name in ("exact_title", "tfidf", "bm25")}
    results = []
    for record in primary:
        query = content_query(record)
        title = normalize_text(record.get("course_title"))
        exact = exact_index.get(title, [])
        exact_scores = np.zeros(len(outlines))
        exact_scores[exact] = 1.0
        tfidf_scores = (tfidf_matrix @ vectorizer.transform([normalize_text(query)]).T).toarray().ravel()
        bm25 = bm25_scores(query, tokenized, df, average_length)
        method_map = {"exact_title": (exact_scores, exact), "tfidf": (tfidf_scores, None), "bm25": (bm25, None)}
        method_results = {}
        for method, (scores, fixed) in method_map.items():
            indices = fixed if fixed is not None else ranked_indices(scores)
            candidates = [candidate_payload(i, scores[i], outlines) for i in indices[:TOP_K]]
            method_results[method] = candidates
            stats = method_counts[method]
            stats["queries"] += 1
            stats["nonempty_top10"] += bool(candidates)
            exact_flags = [normalize_text(c["subject_name"]) == title for c in candidates]
            stats["top1_exact_subject"] += bool(exact_flags and exact_flags[0])
            stats["top10_exact_subject"] += any(exact_flags)
        results.append({
            "structured_id": record.get("structured_id"),
            "school_id": record.get("school_id"),
            "course_title": record.get("course_title"),
            "department": record.get("department"),
            "content_status": record.get("content_status"),
            "content_chars": record.get("content_chars"),
            "query_fields": ["course_title", "department", "school_name", "content_text"],
            "lane": "primary_content_bearing",
            "retrieval_status": "candidate_only",
            "methods": method_results,
        })
    report = {
        "experiment": "phase2_3a_primary_content_outline_retrieval_v1",
        "status": "pass",
        "content_commit": CONTENT_COMMIT,
        "content_path": CONTENT_PATH,
        "content_total_count": len(records),
        "primary_content_bearing_count": len(primary),
        "outline_commit": OUTLINE_COMMIT,
        "outline_path": OUTLINE_PATH,
        "outline_record_count": len(outlines),
        "methods": method_counts,
        "top_k": TOP_K,
        "priority5_373_lane": "blocked_pending_materialized_pinned_artifact",
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

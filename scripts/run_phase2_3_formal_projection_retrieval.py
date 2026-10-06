"""Run formal syllabus projection content retrieval against normalized outlines.

This replaces the former metadata-only formal lane for content diagnostics.
The older 520-record diagnostic remains immutable and is not overwritten.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

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

FORMAL_PROJECTION_COMMIT = "8922edc"
FORMAL_PROJECTION_PATH = "output/canonical/round26_formal_syllabus_projection.json"
EXPECTED_FORMAL = 176
EXPECTED_OUTLINES = 542


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def query_text(record: dict[str, Any]) -> str:
    """Build formal syllabus query / 建立 formal syllabus query。"""
    fields = ("course_title", "department_name", "school_name", "content_text")
    return " ".join(str(record.get(field) or "") for field in fields if record.get(field))


def main() -> int:
    """Run formal projection retrieval / 執行正式 projection retrieval。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    formal = json.loads(git_show(args.source_repo, FORMAL_PROJECTION_COMMIT, FORMAL_PROJECTION_PATH))
    outlines = json.loads(git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH))
    if len(formal) != EXPECTED_FORMAL or len(outlines) != EXPECTED_OUTLINES:
        raise SystemExit("formal projection or outline count mismatch")
    invalid = [r for r in formal if not (r.get("formal_gate") == "passed" and r.get("content_status") == "full" and r.get("content_text"))]
    if invalid:
        raise SystemExit(f"formal projection gate mismatch: {len(invalid)} records")
    for outline in outlines:
        outline["outline_record_id"] = outline_record_id(outline)
    documents = [document_text(outline) for outline in outlines]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
    tfidf_matrix = vectorizer.fit_transform([normalize_text(text) for text in documents])
    tokenized, df, average_length = build_bm25(documents)
    exact_index: dict[str, list[int]] = {}
    for index, outline in enumerate(outlines):
        exact_index.setdefault(normalize_text(outline.get("subject_name")), []).append(index)
    methods = ("exact_title", "tfidf", "bm25")
    stats = {name: {"queries": 0, "nonempty_top10": 0, "top1_exact_subject": 0, "top10_exact_subject": 0} for name in methods}
    results = []
    for record in formal:
        query = query_text(record)
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
            stats[method]["queries"] += 1
            stats[method]["nonempty_top10"] += bool(candidates)
            exact_flags = [normalize_text(c["subject_name"]) == title for c in candidates]
            stats[method]["top1_exact_subject"] += bool(exact_flags and exact_flags[0])
            stats[method]["top10_exact_subject"] += any(exact_flags)
        results.append({
            "record_id": record.get("candidate_id"),
            "school_id": record.get("school_id"),
            "course_title": record.get("course_title"),
            "department_name": record.get("department_name"),
            "content_status": record.get("content_status"),
            "formal_gate": record.get("formal_gate"),
            "promotion_status": record.get("promotion_status"),
            "content_char_count": record.get("content_char_count"),
            "content_sha256": record.get("content_sha256"),
            "query_fields": ["course_title", "department_name", "school_name", "content_text"],
            "lane": "formal_syllabus_projection",
            "retrieval_status": "candidate_only",
            "methods": method_results,
        })
    report = {
        "experiment": "phase2_3_formal_syllabus_projection_retrieval_v1",
        "status": "pass",
        "formal_projection_commit": FORMAL_PROJECTION_COMMIT,
        "formal_projection_path": FORMAL_PROJECTION_PATH,
        "formal_record_count": len(formal),
        "formal_gate_passed_count": len(formal) - len(invalid),
        "outline_commit": OUTLINE_COMMIT,
        "outline_path": OUTLINE_PATH,
        "outline_record_count": len(outlines),
        "methods": stats,
        "top_k": TOP_K,
        "replaces_formal_metadata_only_lane": True,
        "candidate_only": True,
        "formal_alignment": "not_started",
        "promotion_status": "blocked_pending_alignment_evidence",
    }
    (args.output_dir / "retrieval_results.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in results), encoding="utf-8")
    (args.output_dir / "retrieval_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

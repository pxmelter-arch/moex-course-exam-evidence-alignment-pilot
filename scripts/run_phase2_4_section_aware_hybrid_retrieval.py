"""Run section-aware formal syllabus to exam-outline hybrid retrieval.

The runner preserves raw syllabus fields, creates explicit topic/content views,
and emits explainable component scores. Results remain candidate diagnostics.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_phase2_1_course_outline_retrieval import (  # noqa: E402
    OUTLINE_COMMIT,
    OUTLINE_PATH,
    TOP_K,
    bm25_scores,
    build_bm25,
    git_show,
    normalize_text,
    outline_record_id,
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


def as_text(value: Any) -> str:
    """Convert structured or scalar values to stable text / 統一轉成文字。"""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def field_text(fields: dict[str, Any], name: str) -> str:
    """Read one syllabus field without imputation / 讀取欄位但不補值。"""
    return as_text(fields.get(name)).strip()


def section_aware_views(record: dict[str, Any]) -> dict[str, Any]:
    """Create section-aware views while retaining raw fields / 建立 section views。"""
    fields = record.get("syllabus_fields") or {}
    description = field_text(fields, "course_description")
    syllabus_outline = field_text(fields, "outline")
    objectives = field_text(fields, "objectives")
    assessment = field_text(fields, "assessment")
    textbook = field_text(fields, "textbook")
    prerequisite = field_text(fields, "prerequisite")
    topic_text = "\n".join(x for x in (syllabus_outline, description) if x)
    content_text = "\n".join(x for x in (description, syllabus_outline, objectives) if x)
    metadata_text = "\n".join(
        x for x in (assessment, textbook, prerequisite) if x
    )
    return {
        "raw_content_sections": record.get("content_sections"),
        "raw_syllabus_field_names": sorted(fields),
        "section_presence": {name: bool(value) for name, value in {
            "course_description": description,
            "outline": syllabus_outline,
            "objectives": objectives,
            "assessment": assessment,
            "textbook": textbook,
            "prerequisite": prerequisite,
        }.items()},
        "topic_text": topic_text,
        "content_text": content_text,
        "metadata_text": metadata_text,
    }


def outline_views(outline: dict[str, Any]) -> dict[str, str]:
    """Create weighted outline field views / 建立命題大綱欄位 views。"""
    return {
        "subject_name": as_text(outline.get("subject_name")),
        "core_knowledge": as_text(outline.get("core_knowledge")),
        "outline": as_text(outline.get("outline")),
        "remarks": as_text(outline.get("remarks")),
    }


def normalize_scores(scores: np.ndarray) -> np.ndarray:
    """Scale non-negative scores to [0, 1] / 將分數縮放至 [0, 1]。"""
    values = np.asarray(scores, dtype=float)
    if values.size == 0 or float(values.max()) <= 0:
        return np.zeros_like(values)
    return np.clip(values / float(values.max()), 0.0, 1.0)


def top_indices(scores: np.ndarray, limit: int = TOP_K) -> list[int]:
    """Return stable descending score indices / 回傳穩定排序索引。"""
    return sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))[:limit]


def exact_title_indices(title: str, outlines: list[dict[str, Any]]) -> list[int]:
    """Find exact normalized subject-name matches / 找 exact subject match。"""
    wanted = normalize_text(title)
    return [i for i, item in enumerate(outlines) if normalize_text(item.get("subject_name")) == wanted]


def candidate_status(
    title_exact: bool,
    score: float,
    next_score: float,
    duplicate_subject: bool,
) -> str:
    """Assign conservative diagnostic status / 保守指定 diagnostic status。"""
    margin = score - next_score
    if title_exact and not duplicate_subject and score >= 0.55:
        return "exact"
    if title_exact or margin < 0.05 or score >= 0.35:
        return "ambiguous"
    return "weak"


def main() -> int:
    """Run section-aware hybrid retrieval / 執行 section-aware hybrid retrieval。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    formal = json.loads(git_show(args.source_repo, FORMAL_PROJECTION_COMMIT, FORMAL_PROJECTION_PATH))
    outlines = json.loads(git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH))
    if len(formal) != EXPECTED_FORMAL or len(outlines) != EXPECTED_OUTLINES:
        raise SystemExit("formal projection or outline count mismatch")
    if any(r.get("formal_gate") != "passed" for r in formal):
        raise SystemExit("formal gate mismatch")

    formal_views = [section_aware_views(record) for record in formal]
    outline_view_rows = [outline_views(item) for item in outlines]
    for item in outlines:
        item["outline_record_id"] = outline_record_id(item)

    # Separate field models prevent generic remarks from dominating topic evidence.
    field_names = ("subject_name", "core_knowledge", "outline", "remarks")
    field_vectors: dict[str, tuple[TfidfVectorizer, Any]] = {}
    field_scores_cache: dict[str, list[np.ndarray]] = {}
    for field in field_names:
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
        matrix = vectorizer.fit_transform([normalize_text(row[field]) for row in outline_view_rows])
        field_vectors[field] = (vectorizer, matrix)
        field_scores_cache[field] = []

    # BM25 document is deliberately weighted: subject/core/outline dominate remarks.
    weighted_documents = [
        " ".join([
            row["subject_name"] + " " + row["subject_name"],
            row["core_knowledge"] + " " + row["core_knowledge"],
            row["outline"] + " " + row["outline"],
            row["remarks"],
        ])
        for row in outline_view_rows
    ]
    tokenized, df, average_length = build_bm25(weighted_documents)
    duplicate_subjects: dict[str, int] = {}
    for row in outline_view_rows:
        key = normalize_text(row["subject_name"])
        duplicate_subjects[key] = duplicate_subjects.get(key, 0) + 1

    results: list[dict[str, Any]] = []
    status_counts = {"exact": 0, "ambiguous": 0, "weak": 0}
    review_queue: list[dict[str, Any]] = []
    method_counts = {
        "title_identity": {"top1_exact_subject": 0, "top10_exact_subject": 0},
        "hybrid": {"top1_exact_subject": 0, "top10_exact_subject": 0},
    }

    for record, views in zip(formal, formal_views):
        title = as_text(record.get("course_title"))
        title_norm = normalize_text(title)
        exact_indices = exact_title_indices(title, outlines)
        title_query = normalize_text(" ".join([title, as_text(record.get("department_name"))]))
        topic_query = normalize_text(views["topic_text"])
        content_query = normalize_text(views["content_text"])
        title_scores = cosine_similarity(
            field_vectors["subject_name"][1],
            field_vectors["subject_name"][0].transform([title_query]),
        ).ravel()
        core_scores = cosine_similarity(
            field_vectors["core_knowledge"][1],
            field_vectors["core_knowledge"][0].transform([topic_query]),
        ).ravel()
        outline_scores = cosine_similarity(
            field_vectors["outline"][1],
            field_vectors["outline"][0].transform([topic_query]),
        ).ravel()
        remarks_scores = cosine_similarity(
            field_vectors["remarks"][1],
            field_vectors["remarks"][0].transform([content_query]),
        ).ravel()
        bm25 = normalize_scores(bm25_scores(content_query, tokenized, df, average_length))
        title_identity = np.zeros(len(outlines), dtype=float)
        title_identity[exact_indices] = 1.0
        title_similarity = np.maximum(normalize_scores(title_scores), title_identity)
        topic_score = 0.60 * normalize_scores(core_scores) + 0.40 * normalize_scores(outline_scores)
        # Explicitly small remarks weight; assessment/textbook/prerequisite are excluded.
        hybrid = (
            0.30 * title_identity
            + 0.20 * title_similarity
            + 0.20 * topic_score
            + 0.20 * bm25
            + 0.10 * normalize_scores(remarks_scores)
        )
        ranked = top_indices(hybrid)
        candidates = []
        for rank, index in enumerate(ranked):
            next_score = float(hybrid[ranked[rank + 1]]) if rank + 1 < len(ranked) else 0.0
            exact = index in exact_indices
            status = candidate_status(
                exact,
                float(hybrid[index]),
                next_score,
                duplicate_subjects.get(normalize_text(outlines[index].get("subject_name")), 0) > 1,
            )
            candidates.append({
                "rank": rank + 1,
                "outline_record_id": outlines[index]["outline_record_id"],
                "subject_name": outlines[index].get("subject_name"),
                "applicable_exams": outlines[index].get("applicable_exams"),
                "source": outlines[index].get("source"),
                "candidate_status": status,
                "exact_title_match": exact,
                "component_scores": {
                    "title_identity": round(float(title_identity[index]), 6),
                    "title_similarity": round(float(title_similarity[index]), 6),
                    "topic_score": round(float(topic_score[index]), 6),
                    "core_knowledge_score": round(float(normalize_scores(core_scores)[index]), 6),
                    "outline_topic_score": round(float(normalize_scores(outline_scores)[index]), 6),
                    "content_bm25_score": round(float(bm25[index]), 6),
                    "remarks_score": round(float(normalize_scores(remarks_scores)[index]), 6),
                    "hybrid_score": round(float(hybrid[index]), 6),
                },
            })
        top = candidates[0] if candidates else None
        top10_exact = any(item["exact_title_match"] for item in candidates)
        method_counts["title_identity"]["top1_exact_subject"] += bool(exact_indices and normalize_text(outlines[exact_indices[0]].get("subject_name")) == title_norm)
        method_counts["title_identity"]["top10_exact_subject"] += bool(exact_indices)
        method_counts["hybrid"]["top1_exact_subject"] += bool(top and top["exact_title_match"])
        method_counts["hybrid"]["top10_exact_subject"] += top10_exact
        if top:
            status_counts[top["candidate_status"]] += 1
            if top["candidate_status"] != "exact":
                review_queue.append({
                    "record_id": record.get("candidate_id"),
                    "course_title": title,
                    "review_status": top["candidate_status"],
                    "top_candidate": top,
                    "candidate_count": len(candidates),
                    "human_adjudication": "required",
                })
        results.append({
            "record_id": record.get("candidate_id"),
            "school_id": record.get("school_id"),
            "course_title": title,
            "department_name": record.get("department_name"),
            "formal_gate": record.get("formal_gate"),
            "promotion_status": record.get("promotion_status"),
            "section_aware": views,
            "retrieval_status": "candidate_only",
            "methods": {"title_identity": exact_indices, "hybrid": candidates},
        })

    report = {
        "experiment": "phase2_4_formal_section_aware_hybrid_retrieval_v1",
        "status": "pass",
        "formal_projection_commit": FORMAL_PROJECTION_COMMIT,
        "formal_projection_path": FORMAL_PROJECTION_PATH,
        "formal_record_count": len(formal),
        "formal_gate_passed_count": sum(r.get("formal_gate") == "passed" for r in formal),
        "outline_commit": OUTLINE_COMMIT,
        "outline_path": OUTLINE_PATH,
        "outline_record_count": len(outlines),
        "section_field_presence": {name: sum(v["section_presence"][name] for v in formal_views) for name in formal_views[0]["section_presence"]},
        "weights": {"title_identity": 0.30, "title_similarity": 0.20, "topic_score": 0.20, "content_bm25": 0.20, "remarks": 0.10},
        "topic_weights": {"core_knowledge": 0.60, "outline": 0.40},
        "methods": method_counts,
        "top_k": TOP_K,
        "top_candidate_status_counts": status_counts,
        "review_queue_count": len(review_queue),
        "candidate_only": True,
        "formal_alignment": "not_started",
        "promotion_status": "blocked_pending_alignment_evidence",
        "qdrant_ingest": False,
    }
    (args.output_dir / "section_aware_manifest.jsonl").write_text("".join(json.dumps({"record_id": r["record_id"], "course_title": r["course_title"], "section_aware": r["section_aware"], "retrieval_status": r["retrieval_status"]}, ensure_ascii=False, sort_keys=True) + "\n" for r in results), encoding="utf-8")
    (args.output_dir / "retrieval_results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in results), encoding="utf-8")
    (args.output_dir / "review_queue.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in review_queue), encoding="utf-8")
    (args.output_dir / "retrieval_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

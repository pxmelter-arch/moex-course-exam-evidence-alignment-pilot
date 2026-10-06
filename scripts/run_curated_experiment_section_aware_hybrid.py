"""Run curated 600 section-aware experimental retrieval.

The packet is experimental-only. Content-bearing rows are retrieved; partial
rows are reported as abstention diagnostics / partial rows 不自動補值或 promotion。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
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
    normalize_text,
    outline_record_id,
)

CURATED_COMMIT = "a22f8e7"
CURATED_PATH = "release/curated_experiment_20261006/experiment_projection.jsonl"
EXPECTED_CURATED = 600
EXPECTED_OUTLINES = 542


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def git_show(repo: Path, commit: str, path: str) -> bytes:
    """Read a pinned Git path / 讀取 pinned Git path。"""
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"])


def as_text(value: Any) -> str:
    """Convert a value to text / 轉成文字。"""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def extract_section(text: str, starts: tuple[str, ...], stops: tuple[str, ...]) -> str:
    """Extract a labeled section conservatively / 保守擷取標籤 section。"""
    if not text:
        return ""
    start_pattern = "|".join(re.escape(item) for item in starts)
    stop_pattern = "|".join(re.escape(item) for item in stops)
    match = re.search(rf"(?:{start_pattern})", text, flags=re.IGNORECASE)
    if not match:
        return ""
    tail = text[match.end():]
    stop = re.search(rf"(?:{stop_pattern})", tail, flags=re.IGNORECASE)
    return tail[: stop.start()] if stop else tail


def curated_views(row: dict[str, Any]) -> dict[str, Any]:
    """Build contamination-aware views / 建立污染感知的 views。"""
    fields = row.get("syllabus_fields") or {}
    objective_blob = as_text(fields.get("objectives"))
    full_content = as_text(row.get("content_text"))
    outline = extract_section(
        objective_blob,
        ("內容綱要", "Course Outline", "課程大綱"),
        ("備註", "Note", "教學進度", "Course schedule", "自編教材", "Self-compiled"),
    )
    objectives = extract_section(
        objective_blob,
        ("課程目標", "Course objectives"),
        ("內容綱要", "Course Outline", "備註", "Note"),
    )
    schedule = extract_section(
        objective_blob,
        ("教學進度", "Course schedule"),
        ("自編教材", "Self-compiled", "符合智財", "Compliance"),
    )
    # Fallback only for fields that are empty; never silently fill missing data.
    if not outline:
        outline = as_text(fields.get("outline"))
    topic_text = "\n".join(x for x in (outline, objectives, schedule) if x)
    content_text = "\n".join(x for x in (objectives, outline, schedule) if x)
    return {
        "raw_content_sections": row.get("content_sections"),
        "raw_syllabus_field_names": sorted(fields),
        "source_content_status": row.get("content_status"),
        "section_presence": {
            "objectives": bool(objectives),
            "outline": bool(outline),
            "schedule": bool(schedule),
        },
        "topic_text": topic_text,
        "content_text": content_text,
        "raw_content_chars": row.get("content_chars"),
        "parser_fallback_outline": not bool(extract_section(objective_blob, ("內容綱要", "Course Outline", "課程大綱"), ("備註", "Note", "教學進度", "Course schedule", "自編教材", "Self-compiled"))),
        "full_content_available": bool(full_content),
    }


def score_rows(rows: list[dict[str, Any]], outlines: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Score content-bearing rows / 對有內容 records 評分。"""
    outline_fields = [
        {name: as_text(item.get(name)) for name in ("subject_name", "core_knowledge", "outline", "remarks")}
        for item in outlines
    ]
    for item, original in zip(outline_fields, outlines):
        original["outline_record_id"] = outline_record_id(original)
    vectors = {}
    for name in ("subject_name", "core_knowledge", "outline", "remarks"):
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
        vectors[name] = (vectorizer, vectorizer.fit_transform([normalize_text(x[name]) for x in outline_fields]))
    docs = [
        " ".join([x["subject_name"] * 2, x["core_knowledge"] * 2, x["outline"] * 2, x["remarks"]])
        for x in outline_fields
    ]
    tokenized, df, avg_len = build_bm25(docs)
    subject_counts = Counter(normalize_text(x["subject_name"]) for x in outline_fields)
    results = []
    counts = {"exact": 0, "ambiguous": 0, "weak": 0}
    for row in rows:
        view = curated_views(row)
        title = as_text(row.get("course_title"))
        title_query = normalize_text(" ".join((title, as_text(row.get("department")))))
        topic_query = normalize_text(view["topic_text"])
        content_query = normalize_text(view["content_text"])
        title_sim = cosine_similarity(vectors["subject_name"][1], vectors["subject_name"][0].transform([title_query])).ravel()
        core_sim = cosine_similarity(vectors["core_knowledge"][1], vectors["core_knowledge"][0].transform([topic_query])).ravel()
        outline_sim = cosine_similarity(vectors["outline"][1], vectors["outline"][0].transform([topic_query])).ravel()
        remarks_sim = cosine_similarity(vectors["remarks"][1], vectors["remarks"][0].transform([content_query])).ravel()
        bm25 = np.asarray(bm25_scores(content_query, tokenized, df, avg_len), dtype=float)
        def scale(values: np.ndarray) -> np.ndarray:
            return values / values.max() if values.size and values.max() > 0 else np.zeros_like(values)
        identity = np.array([float(normalize_text(x["subject_name"]) == normalize_text(title)) for x in outline_fields])
        title_scaled = np.maximum(scale(title_sim), identity)
        topic = 0.6 * scale(core_sim) + 0.4 * scale(outline_sim)
        hybrid = 0.30 * identity + 0.20 * title_scaled + 0.20 * topic + 0.20 * scale(bm25) + 0.10 * scale(remarks_sim)
        ranked = sorted(range(len(outlines)), key=lambda i: (-float(hybrid[i]), i))[:TOP_K]
        candidates = []
        for rank, index in enumerate(ranked):
            margin = float(hybrid[index] - hybrid[ranked[rank + 1]]) if rank + 1 < len(ranked) else float(hybrid[index])
            exact = bool(identity[index])
            duplicate = subject_counts[normalize_text(outline_fields[index]["subject_name"])] > 1
            status = "exact" if exact and not duplicate and float(hybrid[index]) >= 0.55 else ("ambiguous" if exact or margin < 0.05 or float(hybrid[index]) >= 0.35 else "weak")
            candidates.append({
                "rank": rank + 1,
                "outline_record_id": outlines[index]["outline_record_id"],
                "subject_name": outlines[index].get("subject_name"),
                "candidate_status": status,
                "exact_title_match": exact,
                "component_scores": {
                    "title_identity": round(float(identity[index]), 6),
                    "title_similarity": round(float(title_scaled[index]), 6),
                    "topic_score": round(float(topic[index]), 6),
                    "core_knowledge_score": round(float(scale(core_sim)[index]), 6),
                    "outline_topic_score": round(float(scale(outline_sim)[index]), 6),
                    "content_bm25_score": round(float(scale(bm25)[index]), 6),
                    "remarks_score": round(float(scale(remarks_sim)[index]), 6),
                    "hybrid_score": round(float(hybrid[index]), 6),
                },
            })
        top_status = candidates[0]["candidate_status"]
        counts[top_status] += 1
        results.append({
            "structured_id": row.get("structured_id"),
            "school_id": row.get("school_id"),
            "course_title": title,
            "content_status": row.get("content_status"),
            "source_record_status": row.get("source_record_status"),
            "provenance_status": row.get("provenance_status"),
            "release_status": row.get("release_status"),
            "section_aware": view,
            "retrieval_status": "candidate_only",
            "candidates": candidates,
        })
    return results, counts


def main() -> int:
    """Run curated experimental retrieval / 執行 curated 實驗 retrieval。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    curated = [json.loads(line) for line in git_show(args.source_repo, CURATED_COMMIT, CURATED_PATH).decode().splitlines() if line.strip()]
    outlines = json.loads(git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH))
    if len(curated) != EXPECTED_CURATED or len(outlines) != EXPECTED_OUTLINES:
        raise SystemExit("curated or outline scope mismatch")
    content = [row for row in curated if row.get("content_status") == "content_bearing"]
    partial = [row for row in curated if row.get("content_status") == "partial"]
    results, status_counts = score_rows(content, outlines)
    partial_queue = [{
        "structured_id": row.get("structured_id"),
        "school_id": row.get("school_id"),
        "course_title": row.get("course_title"),
        "content_status": row.get("content_status"),
        "content_chars": row.get("content_chars"),
        "abstention_reason": "partial_content_status",
        "retrieval_status": "abstained_by_default",
        "promotion_status": "blocked",
    } for row in partial]
    report = {
        "experiment": "curated_600_section_aware_hybrid_retrieval_v1",
        "status": "pass",
        "curated_commit": CURATED_COMMIT,
        "curated_path": CURATED_PATH,
        "curated_records": len(curated),
        "content_bearing_records": len(content),
        "partial_records": len(partial),
        "outline_commit": OUTLINE_COMMIT,
        "outline_path": OUTLINE_PATH,
        "outline_records": len(outlines),
        "retrieval_records": len(results),
        "top_candidate_status_counts": status_counts,
        "partial_abstention_count": len(partial_queue),
        "retrieval_status": "candidate_only",
        "promotion_status": "blocked_experimental_only",
        "qdrant_ingest": False,
        "weights": {"title_identity": 0.30, "title_similarity": 0.20, "topic_score": 0.20, "content_bm25": 0.20, "remarks": 0.10},
        "topic_weights": {"core_knowledge": 0.60, "outline": 0.40},
    }
    (args.output_dir / "retrieval_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "content_bearing_results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in results), encoding="utf-8")
    (args.output_dir / "partial_abstention_queue.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in partial_queue), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

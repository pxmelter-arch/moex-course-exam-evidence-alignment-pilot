"""Compare original top-50 and identity-expanded formal candidate pools.

The scoring and local embedding configuration match Phase 2.6. Only the
candidate pool changes / 僅比較 candidate pool，不改變 truth 或 promotion。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_phase2_1_course_outline_retrieval import OUTLINE_COMMIT, OUTLINE_PATH, git_show, normalize_text, outline_record_id  # noqa: E402
from run_phase2_6_formal_chunk_dense_hybrid_evidence import (  # noqa: E402
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    FORMAL_PROJECTION_COMMIT,
    FORMAL_PROJECTION_PATH,
    MODEL_PATH,
    MODEL_NAME,
    chunks_for_section,
    section_aware_views,
)

RESULT_PATH = "experiments/phase2_6_formal_chunk_dense_hybrid_evidence_v1/course_chunk_hybrid_results.jsonl"
BRIDGE_PATH = "experiments/phase2_7_formal_identity_bridge_v1/identity_bridge_candidates.jsonl"


def text(value: Any) -> str:
    """Convert values to text / 統一轉成文字。"""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def scale(values: np.ndarray) -> np.ndarray:
    """Scale scores / 缩放分數。"""
    values = np.asarray(values, dtype=float)
    return values / values.max() if values.size and values.max() > 0 else np.zeros_like(values)


def make_chunks(record: dict[str, Any]) -> list[str]:
    """Make text chunks / 建立文字 chunks。"""
    fields = record.get("syllabus_fields") or {}
    chunks = []
    for field in ("course_description", "outline", "objectives", "assessment", "textbook", "prerequisite"):
        for chunk in chunks_for_section(text(fields.get(field))):
            chunks.append(chunk)
    return chunks


def candidate_status(index: int, ranked: list[int], hybrid: np.ndarray, exact_title: np.ndarray, outlines: list[dict[str, Any]]) -> str:
    """Classify candidate status / 分類 candidate status。"""
    next_score = float(hybrid[ranked[1]]) if len(ranked) > 1 else float(hybrid[index])
    margin = float(hybrid[index]) - next_score
    duplicate = sum(normalize_text(item.get("subject_name")) == normalize_text(outlines[index].get("subject_name")) for item in outlines) > 1
    if exact_title[index] and not duplicate and hybrid[index] >= 0.55:
        return "exact"
    if exact_title[index] or margin < 0.05 or hybrid[index] >= 0.35:
        return "ambiguous"
    return "weak"


def rank_pool(pool: set[int], hybrid: np.ndarray, exact_title: np.ndarray, outlines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank a candidate pool / 排序 candidate pool。"""
    ranked = sorted(pool, key=lambda i: (-float(hybrid[i]), i))[:10]
    output = []
    for rank, index in enumerate(ranked):
        next_score = float(hybrid[ranked[rank + 1]]) if rank + 1 < len(ranked) else float(hybrid[index])
        output.append({
            "rank": rank + 1,
            "outline_record_id": outlines[index]["outline_record_id"],
            "subject_name": outlines[index].get("subject_name"),
            "candidate_status": candidate_status(index, ranked, hybrid, exact_title, outlines),
            "title_exact": bool(exact_title[index]),
            "hybrid_score": round(float(hybrid[index]), 8),
            "margin": round(float(hybrid[index]) - next_score, 8),
        })
    return output


def main() -> int:
    """Run paired comparison / 執行 paired comparison。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    formal = json.loads(git_show(args.source_repo, FORMAL_PROJECTION_COMMIT, FORMAL_PROJECTION_PATH))
    outlines = json.loads(git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH))
    original_rows = [json.loads(line) for line in (ROOT / RESULT_PATH).read_text(encoding="utf-8").splitlines()]
    bridge_rows = [json.loads(line) for line in (ROOT / BRIDGE_PATH).read_text(encoding="utf-8").splitlines()]
    for outline in outlines:
        outline["outline_record_id"] = outline_record_id(outline)
    outline_index = {row["outline_record_id"]: i for i, row in enumerate(outlines)}
    docs = [" ".join(text(row.get(field)) for field in ("subject_name", "core_knowledge", "outline", "remarks")) for row in outlines]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
    outline_matrix = vectorizer.fit_transform([normalize_text(doc) for doc in docs])
    title_vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
    title_matrix = title_vectorizer.fit_transform([normalize_text(text(row.get("subject_name"))) for row in outlines])
    model = SentenceTransformer(str(MODEL_PATH), local_files_only=True, device="cuda" if __import__("torch").cuda.is_available() else "cpu")
    outline_embeddings = model.encode(docs, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    paired_rows = []
    recovery = []
    totals = {"original": {"top1_exact": 0, "top10_exact": 0, "ambiguous_top10": 0}, "expanded": {"top1_exact": 0, "top10_exact": 0, "ambiguous_top10": 0}}
    for record, original, bridge in zip(formal, original_rows, bridge_rows):
        title = normalize_text(record.get("course_title"))
        exact_title = np.array([float(normalize_text(row.get("subject_name")) == title) for row in outlines])
        views = section_aware_views(record)
        query = normalize_text(" ".join((text(record.get("course_title")), views["topic_text"], views["content_text"])))
        lexical_course = scale(cosine_similarity(outline_matrix, vectorizer.transform([query])).ravel())
        title_scores = scale(cosine_similarity(title_matrix, title_vectorizer.transform([normalize_text(text(record.get("course_title")))] )).ravel())
        chunks = make_chunks(record) or [views["content_text"] or views["topic_text"] or text(record.get("course_title"))]
        chunk_embeddings = model.encode(chunks, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        dense_matrix = np.asarray(chunk_embeddings) @ np.asarray(outline_embeddings).T
        course_dense = np.mean(chunk_embeddings, axis=0) @ np.asarray(outline_embeddings).T
        chunk_lexical = cosine_similarity(outline_matrix, vectorizer.transform([normalize_text(chunk) for chunk in chunks]))
        max_chunk_lexical = np.max(chunk_lexical, axis=1)
        max_chunk_dense = np.max(dense_matrix, axis=0)
        lexical = scale(0.65 * lexical_course + 0.35 * scale(max_chunk_lexical))
        dense = scale(0.50 * scale(course_dense) + 0.50 * scale(max_chunk_dense))
        hybrid = 0.20 * exact_title + 0.40 * lexical + 0.40 * dense
        original_ids = set(original.get("course_candidate_outline_record_ids", []))
        expanded_ids = set(bridge.get("expanded_candidate_outline_record_ids", []))
        original_pool = {outline_index[i] for i in original_ids if i in outline_index}
        expanded_pool = {outline_index[i] for i in expanded_ids if i in outline_index}
        original_ranked = rank_pool(original_pool, hybrid, exact_title, outlines)
        expanded_ranked = rank_pool(expanded_pool, hybrid, exact_title, outlines)
        original_top10 = any(row["title_exact"] for row in original_ranked)
        expanded_top10 = any(row["title_exact"] for row in expanded_ranked)
        original_top1 = bool(original_ranked and original_ranked[0]["title_exact"])
        expanded_top1 = bool(expanded_ranked and expanded_ranked[0]["title_exact"])
        original_ambiguous = sum(row["candidate_status"] == "ambiguous" for row in original_ranked)
        expanded_ambiguous = sum(row["candidate_status"] == "ambiguous" for row in expanded_ranked)
        for key, top1, top10, ambiguous in (("original", original_top1, original_top10, original_ambiguous), ("expanded", expanded_top1, expanded_top10, expanded_ambiguous)):
            totals[key]["top1_exact"] += int(top1)
            totals[key]["top10_exact"] += int(top10)
            totals[key]["ambiguous_top10"] += ambiguous
        if not original_top10 and expanded_top10:
            recovery.append({"record_id": original["record_id"], "course_title": record.get("course_title"), "expanded_exact_candidates": [row for row in expanded_ranked if row["title_exact"]]})
        paired_rows.append({"record_id": original["record_id"], "course_title": record.get("course_title"), "original_pool_size": len(original_pool), "expanded_pool_size": len(expanded_pool), "original": original_ranked, "expanded": expanded_ranked, "recovered_top10": not original_top10 and expanded_top10, "ambiguous_delta": expanded_ambiguous - original_ambiguous})
    report = {"experiment": "phase2_8_formal_identity_expanded_pool_comparison_v1", "formal_records": len(formal), "outline_records": len(outlines), "original_pool": {"definition": "phase2_6 course-level top-50", "metrics": totals["original"]}, "expanded_pool": {"definition": "phase2_6 pool + exact identity + top-5 machine alias candidates", "metrics": totals["expanded"]}, "gate_miss_recovery": {"count": len(recovery), "records": recovery}, "ambiguous_delta": totals["expanded"]["ambiguous_top10"] - totals["original"]["ambiguous_top10"], "promotion_status": "blocked", "formal_alignment": "not_started", "qdrant_ingest": False, "embedding": {"model": MODEL_NAME, "local_only": True, "chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP}}
    (args.output_dir / "comparison_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "paired_comparison.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in paired_rows), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

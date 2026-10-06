"""Run the formal 176 course-to-outline chunk/dense/evidence pipeline.

All embeddings are local-only. The output is candidate evidence, not ground truth.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_phase2_1_course_outline_retrieval import (  # noqa: E402
    OUTLINE_COMMIT,
    OUTLINE_PATH,
    git_show,
    normalize_text,
    outline_record_id,
)
from run_phase2_4_section_aware_hybrid_retrieval import (  # noqa: E402
    FORMAL_PROJECTION_COMMIT,
    FORMAL_PROJECTION_PATH,
    section_aware_views,
)

EXPECTED_FORMAL = 176
EXPECTED_OUTLINES = 542
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
MODEL_PATH = Path("/home/aelix/.hermes/profiles/ml-expert/home/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/snapshots/7999e1d3359715c523056ef9478215996d62a620")
COURSE_CANDIDATE_K = 50
OUTPUT_K = 10
CHUNK_SIZE = 420
CHUNK_OVERLAP = 60


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def as_text(value: Any) -> str:
    """Convert value to text / 統一轉成文字。"""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def chunks_for_section(text: str) -> list[str]:
    """Split text into bounded overlapping chunks / 建立 bounded chunks。"""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = [part.strip() for part in re.split(r"(?<=[。！？.!?；;])\s*", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > CHUNK_SIZE:
            chunks.append(current)
            current = current[-CHUNK_OVERLAP:]
        current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks or [text[:CHUNK_SIZE]]


def make_chunks(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Create provenance-preserving section chunks / 建立保留 provenance 的 section chunks。"""
    fields = record.get("syllabus_fields") or {}
    chunks: list[dict[str, Any]] = []
    for field in ("course_description", "outline", "objectives", "assessment", "textbook", "prerequisite"):
        raw = as_text(fields.get(field))
        for index, chunk in enumerate(chunks_for_section(raw)):
            chunks.append({
                "chunk_id": f"{record.get('record_id') or record.get('candidate_id') or record.get('course_title')}-{field}-{index:03d}",
                "record_id": record.get("record_id") or record.get("candidate_id"),
                "course_title": record.get("course_title"),
                "section": field,
                "section_index": index,
                "text": chunk,
                "source_path": FORMAL_PROJECTION_PATH,
                "source_commit": FORMAL_PROJECTION_COMMIT,
                "raw_sha256": record.get("raw_sha256"),
                "evidence_span": chunk,
            })
    return chunks


def scale(values: np.ndarray) -> np.ndarray:
    """Scale scores / 將分數縮放。"""
    values = np.asarray(values, dtype=float)
    return values / values.max() if values.size and values.max() > 0 else np.zeros_like(values)


def main() -> int:
    """Run formal chunk/dense/hybrid pipeline / 執行 formal pipeline。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    formal = json.loads(git_show(args.source_repo, FORMAL_PROJECTION_COMMIT, FORMAL_PROJECTION_PATH))
    outlines = json.loads(git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH))
    if len(formal) != EXPECTED_FORMAL or len(outlines) != EXPECTED_OUTLINES:
        raise SystemExit("scope mismatch")
    if any(row.get("formal_gate") != "passed" for row in formal):
        raise SystemExit("formal gate mismatch")

    outline_docs = []
    for outline in outlines:
        outline["outline_record_id"] = outline_record_id(outline)
        outline_docs.append(" ".join(as_text(outline.get(field)) for field in ("subject_name", "core_knowledge", "outline", "remarks")))
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
    outline_matrix = vectorizer.fit_transform([normalize_text(doc) for doc in outline_docs])
    title_vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
    title_matrix = title_vectorizer.fit_transform([normalize_text(as_text(item.get("subject_name"))) for item in outlines])

    if not MODEL_PATH.exists():
        raise SystemExit(f"local embedding model missing: {MODEL_PATH}")
    model = SentenceTransformer(str(MODEL_PATH), local_files_only=True, device="cuda" if __import__("torch").cuda.is_available() else "cpu")
    outline_embeddings = model.encode(outline_docs, normalize_embeddings=True, batch_size=32, show_progress_bar=False)

    all_chunks: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    exact_top1 = 0
    exact_top10 = 0
    status_counts = {"exact": 0, "ambiguous": 0, "weak": 0}
    for record_index, record in enumerate(formal):
        record["record_id"] = record.get("record_id") or record.get("candidate_id") or f"formal-{record_index:03d}"
        chunks = make_chunks(record)
        all_chunks.extend(chunks)
        views = section_aware_views(record)
        course_query = normalize_text(" ".join((as_text(record.get("course_title")), views["topic_text"], views["content_text"])))
        course_lexical = scale(cosine_similarity(outline_matrix, vectorizer.transform([course_query])).ravel())
        title_query = normalize_text(as_text(record.get("course_title")))
        title_scores = scale(cosine_similarity(title_matrix, title_vectorizer.transform([title_query])).ravel())
        exact_title = np.array([float(normalize_text(item.get("subject_name")) == title_query) for item in outlines])
        chunk_texts = [chunk["text"] for chunk in chunks] or [views["content_text"] or views["topic_text"] or as_text(record.get("course_title"))]
        chunk_embeddings = model.encode(chunk_texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        chunk_dense = np.asarray(chunk_embeddings) @ np.asarray(outline_embeddings).T
        course_dense = np.mean(chunk_embeddings, axis=0) @ np.asarray(outline_embeddings).T
        chunk_lexical = cosine_similarity(outline_matrix, vectorizer.transform([normalize_text(chunk) for chunk in chunk_texts]))
        max_chunk_lexical = np.max(chunk_lexical, axis=1) if chunk_lexical.size else np.zeros(len(outlines))
        max_chunk_dense_index = np.argmax(chunk_dense, axis=0) if chunk_dense.size else np.zeros(len(outlines), dtype=int)
        max_chunk_dense = np.max(chunk_dense, axis=0) if chunk_dense.size else np.zeros(len(outlines))
        lexical = scale(0.65 * course_lexical + 0.35 * scale(max_chunk_lexical))
        dense = scale(0.50 * scale(course_dense) + 0.50 * scale(max_chunk_dense))
        hybrid = 0.20 * exact_title + 0.40 * lexical + 0.40 * dense
        candidate_indices = set(np.argsort(-course_lexical)[:COURSE_CANDIDATE_K].tolist())
        ranked = sorted(candidate_indices, key=lambda i: (-float(hybrid[i]), i))[:OUTPUT_K]
        candidates = []
        top10_has_exact = False
        for rank, index in enumerate(ranked):
            next_score = float(hybrid[ranked[rank + 1]]) if rank + 1 < len(ranked) else float(hybrid[index])
            margin = float(hybrid[index]) - next_score
            duplicate = sum(normalize_text(item.get("subject_name")) == normalize_text(outlines[index].get("subject_name")) for item in outlines) > 1
            status = "exact" if exact_title[index] and not duplicate and hybrid[index] >= 0.55 else ("ambiguous" if exact_title[index] or margin < 0.05 or hybrid[index] >= 0.35 else "weak")
            if rank == 0:
                status_counts[status] += 1
            if rank == 0 and exact_title[index]:
                exact_top1 += 1
            if exact_title[index]:
                top10_has_exact = True
            chunk_index = int(max_chunk_dense_index[index]) if chunks else 0
            evidence = chunks[chunk_index] if chunks else {"section": "fallback", "text": chunk_texts[chunk_index]}
            candidates.append({
                "rank": rank + 1,
                "outline_record_id": outlines[index]["outline_record_id"],
                "subject_name": outlines[index].get("subject_name"),
                "candidate_status": status,
                "course_candidate_stage": "top_50_course_level",
                "evidence_span": {
                    "chunk_id": evidence.get("chunk_id"),
                    "section": evidence.get("section"),
                    "section_index": evidence.get("section_index"),
                    "text": evidence.get("text"),
                    "source_path": evidence.get("source_path", FORMAL_PROJECTION_PATH),
                    "source_commit": evidence.get("source_commit", FORMAL_PROJECTION_COMMIT),
                    "raw_sha256": evidence.get("raw_sha256"),
                },
                "component_scores": {
                    "title_identity": round(float(exact_title[index]), 6),
                    "lexical_course_and_chunk": round(float(lexical[index]), 6),
                    "dense_course_and_chunk": round(float(dense[index]), 6),
                    "chunk_topic_coverage": round(float(max_chunk_lexical[index]), 6),
                    "hybrid_score": round(float(hybrid[index]), 6),
                    "margin": round(margin, 6),
                },
            })
        result_rows.append({
            "record_id": record["record_id"],
            "school_id": record.get("school_id"),
            "course_title": record.get("course_title"),
            "formal_gate": record.get("formal_gate"),
            "chunk_count": len(chunks),
            "course_candidate_count": len(candidate_indices),
            "candidates": candidates,
        })
        if top10_has_exact:
            exact_top10 += 1
        if (record_index + 1) % 25 == 0:
            print(f"processed {record_index + 1}/{len(formal)}", file=sys.stderr)

    report = {
        "experiment": "phase2_6_formal_course_chunk_dense_hybrid_evidence_v1",
        "status": "pass",
        "formal_records": len(formal),
        "formal_projection_commit": FORMAL_PROJECTION_COMMIT,
        "formal_projection_path": FORMAL_PROJECTION_PATH,
        "outline_records": len(outlines),
        "outline_commit": OUTLINE_COMMIT,
        "outline_path": OUTLINE_PATH,
        "chunk_count": len(all_chunks),
        "course_candidate_k": COURSE_CANDIDATE_K,
        "output_k": OUTPUT_K,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding": {"model": MODEL_NAME, "local_path": str(MODEL_PATH), "local_only": True, "device": str(model.device), "normalize_embeddings": True},
        "metrics": {"top1_exact_subject": exact_top1, "top10_exact_subject": exact_top10, "top_candidate_status_counts": status_counts},
        "retrieval_status": "candidate_only",
        "evidence_span_status": "provenance_preserved",
        "formal_alignment": "not_started",
        "promotion_status": "blocked_pending_alignment_evidence",
        "qdrant_ingest": False,
    }
    (args.output_dir / "pipeline_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "section_chunks.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_chunks), encoding="utf-8")
    (args.output_dir / "course_chunk_hybrid_results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in result_rows), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

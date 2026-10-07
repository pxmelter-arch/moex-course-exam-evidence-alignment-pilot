"""Run topic matching, bidirectional coverage, and coverage reranking.

This is a local-only diagnostic experiment. Topic matches are machine evidence,
not human alignment truth / 僅作 machine evidence。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]
REFINE = ROOT / "experiments/phase3_retrieval_refinement_v1"
PAIRED = ROOT / "experiments/phase2_8_identity_expanded_pool_comparison_v1/paired_comparison.jsonl"
FORMAL_COMMIT = "8922edc"
FORMAL_PATH = "output/canonical/round26_formal_syllabus_projection.json"
OUTLINE_COMMIT = "4cb1b5a7155a052450354cdff2e7e00a66728b89"
OUTLINE_PATH = "data/raw/exam_outlines/exam_outline_catalog/output/exam_outline_catalog.json"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"


def git_json(repo: Path, commit: str, path: str) -> Any:
    """Read pinned JSON / 讀取 pinned JSON。"""
    return json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"]))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL / 讀取 JSONL。"""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def outline_id(row: dict[str, Any]) -> str:
    """Recreate deterministic outline ID / 重建 deterministic outline ID。"""
    import hashlib
    payload = {key: row.get(key) for key in ("subject_name", "type", "applicable_exams", "core_knowledge", "outline", "remarks", "source")}
    return "OUT-" + hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]


def main() -> int:
    """Run topic matching and coverage reranking / 執行 topic matching。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--thresholds", default="0.30,0.42,0.55,0.65")
    args = parser.parse_args()
    thresholds = [float(value) for value in args.thresholds.split(",") if value.strip()]
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    syllabus = load_jsonl(REFINE / "syllabus_atomic_topic_chunks.jsonl")
    outline_items = load_jsonl(REFINE / "outline_atomic_items.jsonl")
    paired = load_jsonl(PAIRED)
    outlines = git_json(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH)
    subject_by_id = {outline_id(row): row.get("subject_name") for row in outlines}
    items_by_outline: dict[str, list[int]] = defaultdict(list)
    for index, item in enumerate(outline_items):
        items_by_outline[item["outline_record_id"]].append(index)
    chunks_by_record: dict[str, list[int]] = defaultdict(list)
    for index, chunk in enumerate(syllabus):
        chunks_by_record[chunk["record_id"]].append(index)
    all_texts = [row["text"] for row in syllabus] + [row["text"] for row in outline_items]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=1, max_features=100000)
    tfidf = vectorizer.fit_transform(all_texts)
    syllabus_tfidf = tfidf[: len(syllabus)]
    outline_tfidf = tfidf[len(syllabus) :]
    model = SentenceTransformer(MODEL_NAME, local_files_only=True, device="cuda" if __import__("torch").cuda.is_available() else "cpu")
    syllabus_emb = model.encode([row["text"] for row in syllabus], normalize_embeddings=True, batch_size=64, show_progress_bar=False)
    outline_emb = model.encode([row["text"] for row in outline_items], normalize_embeddings=True, batch_size=64, show_progress_bar=False)
    result_rows = []
    top1 = top10 = baseline_top1 = baseline_top10 = 0
    status_counts = Counter()
    match_rows = []
    for paired_row in paired:
        record_id = paired_row["record_id"]
        chunk_idx = chunks_by_record[record_id]
        candidates = []
        for candidate in paired_row["expanded"]:
            oid = candidate["outline_record_id"]
            item_idx = items_by_outline.get(oid, [])
            if not item_idx or not chunk_idx:
                lexical_max = dense_max = 0.0
                coverage_by_threshold = {str(threshold): {"syllabus_to_outline": 0.0, "outline_to_syllabus": 0.0, "bidirectional": 0.0} for threshold in thresholds}
                s_to_o = o_to_s = 0.0
                matches = []
            else:
                lexical = (syllabus_tfidf[chunk_idx] @ outline_tfidf[item_idx].T).toarray()
                dense = np.asarray(syllabus_emb[chunk_idx] @ outline_emb[item_idx].T)
                combined = (lexical + dense) / 2.0
                lexical_max = float(lexical.max())
                dense_max = float(dense.max())
                coverage_by_threshold = {}
                for threshold in thresholds:
                    threshold_s_to_o = float(np.mean(combined.max(axis=0) >= threshold))
                    threshold_o_to_s = float(np.mean(combined.max(axis=1) >= threshold))
                    coverage_by_threshold[str(threshold)] = {"syllabus_to_outline": round(threshold_s_to_o, 6), "outline_to_syllabus": round(threshold_o_to_s, 6), "bidirectional": round((threshold_s_to_o + threshold_o_to_s) / 2.0, 6)}
                s_to_o = coverage_by_threshold[str(0.42)]["syllabus_to_outline"] if str(0.42) in coverage_by_threshold else coverage_by_threshold[str(thresholds[0])]["syllabus_to_outline"]
                o_to_s = coverage_by_threshold[str(0.42)]["outline_to_syllabus"] if str(0.42) in coverage_by_threshold else coverage_by_threshold[str(thresholds[0])]["outline_to_syllabus"]
                matches = []
                threshold_for_matches = 0.42 if 0.42 in thresholds else thresholds[0]
                for left, right in zip(*np.where(combined >= threshold_for_matches)):
                    matches.append({"syllabus_chunk_id": syllabus[chunk_idx[left]]["chunk_id"], "outline_item_id": outline_items[item_idx[right]]["item_id"], "score": round(float(combined[left, right]), 6)})
                matches = sorted(matches, key=lambda x: x["score"], reverse=True)[:5]
            coverage = (s_to_o + o_to_s) / 2.0
            rerank_score = 0.20 * float(candidate["hybrid_score"]) + 0.25 * lexical_max + 0.25 * dense_max + 0.30 * coverage
            candidates.append({**candidate, "lexical_topic_max": round(lexical_max, 6), "dense_topic_max": round(dense_max, 6), "syllabus_to_outline_coverage": round(s_to_o, 6), "outline_to_syllabus_coverage": round(o_to_s, 6), "bidirectional_topic_coverage": round(coverage, 6), "coverage_by_threshold": coverage_by_threshold, "coverage_reranked_score": round(rerank_score, 6)})
            match_rows.append({"record_id": record_id, "outline_record_id": oid, "subject_name": subject_by_id.get(oid), "coverage_by_threshold": coverage_by_threshold, "syllabus_to_outline_coverage": round(s_to_o, 6), "outline_to_syllabus_coverage": round(o_to_s, 6), "matches": matches})
        ranked = sorted(candidates, key=lambda row: (-row["coverage_reranked_score"], row["outline_record_id"]))
        for rank, candidate in enumerate(ranked, 1):
            candidate["coverage_rank"] = rank
        baseline = paired_row["expanded"]
        exact_subject = paired_row["course_title"]
        if baseline and baseline[0]["subject_name"] == exact_subject:
            baseline_top1 += 1
        if any(row["subject_name"] == exact_subject for row in baseline):
            baseline_top10 += 1
        if ranked and ranked[0]["subject_name"] == exact_subject:
            top1 += 1
        if any(row["subject_name"] == exact_subject for row in ranked[:10]):
            top10 += 1
        for candidate in ranked:
            status_counts[candidate["candidate_status"]] += 1
        result_rows.append({"record_id": record_id, "course_title": paired_row["course_title"], "candidate_count": len(ranked), "candidates": ranked, "coverage_threshold": 0.42, "machine_inference_only": True})
    report = {"experiment": "phase3_topic_matching_bidirectional_coverage_reranking_v1", "formal_records": len(paired), "syllabus_atomic_chunks": len(syllabus), "outline_atomic_items": len(outline_items), "candidate_rows": len(result_rows) * 10, "embedding": {"model": MODEL_NAME, "local_only": True, "normalized": True}, "coverage": {"threshold": 0.42, "directional": True}, "baseline_expanded": {"top1_exact": baseline_top1, "top10_exact": baseline_top10}, "coverage_reranked": {"top1_exact": top1, "top10_exact": top10}, "delta": {"top1": top1 - baseline_top1, "top10": top10 - baseline_top10}, "status_counts": dict(status_counts), "formal_alignment": "not_started", "promotion_status": "blocked", "qdrant_ingest": False}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "topic_coverage_reranking_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "coverage_reranked_results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in result_rows), encoding="utf-8")
    (args.output_dir / "topic_match_evidence.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in match_rows), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

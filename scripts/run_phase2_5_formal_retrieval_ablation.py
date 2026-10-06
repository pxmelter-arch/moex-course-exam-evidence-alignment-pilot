"""Run formal 176 retrieval ablation comparison.

This experiment stays on the formal syllabus projection and compares title,
topic, content, and hybrid signals without promotion.
"""
from __future__ import annotations

import argparse
import json
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


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def text(value: Any) -> str:
    """Convert value to text / 統一轉成文字。"""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def scale(values: np.ndarray) -> np.ndarray:
    """Scale scores to [0, 1] / 將分數縮放至 [0, 1]。"""
    values = np.asarray(values, dtype=float)
    return values / values.max() if values.size and values.max() > 0 else np.zeros_like(values)


def main() -> int:
    """Run ablation comparison / 執行 ablation comparison。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    formal = json.loads(git_show(args.source_repo, FORMAL_PROJECTION_COMMIT, FORMAL_PROJECTION_PATH))
    outlines = json.loads(git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH))
    if len(formal) != EXPECTED_FORMAL or len(outlines) != EXPECTED_OUTLINES:
        raise SystemExit("scope mismatch")
    outline_rows = [{name: text(item.get(name)) for name in ("subject_name", "core_knowledge", "outline", "remarks")} for item in outlines]
    for item, row in zip(outlines, outline_rows):
        item["outline_record_id"] = outline_record_id(item)
    vectors = {}
    for name in ("subject_name", "core_knowledge", "outline", "remarks"):
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
        vectors[name] = (vectorizer, vectorizer.fit_transform([normalize_text(row[name]) for row in outline_rows]))
    docs = [" ".join([row["subject_name"] * 2, row["core_knowledge"] * 2, row["outline"] * 2, row["remarks"]]) for row in outline_rows]
    tokenized, df, avg_len = build_bm25(docs)
    exact_counts = Counter(normalize_text(row["subject_name"]) for row in outline_rows)
    method_rows = {name: [] for name in ("title_identity", "topic_only", "content_topic_only", "section_hybrid")}
    result_rows = []
    for record in formal:
        views = section_aware_views(record)
        title = text(record.get("course_title"))
        title_query = normalize_text(" ".join((title, text(record.get("department_name")))))
        topic_query = normalize_text(views["topic_text"])
        content_query = normalize_text(views["content_text"])
        title_sim = scale(cosine_similarity(vectors["subject_name"][1], vectors["subject_name"][0].transform([title_query])).ravel())
        core_sim = scale(cosine_similarity(vectors["core_knowledge"][1], vectors["core_knowledge"][0].transform([topic_query])).ravel())
        outline_sim = scale(cosine_similarity(vectors["outline"][1], vectors["outline"][0].transform([topic_query])).ravel())
        remarks_sim = scale(cosine_similarity(vectors["remarks"][1], vectors["remarks"][0].transform([content_query])).ravel())
        bm25 = scale(np.asarray(bm25_scores(content_query, tokenized, df, avg_len), dtype=float))
        identity = np.array([float(normalize_text(row["subject_name"]) == normalize_text(title)) for row in outline_rows])
        title_signal = np.maximum(title_sim, identity)
        topic = 0.60 * core_sim + 0.40 * outline_sim
        methods = {
            "title_identity": identity,
            "topic_only": topic,
            "content_topic_only": 0.55 * topic + 0.35 * bm25 + 0.10 * remarks_sim,
            "section_hybrid": 0.30 * identity + 0.20 * title_signal + 0.20 * topic + 0.20 * bm25 + 0.10 * remarks_sim,
        }
        method_result = {"record_id": record.get("candidate_id"), "course_title": title, "methods": {}}
        for name, scores in methods.items():
            ranked = sorted(range(len(outlines)), key=lambda index: (-float(scores[index]), index))[:TOP_K]
            exact = [index for index in ranked if identity[index] == 1.0]
            method_rows[name].append({"top1_exact": bool(ranked and identity[ranked[0]] == 1.0), "top10_exact": bool(exact), "top1": outlines[ranked[0]].get("subject_name") if ranked else None})
            method_result["methods"][name] = {"top1": outlines[ranked[0]].get("subject_name") if ranked else None, "top1_exact": bool(ranked and identity[ranked[0]] == 1.0), "top10_exact": bool(exact), "top1_score": round(float(scores[ranked[0]]), 6) if ranked else 0.0}
        result_rows.append(method_result)

    summary = {}
    for name, rows in method_rows.items():
        summary[name] = {
            "query_count": len(rows),
            "top1_exact_subject": sum(row["top1_exact"] for row in rows),
            "top10_exact_subject": sum(row["top10_exact"] for row in rows),
        }
    report = {
        "experiment": "phase2_5_formal_retrieval_ablation_v1",
        "status": "pass",
        "formal_projection_commit": FORMAL_PROJECTION_COMMIT,
        "formal_projection_path": FORMAL_PROJECTION_PATH,
        "formal_records": len(formal),
        "outline_commit": OUTLINE_COMMIT,
        "outline_path": OUTLINE_PATH,
        "outline_records": len(outlines),
        "methods": summary,
        "candidate_only": True,
        "formal_alignment": "not_started",
        "promotion_status": "blocked_pending_alignment_evidence",
        "qdrant_ingest": False,
    }
    (args.output_dir / "ablation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "ablation_results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in result_rows), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

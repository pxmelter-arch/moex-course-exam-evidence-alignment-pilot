"""Run a bounded lexical course-to-exam-outline candidate retrieval experiment.

The formal course manifest contains course metadata and section names but not
syllabus full text. This runner therefore evaluates title/department queries
against the pinned normalized exam-outline catalog. Results are diagnostic
candidate retrieval, never truth or formal alignment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

FORMAL_COMMIT = "1f2a2e635d61e01b5788a3c8c5b66adeb5c7e9db"
FORMAL_PATH = "output/dataset/round26_formal_dataset_2026-10-02.json"
OUTLINE_COMMIT = "4cb1b5a7155a052450354cdff2e7e00a66728b89"
OUTLINE_PATH = "data/raw/exam_outlines/exam_outline_catalog/output/exam_outline_catalog.json"
EXPECTED_FORMAL = 176
EXPECTED_OUTLINES = 542
TOP_K = 10


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments / 解析命令列參數。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def git_show(repo: Path, commit: str, path: str) -> bytes:
    """Read an exact pinned Git object / 讀取固定 commit 的檔案。"""
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"])


def normalize_text(value: Any) -> str:
    """Normalize multilingual text without semantic imputation / 正規化文字。"""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = re.sub(r"\s+", "", text)
    return re.sub(r"[^\w\u3400-\u9fff]", "", text)


def char_ngrams(text: str, n: int = 2) -> list[str]:
    """Create deterministic character n-grams / 建立字元 n-gram。"""
    normalized = normalize_text(text)
    if len(normalized) <= n:
        return [normalized] if normalized else []
    return [normalized[i : i + n] for i in range(len(normalized) - n + 1)]


def outline_record_id(record: dict[str, Any]) -> str:
    """Create content-aware outline identity / 建立內容感知的大綱 identity。"""
    payload = {
        "subject_name": record.get("subject_name"),
        "type": record.get("type"),
        "applicable_exams": record.get("applicable_exams"),
        "core_knowledge": record.get("core_knowledge"),
        "outline": record.get("outline"),
        "remarks": record.get("remarks"),
        "source": record.get("source"),
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:20]
    return f"OUT-{digest}"


def document_text(record: dict[str, Any]) -> str:
    """Build outline retrieval document / 建立命題大綱檢索文件。"""
    parts = [record.get("subject_name", "")]
    parts.extend(record.get("core_knowledge", []))
    parts.extend(item.get("text", "") for item in record.get("outline", []))
    if record.get("remarks"):
        parts.append(record["remarks"])
    return " ".join(str(part) for part in parts if part)


def query_text(record: dict[str, Any]) -> str:
    """Build formal course query / 建立正式課程 query。"""
    return " ".join(
        str(record.get(field, ""))
        for field in ("course_title", "department_name")
        if record.get(field)
    )


def build_bm25(documents: list[str]) -> tuple[list[list[str]], dict[str, int], float]:
    """Build an in-memory BM25 index / 建立 BM25 index。"""
    tokenized = [char_ngrams(doc) for doc in documents]
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))
    average_length = sum(map(len, tokenized)) / max(len(tokenized), 1)
    return tokenized, dict(document_frequency), average_length


def bm25_scores(query: str, tokenized: list[list[str]], df: dict[str, int], avg_len: float) -> np.ndarray:
    """Score documents with BM25 / 使用 BM25 計算文件分數。"""
    query_tokens = Counter(char_ngrams(query))
    n_docs = len(tokenized)
    scores = np.zeros(n_docs, dtype=float)
    k1, b = 1.2, 0.75
    for index, tokens in enumerate(tokenized):
        counts = Counter(tokens)
        length = len(tokens)
        for term, query_tf in query_tokens.items():
            if term not in counts:
                continue
            idf = math.log(1 + (n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
            numerator = counts[term] * (k1 + 1)
            denominator = counts[term] + k1 * (1 - b + b * length / max(avg_len, 1e-9))
            scores[index] += idf * numerator / denominator * query_tf
    return scores


def ranked_indices(scores: np.ndarray, limit: int = TOP_K) -> list[int]:
    """Return deterministic top-ranked indices / 回傳穩定排序結果。"""
    return sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))[:limit]


def candidate_payload(index: int, score: float, outlines: list[dict[str, Any]]) -> dict[str, Any]:
    """Serialize one candidate / 序列化一個 candidate。"""
    record = outlines[index]
    return {
        "outline_record_id": record["outline_record_id"],
        "subject_name": record.get("subject_name"),
        "type": record.get("type"),
        "applicable_exams": record.get("applicable_exams", []),
        "score": round(float(score), 8),
        "source": record.get("source", []),
    }


def main() -> int:
    """Run experiment and write reproducible artifacts / 執行實驗。"""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    formal_raw = git_show(args.source_repo, FORMAL_COMMIT, FORMAL_PATH)
    outline_raw = git_show(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH)
    formal_doc = json.loads(formal_raw)
    formal_records = formal_doc["records"]
    outlines = json.loads(outline_raw)
    if len(formal_records) != EXPECTED_FORMAL or len(outlines) != EXPECTED_OUTLINES:
        raise SystemExit("pinned input record count mismatch")

    for record in outlines:
        record["outline_record_id"] = outline_record_id(record)
    documents = [document_text(record) for record in outlines]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
    tfidf_matrix = vectorizer.fit_transform([normalize_text(document) for document in documents])
    tokenized, df, average_length = build_bm25(documents)

    normalized_subjects = [normalize_text(record.get("subject_name")) for record in outlines]
    exact_index: defaultdict[str, list[int]] = defaultdict(list)
    for index, subject in enumerate(normalized_subjects):
        exact_index[subject].append(index)

    results: list[dict[str, Any]] = []
    method_counts = {method: Counter() for method in ("exact_title", "tfidf", "bm25")}
    for course in formal_records:
        query = query_text(course)
        query_normalized = normalize_text(course.get("course_title"))
        exact_candidates = exact_index.get(query_normalized, [])
        exact_scores = np.zeros(len(outlines), dtype=float)
        for index in exact_candidates:
            exact_scores[index] = 1.0
        query_vector = vectorizer.transform([normalize_text(query)])
        tfidf_scores = (tfidf_matrix @ query_vector.T).toarray().ravel()
        bm25 = bm25_scores(query, tokenized, df, average_length)
        methods = {
            "exact_title": (exact_scores, exact_candidates),
            "tfidf": (tfidf_scores, None),
            "bm25": (bm25, None),
        }
        method_results: dict[str, list[dict[str, Any]]] = {}
        for method, (scores, exact) in methods.items():
            indices = exact if exact is not None else ranked_indices(scores)
            candidates = [candidate_payload(i, scores[i], outlines) for i in indices[:TOP_K]]
            method_results[method] = candidates
            method_counts[method]["queries"] += 1
            method_counts[method]["nonempty_top10"] += int(bool(candidates))
            method_counts[method]["top1_exact_subject"] += int(
                bool(candidates)
                and normalize_text(candidates[0]["subject_name"]) == query_normalized
            )
            method_counts[method]["top10_exact_subject"] += int(
                any(normalize_text(candidate["subject_name"]) == query_normalized for candidate in candidates)
            )
        results.append({
            "course_record_id": course.get("candidate_id"),
            "school_id": course.get("school_id"),
            "course_title": course.get("course_title"),
            "department_name": course.get("department_name"),
            "lane": "formal",
            "query_fields": ["course_title", "department_name"],
            "query_text": query,
            "retrieval_status": "candidate_only",
            "methods": method_results,
        })

    report = {
        "experiment": "phase2_1_course_outline_lexical_retrieval_v1",
        "status": "pass",
        "formal_commit": FORMAL_COMMIT,
        "formal_path": FORMAL_PATH,
        "outline_commit": OUTLINE_COMMIT,
        "outline_path": OUTLINE_PATH,
        "formal_record_count": len(formal_records),
        "outline_record_count": len(outlines),
        "query_fields": ["course_title", "department_name"],
        "syllabus_full_text_available_in_formal_input": False,
        "methods": dict(method_counts),
        "top_k": TOP_K,
        "candidate_only": True,
        "formal_alignment": "not_started",
        "human_adjudication": "not_available",
        "promotion_status": "blocked",
        "interpretation": "Lexical candidate retrieval diagnostic; exact title match is not truth alignment.",
    }
    (args.output_dir / "retrieval_results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in results),
        encoding="utf-8",
    )
    (args.output_dir / "retrieval_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

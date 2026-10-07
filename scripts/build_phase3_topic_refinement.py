"""Build Phase 3 topic/chapter/subtopic refinement artifacts.

Deterministic extraction only. Raw text and provenance are retained; extracted
topics are diagnostic candidates, not human truth / 僅作 diagnostic。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORMAL_COMMIT = "8922edc"
FORMAL_PATH = "output/canonical/round26_formal_syllabus_projection.json"
OUTLINE_COMMIT = "4cb1b5a7155a052450354cdff2e7e00a66728b89"
OUTLINE_PATH = "data/raw/exam_outlines/exam_outline_catalog/output/exam_outline_catalog.json"
FIELD_ALLOWLIST = ("course_description", "outline", "objectives")
OUTLINE_ALLOWLIST = ("outline", "core_knowledge")
GENERIC_RE = re.compile(r"(本課程|學生|學習|課程目標|教學|評量|教材|參考書|office|授課|了解|介紹|培養|能力|course|student|learn)", re.I)
HEADING_RE = re.compile(r"(?:^|\n)\s*(?P<head>(?:[一二三四五六七八九十]+、|\d+[\.、)]|[A-Z][\.、]))\s*(?P<text>[^\n]{2,120})")
SEPARATOR_RE = re.compile(r"[\n；;。！？!?]|(?:\s{2,})")


def git_json(repo: Path, commit: str, path: str) -> Any:
    """Read pinned JSON / 讀取 pinned JSON。"""
    return json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"]))


def as_text(value: Any) -> str:
    """Convert a value to text / 轉換文字。"""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def norm(text: str) -> str:
    """Normalize whitespace / 正規化空白。"""
    return re.sub(r"\s+", " ", text).strip(" \t\r\n,，;；:：")


def record_id(row: dict[str, Any]) -> str:
    """Create deterministic outline ID / 建立 deterministic outline ID。"""
    payload = {key: row.get(key) for key in ("subject_name", "type", "applicable_exams", "core_knowledge", "outline", "remarks", "source")}
    return "OUT-" + hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]


def split_atomic(raw: str) -> list[str]:
    """Split raw section into atomic topic candidates / 拆成 atomic topic candidates。"""
    text = raw.replace("\r", "\n")
    pieces = []
    for match in HEADING_RE.finditer(text):
        value = norm(match.group("text"))
        if value:
            pieces.append(value)
    if not pieces:
        pieces = [norm(piece) for piece in SEPARATOR_RE.split(text)]
    output = []
    seen = set()
    for piece in pieces:
        piece = re.sub(r"^(?:[-*•]|\d+[\.、)]|[一二三四五六七八九十]+、)\s*", "", piece)
        piece = norm(piece)
        if len(piece) < 3 or len(piece) > 300 or piece in seen:
            continue
        seen.add(piece)
        output.append(piece)
    return output


def topic_label(text: str) -> str:
    """Assign a transparent heuristic topic label / 建立透明 heuristic label。"""
    words = re.findall(r"[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9+#-]{1,30}", text)
    meaningful = [word for word in words if not GENERIC_RE.search(word)]
    return " / ".join(meaningful[:5]) if meaningful else text[:80]


def main() -> int:
    """Build refinement artifacts / 建立 refinement artifacts。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    formal = git_json(args.source_repo, FORMAL_COMMIT, FORMAL_PATH)
    outlines = git_json(args.source_repo, OUTLINE_COMMIT, OUTLINE_PATH)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    syllabus_rows, syllabus_chunks, outline_items = [], [], []
    parser_status = Counter()
    for record in formal:
        fields = record.get("syllabus_fields") or {}
        sections = []
        for field in FIELD_ALLOWLIST:
            raw = as_text(fields.get(field))
            if not raw:
                continue
            items = split_atomic(raw)
            status = "extracted" if items else "present_but_no_atomic_split"
            parser_status[status] += 1
            sections.append({"field": field, "raw_text": raw, "item_count": len(items), "parser_status": status})
            for index, item in enumerate(items):
                chunk_id = "SCH-" + hashlib.sha256(f"{record.get('record_id')}|{field}|{index}|{item}".encode()).hexdigest()[:20]
                syllabus_chunks.append({"chunk_id": chunk_id, "record_id": record.get("record_id"), "course_title": record.get("course_title"), "field": field, "section_index": index, "chapter": None, "topic": topic_label(item), "subtopic": item, "text": item, "raw_text": item, "source_path": FORMAL_PATH, "source_commit": FORMAL_COMMIT, "raw_sha256": record.get("raw_sha256") or record.get("content_sha256"), "extraction_status": "machine_candidate"})
        syllabus_rows.append({"record_id": record.get("record_id"), "course_title": record.get("course_title"), "sections": sections, "parser_status": "partial" if not sections else "extracted", "source_path": FORMAL_PATH, "source_commit": FORMAL_COMMIT})
    outline_status = Counter()
    for outline in outlines:
        oid = record_id(outline)
        for field in OUTLINE_ALLOWLIST:
            raw = as_text(outline.get(field))
            if not raw:
                continue
            items = split_atomic(raw)
            outline_status["fields_present"] += 1
            for index, item in enumerate(items):
                item_id = "OIT-" + hashlib.sha256(f"{oid}|{field}|{index}|{item}".encode()).hexdigest()[:20]
                outline_items.append({"outline_record_id": oid, "subject_name": outline.get("subject_name"), "field": field, "item_index": index, "chapter": None, "topic": topic_label(item), "subtopic": item, "text": item, "raw_text": item, "source": outline.get("source"), "source_path": OUTLINE_PATH, "source_commit": OUTLINE_COMMIT, "item_id": item_id, "extraction_status": "machine_candidate"})
    report = {"experiment": "phase3_retrieval_refinement_topic_extraction_v1", "formal_records": len(formal), "outline_records": len(outlines), "syllabus_sections": len(syllabus_rows), "syllabus_atomic_topic_chunks": len(syllabus_chunks), "outline_atomic_items": len(outline_items), "syllabus_parser_status": dict(parser_status), "outline_status": dict(outline_status), "raw_preserved": True, "machine_inference_only": True, "human_truth": False, "promotion_status": "blocked"}
    (args.output_dir / "refinement_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "syllabus_section_parse.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in syllabus_rows), encoding="utf-8")
    (args.output_dir / "syllabus_atomic_topic_chunks.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in syllabus_chunks), encoding="utf-8")
    (args.output_dir / "outline_atomic_items.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in outline_items), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

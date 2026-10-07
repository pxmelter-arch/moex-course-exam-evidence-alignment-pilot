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
CONTAMINATION_PATTERNS = {
    "assessment": re.compile(r"評量|考試|assessment|exam|quiz|作業|報告", re.I),
    "administrative": re.compile(r"office|email|電話|時間|星期|教室|授課|教師|office hour", re.I),
    "textbook": re.compile(r"教材|教科書|textbook|參考書|handbook", re.I),
    "schedule_note": re.compile(r"schedule|課程進度|note|備註|注意|copyright|智慧財產|週次|日期", re.I),
    "teaching_method": re.compile(r"教學方式|講授|討論|實作|teaching approach", re.I),
}


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


def heading_level(marker: str) -> int:
    """Infer hierarchy depth / 推斷 hierarchy depth。"""
    if re.fullmatch(r"第[一二三四五六七八九十]+章", marker):
        return 1
    if re.fullmatch(r"第[一二三四五六七八九十]+節", marker):
        return 2
    if re.fullmatch(r"[一二三四五六七八九十]+、", marker):
        return 1
    if re.fullmatch(r"\d+\.\d+\.\d+", marker):
        return 3
    if re.fullmatch(r"\d+\.\d+", marker):
        return 2
    if re.fullmatch(r"\d+[\.、)]", marker):
        return 1
    return 0


def split_atomic(raw: str) -> list[dict[str, Any]]:
    """Split raw text and propagate heading context / 拆分並傳遞 hierarchy。"""
    text = raw.replace("\r", "\n")
    pattern = re.compile(r"^\s*(?P<head>(?:第[一二三四五六七八九十]+[章節]|[一二三四五六七八九十]+、|\d+\.\d+\.\d+|\d+\.\d+|\d+[\.、)]))\s*(?P<body>.+?)\s*$")
    units: list[dict[str, Any]] = []
    chapter = topic = None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [piece.strip() for piece in re.split(r"[；;。！？!?]", text) if piece.strip()]
    for line in lines:
        match = pattern.match(line)
        if match:
            marker = match.group("head")
            body = norm(match.group("body"))
            level = heading_level(marker)
            if level == 1:
                chapter, topic = body, None
            elif level == 2:
                topic = body
            units.append({"text": body, "level": level, "chapter": chapter, "topic": topic, "marker": marker})
        else:
            for piece in re.split(r"[；;。！？!?]", line):
                value = norm(piece)
                if value:
                    units.append({"text": value, "level": 0, "chapter": chapter, "topic": topic, "marker": None})
    output = []
    seen = set()
    for unit in units:
        value = re.sub(r"^(?:[-*•]|\d+[\.、)]|[一二三四五六七八九十]+、)\s*", "", unit["text"])
        value = norm(value)
        if len(value) < 3 or len(value) > 300 or value in seen:
            continue
        seen.add(value)
        unit["text"] = value
        unit["subtopic"] = value
        output.append(unit)
    return output


def topic_label(text: str) -> str:
    """Assign a transparent heuristic topic label / 建立透明 heuristic label。"""
    words = re.findall(r"[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9+#-]{1,30}", text)
    meaningful = [word for word in words if not any(pattern.search(word) for pattern in CONTAMINATION_PATTERNS.values())]
    return " / ".join(meaningful[:5]) if meaningful else text[:80]


def contamination_labels(text: str) -> list[str]:
    """Return contamination flags / 回傳 contamination flags。"""
    return [name for name, pattern in CONTAMINATION_PATTERNS.items() if pattern.search(text)]


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
                chunk_id = "SCH-" + hashlib.sha256(f"{record.get('candidate_id')}|{field}|{index}|{item['text']}".encode()).hexdigest()[:20]
                flags = contamination_labels(item["text"])
                syllabus_chunks.append({"chunk_id": chunk_id, "record_id": record.get("candidate_id"), "course_title": record.get("course_title"), "field": field, "section_index": index, "chapter": item.get("chapter"), "topic": item.get("topic") or topic_label(item["text"]), "subtopic": item["text"], "text": item["text"], "raw_text": item["text"], "source_path": FORMAL_PATH, "source_commit": FORMAL_COMMIT, "raw_sha256": record.get("raw_sha256") or record.get("content_sha256"), "contamination_labels": flags, "lane": "contamination" if flags else "content", "extraction_status": "machine_candidate"})
        syllabus_rows.append({"record_id": record.get("candidate_id"), "course_title": record.get("course_title"), "sections": sections, "parser_status": "partial" if not sections else "extracted", "source_path": FORMAL_PATH, "source_commit": FORMAL_COMMIT})
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
                item_id = "OIT-" + hashlib.sha256(f"{oid}|{field}|{index}|{item['text']}".encode()).hexdigest()[:20]
                flags = contamination_labels(item["text"])
                outline_items.append({"outline_record_id": oid, "subject_name": outline.get("subject_name"), "field": field, "item_index": index, "chapter": item.get("chapter"), "topic": item.get("topic") or topic_label(item["text"]), "subtopic": item["text"], "text": item["text"], "raw_text": item["text"], "source": outline.get("source"), "source_path": OUTLINE_PATH, "source_commit": OUTLINE_COMMIT, "item_id": item_id, "contamination_labels": flags, "lane": "contamination" if flags else "content", "extraction_status": "machine_candidate"})
    report = {"experiment": "phase3_retrieval_refinement_topic_extraction_v2", "formal_records": len(formal), "outline_records": len(outlines), "syllabus_sections": len(syllabus_rows), "syllabus_atomic_topic_chunks": len(syllabus_chunks), "outline_atomic_items": len(outline_items), "syllabus_parser_status": dict(parser_status), "outline_status": dict(outline_status), "syllabus_lanes": dict(Counter(row["lane"] for row in syllabus_chunks)), "outline_lanes": dict(Counter(row["lane"] for row in outline_items)), "syllabus_hierarchy_depth": dict(Counter(1 if row.get("chapter") else 0 for row in syllabus_chunks)), "outline_hierarchy_depth": dict(Counter(1 if row.get("chapter") else 0 for row in outline_items)), "record_id_field": "candidate_id", "raw_preserved": True, "machine_inference_only": True, "human_truth": False, "promotion_status": "blocked"}
    (args.output_dir / "refinement_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "syllabus_section_parse.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in syllabus_rows), encoding="utf-8")
    (args.output_dir / "syllabus_atomic_topic_chunks.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in syllabus_chunks), encoding="utf-8")
    (args.output_dir / "outline_atomic_items.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in outline_items), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

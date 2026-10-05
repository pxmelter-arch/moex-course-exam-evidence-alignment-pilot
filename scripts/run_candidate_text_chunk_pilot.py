"""Run a bounded text normalization and chunking pilot.

The source dataset is read from the exact pinned Git object. Only chunk
metadata and hashes are written to the experiment repository; source text is
not copied into this repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_PATH = "output/unified_dataset/round26_20261004/structured_content_600.json"
SECTION_RE = re.compile(
    r"(?=(?:objectives|outline|assessment|textbook|reference|prerequisite|course_description|syllabus_fields):)",
    re.IGNORECASE,
)


def normalize_text(value: str) -> str:
    """Normalize Unicode and whitespace / 正規化 Unicode 與空白。"""
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def read_source(repo: Path, commit: str) -> list[dict[str, Any]]:
    """Read records from pinned Git object / 讀取 pinned Git record。"""
    output = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{commit}:{EXPECTED_PATH}"]
    )
    records = json.loads(output)
    if not isinstance(records, list):
        raise ValueError("candidate source is not a JSON array")
    return records


def make_chunks(record: dict[str, Any], lane: str) -> list[dict[str, Any]]:
    """Create section-aware chunk metadata / 建立 section-aware chunk metadata。"""
    text = normalize_text(str(record.get("content_text") or ""))
    if not text:
        return []
    pieces = [piece.strip() for piece in SECTION_RE.split(text) if piece.strip()]
    if not pieces:
        pieces = [text]
    chunks = []
    for index, piece in enumerate(pieces):
        section_match = re.match(r"([a-z_]+):", piece)
        section = section_match.group(1) if section_match else "document"
        chunk_id = f"{record['structured_id']}:chunk:{index:04d}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "structured_id": record["structured_id"],
                "school_id": record.get("school_id"),
                "lane": lane,
                "section_name": section,
                "chunk_index": index,
                "char_count": len(piece),
                "normalized_text_sha256": hashlib.sha256(piece.encode("utf-8")).hexdigest(),
                "source_raw_sha256": record.get("raw_sha256"),
                "content_status": record.get("content_status"),
                "hash_status": record.get("hash_status"),
                "provenance_status": record.get("provenance_status"),
                "review_status": "unreviewed",
                "machine_provisional": True,
            }
        )
    return chunks


def main() -> int:
    """Run pilot and write metadata artifacts / 執行 pilot 並寫出 metadata。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = read_source(args.source_repo, args.commit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_chunks: list[dict[str, Any]] = []
    record_lanes = Counter()
    for record in records:
        lane = "primary_content_bearing" if record.get("content_status") == "content_bearing" else "partial_sensitivity"
        record_lanes[lane] += 1
        all_chunks.extend(make_chunks(record, lane))

    section_counts = Counter(chunk["section_name"] for chunk in all_chunks)
    lane_chunks = Counter(chunk["lane"] for chunk in all_chunks)
    lengths = [chunk["char_count"] for chunk in all_chunks]
    report = {
        "pilot_version": "candidate-text-chunking-v1",
        "source_commit": args.commit,
        "source_path": EXPECTED_PATH,
        "record_count": len(records),
        "record_lane_counts": dict(record_lanes),
        "chunk_count": len(all_chunks),
        "chunk_lane_counts": dict(lane_chunks),
        "section_counts": dict(section_counts),
        "char_count": {
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "mean": round(sum(lengths) / len(lengths), 2) if lengths else 0,
        },
        "source_text_written_to_experiment_repo": False,
        "embedding_executed": False,
        "promotion_status": "blocked",
        "human_adjudicated": False,
    }
    (args.output_dir / "candidate_text_chunk_pilot_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (args.output_dir / "candidate_chunk_manifest.jsonl").open("w", encoding="utf-8") as handle:
        for chunk in all_chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", **report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

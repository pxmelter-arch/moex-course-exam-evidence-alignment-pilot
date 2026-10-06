"""Audit Phase 2 diagnostic completion gates.

This closes the candidate-retrieval diagnostic phase without promoting any
candidate to alignment truth / 完成 diagnostic，不 promotion truth。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    """Read JSON artifact / 讀取 JSON artifact。"""
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    """Audit completion gates / 審計完成 gates。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    phase26 = ROOT / "experiments/phase2_6_formal_chunk_dense_hybrid_evidence_v1"
    phase27 = ROOT / "experiments/phase2_7_formal_identity_bridge_v1"
    phase28 = ROOT / "experiments/phase2_8_identity_expanded_pool_comparison_v1"
    p26 = read_json(phase26 / "pipeline_report.json")
    p27 = read_json(phase27 / "identity_bridge_report.json")
    p28 = read_json(phase28 / "comparison_report.json")
    gates = {
        "formal_scope_176": p26["formal_records"] == 176,
        "outline_scope_542": p26["outline_records"] == 542,
        "section_chunks_1490": p26["chunk_count"] == 1490,
        "local_embedding_only": p26["embedding"]["local_only"] is True,
        "evidence_spans_provenance_preserved": p26["evidence_span_status"] == "provenance_preserved",
        "identity_bridge_176": p27["formal_records"] == 176,
        "duplicate_groups_audited": p27["duplicate_subject_name_groups"] == 36,
        "original_expanded_paired_comparison": p28["formal_records"] == 176,
        "three_gate_misses_recovered": p28["gate_miss_recovery"]["count"] == 3,
        "ambiguity_delta_audited": "ambiguous_delta" in p28,
        "promotion_blocked": p28["promotion_status"] == "blocked",
        "qdrant_ingest_blocked": p28["qdrant_ingest"] is False,
    }
    report = {
        "experiment": "phase2_candidate_retrieval_diagnostic_completion_v1",
        "phase2_status": "complete_for_candidate_retrieval_diagnostic",
        "formal_alignment_status": "not_started",
        "gates": gates,
        "all_diagnostic_gates_pass": all(gates.values()),
        "results": {
            "formal_records": p26["formal_records"],
            "outline_records": p26["outline_records"],
            "section_chunks": p26["chunk_count"],
            "phase2_6_top1_exact": p26["metrics"]["top1_exact_subject"],
            "phase2_6_top10_exact": p26["metrics"]["top10_exact_subject"],
            "identity_status_counts": p27["identity_status_counts"],
            "gate_miss_recovery": p28["gate_miss_recovery"]["count"],
            "original_top10_exact": p28["original_pool"]["metrics"]["top10_exact"],
            "expanded_top10_exact": p28["expanded_pool"]["metrics"]["top10_exact"],
            "ambiguous_delta": p28["ambiguous_delta"],
        },
        "non_goals_remaining": [
            "human_adjudicated alignment truth",
            "gold-label accuracy",
            "automatic promotion to default runtime",
            "Qdrant production ingest",
        ],
        "next_phase_boundary": "independent evidence/human adjudication and promotion review",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "phase2_completion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

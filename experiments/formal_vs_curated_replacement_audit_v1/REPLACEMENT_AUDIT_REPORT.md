# Formal 176 vs Curated Experiment 600 Replacement Audit

## Decision

```text
do_not_replace_formal_176
```

這不是因為 600 筆不能做實驗，而是因為 600 packet 目前仍是 `experimental_only`，且與 176 formal 的 identity/provenance lineage 不同。

## Pinned inputs

| Lane | Commit | Path | Records |
|---|---|---|---:|
| Formal | `8922edc` | `output/canonical/round26_formal_syllabus_projection.json` | 176 |
| Curated | `a22f8e7` | `release/curated_experiment_20261006/experiment_projection.jsonl` | 600 |

## Identity comparison

| Comparison | Count |
|---|---:|
| Exact composite identity overlap | 2 |
| Exact raw SHA-256 overlap | 2 |
| School + course-title overlap | 7 |
| Official URL overlap | 7 |
| Curated records overlapping formal identity | 2 |
| Formal records overlapping curated identity | 2 |

The low exact identity overlap shows that curated 600 is not simply a larger materialized copy of formal 176. It is a different population and lineage.

## Curated packet partition

```text
content_bearing = 520
partial = 80
source_record_status=quarantine = 370
source_record_status=quarantine_candidate_provenance_pending = 23
source_record_status=staged = 57
source_record_status=staged_course_evidence = 150
```

The two quarantine labels total 393 records. `quarantine` is retained as workflow/release state; it is not interpreted as content invalidity.

Curated packet metadata also declares:

```text
release_status = experimental_only for 600 / 600
formal_promotion = 0 at packet level
qdrant_ingest = false at packet level
fresh_raw_mixed_in = false
```

The projection records do not consistently carry per-record `formal_promotion` or `qdrant_ingest` fields; the packet-level manifest is therefore the authoritative release declaration for those fields.

## Curated duplicate signal

```text
duplicate structured_id groups = 0
duplicate raw_sha256 groups = 75
```

A repeated raw hash is a duplicate signal, not an automatic deletion instruction. It requires classification into exact duplicate, versioned source observation, or distinct record with shared raw artifact.

## Formal partition

```text
formal records = 176
formal_gate = passed = 176
content_status = full = 176
promotion_status = formal_manifest_eligible = 176
independent provenance:
  pass = 121
  pass_alias = 3
  pass_bounded_exact_official = 52
```

## Gate decision

| Gate | Result |
|---|---|
| Curated usable for parser/retrieval experiment | Yes |
| Curated usable as 520 content-bearing diagnostic subset | Yes |
| Curated can replace formal 176 without re-formalization | No |
| Formal lane changed | No |
| Promotion | Blocked |

## Required before any formal replacement

1. Reconcile 75 raw-hash duplicate groups.
2. Review 80 partial records and define abstention policy.
3. Resolve 393 quarantine/quarantine-pending workflow states.
4. Build per-record formal identity and provenance evidence.
5. Re-run formal eligibility gates and independent provenance audit.
6. Rebuild all formal baselines under the new scope.
7. Preserve 176 as a reproducible prior formal baseline.

This audit does not alter the formal dataset, default runtime, candidate runtime, Qdrant, or release pointer.

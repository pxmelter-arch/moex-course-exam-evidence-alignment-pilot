# Phase 2.6 Formal Course → Chunk → Dense/Hybrid → Evidence

## Scope

```text
formal syllabus projection = 176
normalized exam outlines = 542
```

Pinned inputs:

```text
formal commit: 8922edc
outline commit: 4cb1b5a7155a052450354cdff2e7e00a66728b89
```

## Pipeline

```text
course-level lexical candidate retrieval (K=50)
→ section-level chunks
→ chunk-to-outline lexical topic coverage
→ local dense embedding retrieval
→ lexical + dense hybrid ranking
→ evidence span output
```

## Chunking

```text
chunk count = 1490
chunk size = 420 characters
chunk overlap = 60 characters
```

Each chunk retains:

```text
chunk_id
record_id
section
section_index
source_path
source_commit
raw_sha256
evidence_span
```

## Local embedding

```text
model = BAAI/bge-small-zh-v1.5
local_only = true
device = cuda:0
normalize_embeddings = true
```

No external embedding API was used.

## Results

| Metric | Result |
|---|---:|
| Formal courses | 176 |
| Course candidate K | 50 |
| Output candidates per course | 10 |
| Top-1 exact subject | 22 / 176 |
| Top-10 query coverage exact subject | 24 / 176 |
| Top candidate exact | 8 |
| Top candidate ambiguous | 168 |
| Top candidate weak | 0 |
| Evidence candidates with complete provenance | 1760 / 1760 |

`top-10 query coverage` means a query is counted once if at least one exact normalized subject appears in its top 10; it is not the number of exact candidates.

## Interpretation

- The local dense/chunk hybrid produced 22/176 top-1 exact subject matches and 24/176 top-10 query coverage under the current diagnostic proxy.
- This is below the previous title-identity baseline of 27/176 top-1 and 27/176 top-10, so the current dense/chunk weighting is not yet an improvement.
- The pipeline nevertheless produces inspectable evidence spans for all 1,760 output candidates.
- `ambiguous` remains the dominant status because duplicate subject names and unresolved identity variants are retained rather than auto-merged.
- Exact subject is a retrieval diagnostic proxy, not human-validated alignment truth.

## Release state

```text
retrieval_status = candidate_only
evidence_span_status = provenance_preserved
formal_alignment = not_started
promotion_status = blocked_pending_alignment_evidence
qdrant_ingest = false
```

Artifacts:

```text
pipeline_report.json
section_chunks.jsonl
course_chunk_hybrid_results.jsonl
```

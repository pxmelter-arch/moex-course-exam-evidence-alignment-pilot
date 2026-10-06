# Phase 2 Completion Audit

## Status

```text
phase2 = complete_for_candidate_retrieval_diagnostic
formal_alignment = not_started
```

All diagnostic completion gates pass for the 176 formal lane:

```text
176 formal records
542 normalized exam outlines
1490 section chunks
local-only BGE embedding
provenance-preserving evidence spans
identity bridge and duplicate audit
original vs identity-expanded candidate comparison
3/3 gate-miss recovery audit
ambiguity delta audit
```

## Consolidated results

```text
Phase 2.6 top-1 exact proxy = 22/176
Phase 2.6 top-10 exact proxy = 24/176
identity-expanded top-10 exact proxy = 27/176
identity gate misses recovered = 3
ambiguous top-10 delta = -3
identity status = 13 exact / 20 ambiguous / 143 weak
```

Exact subject is a retrieval diagnostic proxy, not human alignment truth.

## Explicitly not completed

```text
human-adjudicated alignment truth
accuracy against gold labels
automatic promotion to default runtime
Qdrant production ingest
```

The next phase boundary is independent evidence and human-adjudication/promotion review. The formal lane, default runtime, and Qdrant remain unchanged.

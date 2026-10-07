# Phase 3 Hierarchy and Contamination-aware Topic Lane v2

## Changes

```text
record identity: candidate_id
hierarchy parser: numbered / Chinese heading candidates
contamination lane: explicit flags without deleting raw text
content lane: unflagged topic candidates
```

## Results

```text
formal syllabus records = 176
syllabus atomic chunks = 6345
outline atomic items = 2571
```

Hierarchy candidates:

```text
syllabus chapter-resolved = 3034
syllabus chapter-unresolved = 3311
outline chapter-unresolved = 2571
```

The outline catalog still lacks reliable nested chapter structure in the current representation. Syllabus hierarchy is partially recovered by deterministic heading propagation, but remains machine-candidate only.

Contamination-aware lanes:

```text
syllabus content lane = 5515
syllabus contamination lane = 830
outline content lane = 2514
outline contamination lane = 57
```

## Reranking result after v2 extraction

```text
baseline expanded top-1 = 22 / 176
after topic/coverage reranking top-1 = 22 / 176
baseline expanded top-10 = 27 / 176
after topic/coverage reranking top-10 = 27 / 176
```

The parser and contamination lane changed representation and diagnostics, but did not improve the current exact-subject proxy.

```text
formal_alignment = not_started
promotion = blocked
qdrant_ingest = false
```

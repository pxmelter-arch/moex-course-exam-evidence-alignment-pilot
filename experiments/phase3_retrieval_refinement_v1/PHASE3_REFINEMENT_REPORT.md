# Phase 3 Retrieval Refinement: Topic Extraction Pilot

## Scope

```text
formal syllabus records = 176
normalized outline records = 542
```

This bounded pilot implements the first refinement steps:

```text
section parsing
machine chapter/topic/subtopic candidates
outline item normalization
atomic topic candidate generation
```

## Results

```text
syllabus sections = 176
syllabus atomic topic candidates = 4750
outline atomic items = 2573
present but not atomically split sections = 6
```

## Important limitation

The extracted `topic` and `subtopic` values are deterministic machine candidates. They are not human semantic labels. `chapter` remains unresolved where a reliable heading hierarchy is not available; no chapter value is fabricated.

Raw text and provenance are retained:

```text
source_path
source_commit
raw_sha256 where present
field
section_index / item_index
raw_text
```

Generic course and administrative language is not silently treated as exam-topic truth. Further contamination filtering and semantic validation are required before retrieval reranking.

## Release boundary

```text
retrieval_refinement = extraction_pilot_complete
formal_alignment = not_started
promotion = blocked
qdrant_ingest = false
```

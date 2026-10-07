# Phase 3 Topic Matching, Bidirectional Coverage, and Reranking

## Scope

```text
formal records = 176
syllabus atomic topic candidates = 4750
outline atomic items = 2573
paired expanded candidates = 1760
```

Pipeline:

```text
syllabus atomic topic
→ outline atomic item matching
→ syllabus-to-outline coverage
→ outline-to-syllabus coverage
→ lexical + local dense + coverage reranking
```

## Results

| Metric | Expanded baseline | Coverage reranked | Delta |
|---|---:|---:|---:|
| Top-1 exact subject proxy | 22 / 176 | 22 / 176 | 0 |
| Top-10 exact subject proxy | 27 / 176 | 27 / 176 | 0 |

The unchanged result is a valid negative diagnostic result. Coverage signals were computed and evidence was generated, but the current machine topic extraction, threshold, and weighting did not improve exact-subject ranking.

## Evidence

Each topic match retains:

```text
syllabus_chunk_id
outline_item_id
lexical score
dense score
syllabus-to-outline coverage
outline-to-syllabus coverage
```

## Limitations

The topic and subtopic fields are machine candidates, not human semantic labels. The exact-subject metric is a retrieval proxy, not alignment truth. No promotion or Qdrant ingest is performed.

```text
formal_alignment = not_started
promotion = blocked
qdrant_ingest = false
```

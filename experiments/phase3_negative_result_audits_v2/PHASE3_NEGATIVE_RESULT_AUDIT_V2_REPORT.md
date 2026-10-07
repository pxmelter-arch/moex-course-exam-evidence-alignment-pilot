# Phase 3 Negative-result Audit v2

## Results after hierarchy parser and contamination lane refinement

```text
formal records = 176
syllabus atomic chunks = 6345
outline atomic items = 2571
```

### Hierarchy

```text
syllabus chapter-resolved = 3034
syllabus chapter-unresolved = 3311
outline chapter-unresolved = 2571
```

Syllabus heading propagation recovered deterministic chapter candidates. Outline hierarchy remains unresolved because the catalog representation does not expose reliable nested chapter structure.

### Contamination

```text
syllabus flagged chunks = 830 / 6345
outline flagged items = 57 / 2571
```

Contamination is represented as a separate lane; raw text remains preserved.

### Coverage threshold sensitivity

```text
0.30: top-1 22 / 176, top-10 27 / 176
0.42: top-1 22 / 176, top-10 27 / 176
0.55: top-1 22 / 176, top-10 27 / 176
0.65: top-1 22 / 176, top-10 27 / 176
```

### Weight ablation

```text
current:          top-1 22, top-10 27
coverage-heavy:   top-1 22, top-10 27
lexical-heavy:    top-1 22, top-10 27
dense-heavy:      top-1 22, top-10 27
identity-removed: top-1 11, top-10 27
```

The identity signal remains important, but the v2 parser reduces the identity-removed top-1 collapse from 2 to 11. Topic/coverage reranking still does not improve the current exact-subject proxy.

### Corroboration and review

```text
independent corroboration ready = 0
review queue = 1760
machine labels = 0
```

```text
formal_alignment = not_started
promotion = blocked
qdrant_ingest = false
```

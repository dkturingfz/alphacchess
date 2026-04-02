# Text Corpus Manual Review Guidelines

## Purpose

This document defines the permanent human review standard for text-corpus entries used by Fish-LangCell data assets. The objective is to ensure that every retained text entry is biologically grounded, label-aligned, and consistent with repository schemas before downstream data processing.

## Scope

These guidelines apply to the following corpus files:

- `data/text_corpus/fish_celltype_definitions.jsonl`
- `data/text_corpus/testis_celltype_definitions.jsonl`
- `data/text_corpus/marker_sentences.jsonl`
- `data/text_corpus/hierarchy_descriptions.jsonl`

They apply to initial curation, revision passes, and release readiness reviews.

## Review principles

1. **Accuracy over coverage**: reject uncertain or weakly supported language rather than keeping borderline entries.
2. **Schema fidelity**: text content must match declared fields and `text_type` semantics.
3. **Conservatism**: avoid speculative claims unless explicitly labeled and justified in notes.
4. **Traceability**: every review decision should be recoverable from entry-level notes/status.
5. **Consistency**: similar labels across files should follow consistent wording and evidence standards.

## Review checklist by text type

### `definition`

- Must provide a concise description of what the cell type is (identity/function/context).
- Must avoid turning marker evidence into absolute identity claims.
- Should remain stable across species/context unless the label itself is context-specific.

### `marker_prompt`

- Must frame markers as suggestive evidence, not guaranteed identity.
- Must avoid exhaustive or inflated marker lists.
- Should prioritize markers that are relevant and interpretable for the declared label.

### `hierarchy_description`

- Must describe parent-child lineage/ontology placement clearly.
- Must not conflict with repository ontology mapping assumptions.
- Should explicitly indicate scope when hierarchy is tissue- or stage-specific.

### `alias`

- Must be a naming variant/synonym of the same biological label.
- Must not introduce a distinct cell type under alias form.
- Should avoid ambiguous shorthand unless ambiguity is documented.

## Required review checks for every entry

For every row/entry, reviewers must verify all checks below:

1. **Label-text alignment**: text matches the target cell-type label and does not drift to adjacent labels.
2. **Correct `text_type` behavior**: content follows the intended behavior for its text type.
3. **No speculative language unless explicitly documented**: uncertain wording requires explicit documentation and rationale.
4. **Marker restraint and relevance**: marker mentions are limited to relevant support and not overstated.
5. **Consistency with ontology hierarchy**: entry does not contradict known parent/child placement.
6. **Duplication / near-duplication check**: duplicates are removed or intentionally retained with clear purpose.
7. **Broad-vs-testis context consistency**: broad fish corpus and testis-specific corpus do not conflict for shared labels.

## Review status policy

Use one of the following statuses for each entry:

- **`draft`**: unreviewed or substantially modified since last review.
- **`reviewed`**: manually reviewed against this guideline; eligible for internal processing.
- **`frozen`**: release-locked text; change only through explicit change request.
- **`deprecated`**: retained for history/audit but not used for active dataset builds.

Status transitions should be monotonic for release slices (`draft` -> `reviewed` -> `frozen`), with `deprecated` used when content is intentionally retired.

## Handling uncertain cases

When evidence is ambiguous or conflicts exist:

1. Keep or set status to `draft`.
2. Add concise uncertainty notes (what is unclear, what evidence conflicts).
3. Prefer neutral wording over assertive claims.
4. Escalate for a second reviewer when uncertainty affects label assignment.
5. Do not promote to `reviewed` until uncertainty is resolved or explicitly accepted with documented caveats.

## Suggested reviewer workflow

1. **Batch preparation**: group entries by label family and text type.
2. **First-pass screening**: remove obvious off-topic or malformed entries.
3. **Entry-level review**: apply the required checks in order.
4. **Cross-file consistency pass**: compare shared labels between broad fish and testis subsets.
5. **Deduplication pass**: identify exact and near duplicates across files.
6. **Status update**: assign `draft`/`reviewed`/`frozen`/`deprecated`.
7. **Change log note**: record what changed and why for auditability.

## Minimal review checklist block

Use this block (or equivalent) in review notes/PRs:

```text
[ ] Label-text alignment verified
[ ] text_type behavior verified
[ ] Speculative language handled/documented
[ ] Marker restraint and relevance checked
[ ] Ontology hierarchy consistency checked
[ ] Duplicate / near-duplicate check completed
[ ] Broad-vs-testis consistency checked
[ ] Review status set: draft / reviewed / frozen / deprecated
```

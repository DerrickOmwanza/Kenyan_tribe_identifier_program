# Reference Research and Evidence Workflow

This workflow prepares verified evidence for future **likely
community/linguistic association based on name patterns** references. It does
not classify people, establish actual ethnicity, or generate a bulk dictionary.

## Principles and source selection

Prefer traceable academic, institutional, government, established linguistic,
or community-language sources with identifiable authorship and scope. An
internet page is not automatically reliable. Every source is registered before
its evidence is used. The registry records reliability and verification state;
unknown information remains explicitly unknown.

## Controlled reliability

- `very_high`: authoritative, identifiable publication or institution with
  independently checkable provenance and strong methodological relevance.
- `high`: credible scholarly or institutional source with good provenance and
  relevant scope.
- `moderate`: useful documented source with limitations, partial coverage, or
  less independent corroboration.
- `low`: weakly documented, informal, or materially limited source; never enough
  alone for approval.
- `unknown`: reliability cannot yet be assessed.

Dataset frequency is descriptive evidence only. It is not evidence of
community membership.

## Evidence types

`explicit_documentation` records what a source directly states.
`linguistic_form` records documented form or phonological evidence.
`naming_system` records a documented naming-system convention.
`lexical_evidence` records a documented lexical relationship.
`community_documentation` records a community or language resource statement.
`independent_corroboration` records separate supporting sources.
`dataset_observation` records frequency or distribution in the supplied data.
`contextual_evidence` records relevant documented context.
`uncertain` records unresolved evidence.
`contradictory` records evidence that conflicts with another entry.

## Evidence ledger and quotation policy

The ledger keeps source statement, interpretation, and uncertainty separate:
`evidence_statement` describes what is explicitly documented;
`source_quote_or_excerpt` stores only a short relevant excerpt; and
`interpretation_note` explains the limited inference and remaining uncertainty.
Record page, section, chapter, or other location whenever available. Do not
copy entire copyrighted works, fabricate citations, or invent URLs.

## Workflow

```text
SOURCE DISCOVERY
      ↓
SOURCE REGISTRATION
      ↓
SOURCE VERIFICATION
      ↓
EVIDENCE EXTRACTION
      ↓
CANDIDATE REFERENCE ENTRY
      ↓
INDEPENDENT CORROBORATION
      ↓
REVIEW
      ↓
APPROVAL
      ↓
NAME DICTIONARY
```

An evidence ledger row must reference an existing `source_id`. A future
`name_dictionary.csv` entry must be traceable to one or more ledger entries.
`candidate` or `source_verified` is not approval. `approved` requires human
review and adequate provenance; an LLM-generated suggestion alone is never
approval.

## Corroboration and conflicts

Independent corroboration means genuinely separate sources, not duplicate
copies of the same dataset. Conflicting sources are never silently reconciled:
preserve each source and its statement, record the disagreement using
`contradictory`, allow multiple plausible associations, and mark the name for
`needs_review` or `Ambiguous`. Insufficient evidence remains `Unknown` rather
than being forced into a community.

`position_scope` may be `fname`, `mname`, `sname`, or `any_position`. Position
relevance is evidence context, not a rule that determines association.

## Source independence rule

Stage 2 established `unique(tribes.txt:sname) == unique(sname.txt)`. These are
not independent evidence sources for surname association. Frequency may be
recorded as `dataset_observation` from `tribes.txt`; `sname.txt` may serve as a
validation artifact, but neither dataset automatically establishes a
community/linguistic association or counts as independent corroboration.

Generic Biblical, English, internationally common, and Arabic/Muslim names,
as well as broad prefixes, cannot independently establish an association.
Name patterns never establish actual ethnicity.

# Reference Data Architecture

This reference layer is a provenance-first schema for future **likely
community/linguistic association based on name patterns** analysis. The CSVs
are intentionally header-only at this stage. No observed name has been
classified and no community/name dictionary has been populated.

## Files and fields

### `community_reference.csv`

`association_id` (required, stable identifier), `display_name` (required),
`association_type` (required, linguistic/community or naming/cultural
descriptor), `description` (optional), `review_status` (required),
`source_reference` (required), and `notes` (optional). This controlled registry
must support `Unknown`, `Ambiguous`, and `Generic/Non-informative` states where
needed; it must not assert actual ethnicity.

### `name_dictionary.csv`

All fields below are required unless marked optional:

| Field | Requirement and allowed values |
|---|---|
| `name_token` | Required; original spelling exactly as documented |
| `normalized_token` | Required; analysis-only normalized form, stored separately |
| `primary_association` | Optional; blank, `Unknown`, `Ambiguous`, or `Generic/Non-informative`; otherwise a reviewed registry ID |
| `alternative_associations` | Optional; zero or more reviewed IDs, separated by `\|` |
| `category` | Required: `distinctive`, `supporting`, `moderate_ambiguous`, `generic`, `cross_community`, `manual_review`, `excluded` |
| `strength` | Required: `very_strong`, `strong`, `moderate`, `weak`, `ambiguous`, `non_informative` |
| `evidence_score` | Optional numeric strength of the reference evidence, not person-level confidence |
| `evidence_type` | Required controlled descriptor(s): distinctive linguistic/name-form pattern, documented community association, supporting naming pattern, dataset frequency, position-specific evidence, alternative association, generic/common given name, ambiguous evidence, insufficient evidence, or manual verification |
| `position_scope` | Required: `fname`, `mname`, `sname`, or `any_position` |
| `source_type` | Required, such as published reference, curated dataset, archival source, or manual review |
| `source_reference` | Required title/identifier; never a fabricated citation |
| `source_url` | Optional URL |
| `evidence_note` | Required rationale describing what the source supports |
| `review_status` | Required: `draft`, `needs_verification`, `reviewed`, `approved`, `rejected` |
| `reviewer` | Optional until review occurs |
| `date_added` | Optional ISO date |
| `notes` | Optional |

### `aliases.csv`

`name_token`, `alias_token`, `normalized_alias`, and `relationship` are
required. `relationship` is one of `spelling_variant`,
`transliteration_variant`, `abbreviation`, `historical_variant`, or `other`.
`source_reference` and `review_status` are required; `notes` is optional.

### `ambiguous_names.csv`

Required: `name_token`, `normalized_token`, `candidate_associations`,
`reason`, `source_reference`, and `review_status`. `reviewer` and `notes` are
optional. This file records unresolved alternatives or insufficient evidence.

### `excluded_names.csv`

Required: `name_token`, `normalized_token`, `exclusion_reason`,
`source_reference`, and `review_status`. `reviewer` and `notes` are optional.
Excluded entries must not independently contribute meaningful evidence.

## Evidence and decision principles

Reference strength describes the quality and distinctiveness of the evidence
supporting a reference entry. Classification confidence, which belongs to a
later engine and a particular record, is a separate concept and must never be
derived or reported as if it were reference strength.

Evidence should be ranked from documented, distinctive evidence; to corroborated
supporting patterns; to moderate or ambiguous evidence; with generic/common
given names and insufficient evidence treated as non-informative. Generic
Biblical, English, internationally common, and Arabic/Muslim naming patterns
must not independently select a Kenyan community. Broad prefixes must not
independently select one either.

Position scope records where a signal was documented as relevant (`fname`,
`mname`, `sname`, or `any_position`) without assuming that position alone
determines association.

Conflicting strong evidence, multiple plausible associations, incomplete
records, unusual tokens, reference disagreement, and insufficient evidence
must remain `Ambiguous`, `Unknown`, `Generic/Non-informative`, or `manual_review`
as appropriate. Nothing is forced into a community.

## Provenance and source independence

Every non-empty reference entry requires a source type, source identifier,
evidence rationale, review status, and (when available) reviewer and date. If
no source is available, use `needs_verification` and state that verification is
required; do not invent URLs or citations.

Stage 2 established that the unique values in `sname.txt` and
`tribes.txt:sname` are identical. They are therefore not independent evidence
sources. Frequency may be derived from `tribes.txt`; `sname.txt` may be retained
as a validation artifact, but it must never count as independent corroboration.

All outputs from later processing belong under `output/`. Actual ethnicity must
never be presented as established solely from a person's name.

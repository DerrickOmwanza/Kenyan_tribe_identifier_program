# Candidate Prioritization

This stage identifies tokens worth researching first. It does not classify
names, infer ethnicity, or assign community membership. A high-priority token
means only: **this token is worth researching**. It may later be generic,
ambiguous, cross-community, unknown, or excluded.

## Features

For each unique token across `tribes.txt` positions and `sname.txt`, the script
records total frequency, frequency by position, position count, surname
concentration (`sname_frequency / total_frequency`), distinct complete records
containing the token, token length/shape flags, presence in `sname.txt`, and
existing verified-reference status. The duplicate `sname.txt` source is not
given an independent evidence weight.

## Score

`research_priority_score` is deterministic research-priority points:

- 1–4 points from `1 + floor(log10(total_frequency))`, capped at 4
- +2 if observed in surname position
- +1 if surname concentration is at least 0.75
- +0–2 for occurrence in 1–3 positions
- +1 if present in at least two distinct complete records
- +1 when there are no structural flags

This is not a statistical probability, ethnicity score, community score, or
classification confidence.

## Categories and independent review flags

Research priority is independent from review characteristics:
`research_now` is score >= 8; `research_next` is 5–7; `lower_priority` is
1–4; `insufficient_data` is score 0. A high-priority token can simultaneously
have any review flags.

The flags are `generic_review_flag`, `multi_position_flag`,
`structural_review_flag`, `evidence_gap_flag`, and `ambiguity_flag`.
Multi-position occurrence is descriptive and is not linguistic ambiguity.
`ambiguity_flag` is only set when the existing reference/evidence framework
explicitly records `Ambiguous` or `needs_review`; an empty framework therefore
does not manufacture ambiguity. Evidence absence produces `evidence_gap_flag`,
not ambiguity.

`generic_review_flag` is a review mechanism, not a generic-name list: it flags
tokens with at least 500 first-name observations. No Biblical, English,
international, Arabic, or Muslim name list is embedded. Structural flags
identify data-shape review candidates only.

`research_scope` is descriptive: `surname_candidate`,
`multi_position_candidate`, or `given_name_candidate`.

Frequency contributes because it may increase potential reference coverage, not
because it implies community distinctiveness. No ethnicity/community
classification occurs at this stage.

## Limitations

Frequency reflects this dataset, not population prevalence or community
membership. Position concentration is descriptive only. Dataset observations
cannot replace documented sources in the evidence ledger, and no candidate
becomes a reference entry until verified provenance and human review exist.

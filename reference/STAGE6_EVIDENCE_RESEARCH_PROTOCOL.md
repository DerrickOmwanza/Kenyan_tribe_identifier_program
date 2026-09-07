# Stage 6A Evidence Research Protocol

This batch is a list of high-priority research candidates, not a list of
tribal, ethnic, community, cultural, or linguistic classifications. A
candidate means only that the observed token is worth investigating.

## Workflow

1. Select the candidate from the controlled batch.
2. Search authoritative sources.
3. Register each source in `source_registry.csv`.
4. Verify provenance, scope, access, and reliability.
5. Extract only relevant evidence.
6. Record the exact evidence statement separately from interpretation.
7. Record page, section, chapter, or other source location.
8. Record alternative interpretations and uncertainty.
9. Assign evidence strength using the reference framework.
10. Submit the record for human review.
11. Create a `name_dictionary.csv` entry only after review and adequate provenance.

## Source hierarchy

Prefer, in order:

1. Peer-reviewed academic research
2. University theses or dissertations
3. Academic books
4. Government or institutional publications
5. Established linguistic or community-language resources
6. Other documented sources

Random websites, social-media posts, unsourced name lists, AI-generated lists,
and frequency in the supplied dataset are not sufficient evidence for an
association. Dataset frequency may be recorded as `dataset_observation`, but
does not establish community membership.

## Evidence standard and conflicts

An eventual approved entry should contain the exact token, proposed
association, evidence statement, source and location, evidence type and
strength, interpretation, alternatives, reviewer, and review status. Weak
evidence must not be converted into certainty.

If credible sources disagree, preserve both sources, both interpretations, and
the disagreement. Use contradictory evidence and `needs_review`; do not choose
automatically. If evidence is insufficient, use `Unknown` rather than guess.

Preserve `fname`, `mname`, `sname`, or `any_position` as contextual position
scope. Position does not determine association. `sname.txt` and
`tribes.txt:sname` are not independent corroboration because Stage 2 found
identical unique-value sets.

Do not copy complete copyrighted works. Store short relevant excerpts only,
with legitimate bibliographic references or URLs. Never fabricate citations.
Name patterns can support only a **likely community/linguistic association based
on name patterns** and never establish actual ethnicity.

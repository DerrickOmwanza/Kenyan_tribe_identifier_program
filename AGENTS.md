# Project Instructions

These rules apply permanently to all work in this project:

1. Original source data must never be modified.
2. Original spelling must always be preserved.
3. Normalized values must be stored separately from original values.
4. The system must be reproducible.
5. Every classification must have an auditable evidence trail.
6. Unknown and ambiguous cases must not be forcibly classified.
7. Generic Biblical/English names must not independently determine community
   association.
8. Broad prefixes such as MU, WA, NA, KI, MA and NG must not independently
   determine a community.
9. Use the terminology **likely community/linguistic association based on name
   patterns**.
10. Actual ethnicity must never be presented as established solely from a
    person's name.
11. Bulk processing must be performed programmatically rather than by asking an
    LLM to classify every row individually.
12. All generated outputs must be placed under `output/`.
13. Never silently overwrite source data.
14. Changes to classification logic must be testable and documented.

The original source files must remain available for audit and must not be
silently relocated, rewritten, normalized, cleaned, classified, or overwritten.
The community/name dictionary will be designed in a later stage.

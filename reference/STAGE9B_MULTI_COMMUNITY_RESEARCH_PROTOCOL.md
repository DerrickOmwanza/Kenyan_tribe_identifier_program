# Stage 9B Multi-Community Reference Expansion Protocol

This protocol governs the systematic documentary evidence research for Stage 9B Multi-Community Reference Expansion Pilot.

## Purpose

To research documentary evidence concerning 25 high-priority name tokens identified by Stage 9A, preserving existing evidence and establishing new evidence records for future consideration.

## Scope

**25 Candidates (in priority order):**
1. KAMAU
2. KARIUKI
3. NJOROGE
4. MUTUA
5. KIMANI
6. OMONDI
7. WAMBUA
8. NJUGUNA
9. MACHARIA
10. JUMA
11. OUMA
12. MUTUKU
13. WANJIRU
14. NDUNGU
15. MUSYOKA
16. KARANJA
17. IRUNGU
18. NJERI
19. WAMBUI
20. WANJIKU
21. CHEGE
22. WAWERU
23. OWINO
24. ODUOR
25. KIOKO

## Critical Constraints

### Non-Negotiable Rules

1. **DO NOT determine or infer ethnicity** of any individual
2. **DO NOT assume a community** before evidence is found
3. **DO NOT modify the approved dictionary** - it must remain 6 entries
4. **DO NOT modify raw data files** (tribes.txt, sname.txt)
5. **DO NOT run classification** - this is research only
6. **DO NOT classify the Unknown population** (137,522 records)

### Terminology

Use only: **"documented community/linguistic association of a name form"**

Never present:
- Actual ethnicity as established
- Individual community membership as fact
- Name-based association as identity proof

## Research Methodology

### Source-First Strategy

Identify authoritative documentary sources capable of supporting multiple candidates:

**Priority Source Types:**
1. Academic books (peer-reviewed, published)
2. Peer-reviewed academic papers
3. Academic theses/dissertations
4. University repositories/institutional publications
5. Dictionaries and lexicons
6. Documented community-language resources
7. Historical/anthropological works with provenance

### Token-Level Evidence Requirement

A source supports an evidence record ONLY when it establishes something relevant about the candidate token.

**Valid evidence includes:**
- Documented linguistic/name-form pattern
- Documented community naming-system association
- Documented borrowing/adaptation/usage across communities
- Documented position-specific naming usage
- Documented generation-set association
- Documented time-of-birth naming association

**Does NOT constitute evidence:**
- Model knowledge/intuition
- "Sounds like" or "looks like" reasoning
- Frequency in tribes.txt or sname.txt
- Co-occurrence with another name
- Ethnicity of people who carry the name
- Unsourced name lists or website claims

## Evidence Recording Protocol

### Evidence Types (Controlled Vocabulary)

- `explicit_documentation` - Source directly states the association
- `linguistic_form` - Documented form/phonological evidence
- `naming_system` - Documented naming-system convention
- `lexical_evidence` - Documented lexical relationship
- `community_documentation` - Community/language resource statement
- `independent_corroboration` - Separate supporting source
- `dataset_observation` - Frequency/distribution in data (descriptive only)
- `contextual_evidence` - Relevant documented context
- `uncertain` - Unresolved evidence
- `contradictory` - Evidence that conflicts with another entry

### Evidence Strength (Controlled Vocabulary)

- `very_strong` - Direct token-level academic documentation
- `strong` - Documented naming-system evidence
- `moderate` - Contextual documentation
- `weak` - Secondary or indexed leads
- `ambiguous` - Conflicting or unclear evidence
- `non_informative` - Generic/common names

### Position Scope

- `fname` - Evidence supports first name usage
- `mname` - Evidence supports middle name usage
- `sname` - Evidence supports surname usage
- `any_position` - Evidence applies to any name position

### Association Types

- `community/linguistic association` - Documented association
- `shared_usage` - Used across communities
- `borrowed/adapted` - Borrowed or adapted from another community
- `ambiguous` - Multiple plausible associations without clear priority

### Review Status

- `unresolved` - No directly inspectable token-level documentary evidence found
- `source_verified` - Source was directly inspected
- `independently_corroborated` - Supported by genuinely independent source
- `approved` - Human-reviewed with adequate provenance

## Shared/Borrowed/Adapted Names Protocol

If evidence indicates a name is:
- Shared across communities
- Borrowed or adapted
- Transliterated
- Historically transferred

**Preserve that information. DO NOT force exclusive classification.**

Record structure:
```
primary_association = Community A
alternative_associations = Community B
association_type = borrowed/adapted/shared
```

## Existing Evidence Preservation

Pre-existing research in evidence_ledger.csv must be preserved:

**KARIUKI:**
- E6B2-KARIUKI-01: Kikuyu association evidence
- E6B2-KARIUKI-02: Ekegusii borrowing/adaptation evidence

**NJOROGE:**
- E6B2-NJOROGE-01: Kikuyu association evidence
- E6B2-NJOROGE-02: Ekegusii borrowing/adaptation evidence

**OMONDI:**
- E6B7-OMONDI-01: Source-verified moderate Luo/Dholuo evidence

**KAMAU:**
- Previously researched but unresolved - will be re-examined

**Cannot be deleted, overwritten, downgraded, or duplicated.**

## Output Files

### Stage 9B Source Registry Additions
`reference/stage9b_source_registry_additions.csv`
- New sources identified during research

### Stage 9B Evidence Ledger
`reference/stage9b_evidence_ledger.csv`
- New evidence records (NOT the primary evidence_ledger.csv)

### Stage 9B Research Batch
`output/stage9b_research_batch.csv`
- Candidates with research results summary

### Stage 9B Research Report
`output/stage9b_research_report.md`
- Comprehensive documentation of findings

## Validation Requirements

### Hash Preservation

**Before and after validation:**
- Tribes.txt: `F7BFC6ECEFEF03A28C1052700EF5ED9B62D25ADD5B8952682A691DF84B41C2F9`
- Sname.txt: `67561B996AD9A99EEA9C4A32912E0EE5CDB079AFBBBC96BDA3371B24A31E9DFC`
- Dictionary: `B433E3A91DA62A009ECD56457AE2CFDB1D6BC9ACCE682FB49EA126DA57022679`

### Count Verification

- Approved dictionary count MUST remain: 6
- Classifier status counts MUST remain unchanged
- Stage 9A candidates MUST remain exactly 25

## Stop Condition

After completing this research:

1. Run complete test suite
2. Verify all hashes match
3. Verify no dictionary modifications
4. Provide final report
5. STOP - do NOT proceed to Stage 9C

## Safety Reminders

- Raw source files must not be modified
- Approved dictionary must not be modified
- Classification results must not be modified
- Frequency data is descriptive only, never evidence
- Shared/borrowed names preserve all associations
- Unresolved ≠ generic or unknown ethnicity
- Every claim must have documented evidence
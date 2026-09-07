# Stage 6C.1 Research Batch 002 Protocol

Batch 002 is a deterministic research queue of 50 observed tokens. It is not a classification result and assigns no community, ethnicity, confidence, evidence strength, or dictionary category.

Candidates are drawn from `output/reference_candidates.csv`. Approved dictionary tokens and tokens already in Research Batch 001 are excluded. Eligible `research_now` candidates are selected first; `research_next` candidates are used only if needed. Ordering is research-priority score descending, surname frequency descending, total frequency descending, complete-record count descending, then token ascending.

Each selected row starts as `pending_research`. The worksheet's evidence fields remain blank until a separate source-research pass. Researchers must register sources, inspect the actual source, record exact locations and short excerpts, distinguish evidence from interpretation, and preserve uncertainty, contradictions, borrowing, adaptation, and shared use.

Use the source hierarchy in the project workflow: academic and institutional research, theses, books, dictionaries or lexicons, and other documented sources. Generic name websites, snippets, prefixes, dataset frequency, surname position, and name appearance are research leads only, not documentary evidence. `sname.txt` is not independent corroboration because it duplicates the observed surname value set.

Unknown and ambiguous cases must remain unresolved. Do not infer individual ethnicity or community membership. The permitted interpretation is **likely community/linguistic association based on name patterns**. Batch 002 does not modify source data, the evidence ledger, the source registry, or the dictionary.

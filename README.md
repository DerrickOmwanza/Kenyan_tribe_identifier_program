# Kenya Name Reference Engine (`kne`)

A reproducible, auditable CLI that adds or refines a **Tribe** column on a
spreadsheet of Kenyan names (`fname`, `mname`, `sname`). It combines a curated
documentary-evidence dictionary with statistics learned from a labelled reference
corpus, produces a calibrated confidence for every row, and abstains rather than
guess when the name carries no clear signal.

> A name-based association indicates a **likely community / linguistic
> association based on name patterns**. It is **not** proof of an individual's
> ethnicity, community identity, ancestry, or self-identification. Ambiguous and
> unknown cases are reported honestly, never forced into a category.

## Install

```bash
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
```

Requires Python 3.12+.

## The reference corpus

The labelled corpus (`fname, mname, sname, Tribe`, 154,599 rows) is **not
committed**. Place it at `data/corpus/reference_dataset_classified.xlsx`; ingest
verifies its SHA-256 against `data/corpus/MANIFEST.json`.

```bash
kne corpus ingest      # load the xlsx -> data/corpus.db (deterministic corpus_version)
kne corpus status      # sources, record count, tribe list, corpus_version
kne corpus build       # recompute derived tables from stored records
kne corpus report      # write data-quality reports to output/corpus/
```

`kne corpus report` writes `corpus_summary.md`, `surname_reference.csv`
(per-surname tribe distribution + support), `label_consensus_disagreement.csv`
(rows whose label fights the surname consensus — the correction queue) and
`tribe_support.md`.

**The corpus `Tribe` labels are LLM-derived** — a reference signal, not ground
truth. True accuracy will be measured against a separate, independently labelled
gold set (labels not derived from the name). Until then the engine reports
confidence and coverage, and asserts no headline accuracy number.

The original `tribes.txt` / `sname.txt` inputs are retired from the pipeline and
kept unchanged under `archive/` for audit (see `archive/SOURCES.md`).

## Classifying a dataset

```bash
kne classify input.xlsx -o output/run/result.xlsx
kne classify input.csv  -o output/run/result.csv --mode refine --tribe-col Tribe
```

Input may be `.csv`, `.tsv` or `.xlsx` (`--sheet` picks a worksheet). Columns are
auto-detected — `fname` / `first name` / `given name`, `sname` / `surname` /
`last name`, `tribe` / `ethnicity` / `community`, etc. — and `--fname-col`,
`--mname-col`, `--sname-col`, `--tribe-col` override the detection. The resolved
mapping is printed to stderr and recorded in the manifest.

`--mode auto` (default) runs **refine** when a tribe column with values exists,
otherwise **fresh**.

### Output

The format follows the `-o` extension:

- **`result.xlsx`** — a formatted workbook: **Classified Data** (original columns
  verbatim + appended `tribe_*` columns, frozen header, autofilter, rows
  colour-coded by status), **Summary** (run metadata + headline metrics + status
  and tribe breakdowns), **Review Queue** (rows needing a look, lowest confidence
  first), **Run Manifest**.
- **`result.csv`** / **`result.tsv`** — `result.csv` + `result.review.csv`
  (the `review` / `conflict` / `generic` / `unverified` rows) + `result.manifest.json`.

A `result.manifest.json` sidecar is always written. It records the input SHA-256,
`corpus_version`, evidence-dictionary hash, config digest, thresholds and
per-status counts — enough to reproduce the run exactly.

Appended columns: `tribe_predicted`, `tribe_confidence`, `tribe_status`,
`tribe_basis` (the evidence trail for the decision), `tribe_alt_candidates`, plus
`tribe_original` and `tribe_suggested` in refine mode. **Original labels are never
overwritten.**

### Statuses

| status | meaning |
|---|---|
| `assigned` | fresh mode, confident |
| `confirmed` | refine mode, engine agrees with the existing label |
| `refined` | an `Uncertain` label resolved to a community |
| `conflict` | confident, and disagrees with the existing label — original kept, engine pick in `tribe_suggested` |
| `review` | ambiguous — engine abstains |
| `generic` | name is non-informative / borrowed (Christian, Swahili, pan-Kenyan) |
| `unverified` | refine mode, existing label kept, engine could not corroborate |

## How it works

A hybrid **log-linear scorer** ([`src/kne/model/loglinear.py`](src/kne/model/loglinear.py)):

```
logit(t) = w_evidence · evidence_score(t)
         + Σ_position  w_position · ln P_smoothed(t | token, position)
         + w_combo     · ln P_smoothed(t | best name-combination)
posterior = softmax(logit / temperature)   over the 17 assignable communities
```

- **Evidence** comes from approved rows in `reference/name_dictionary.csv` only.
- **`P_smoothed`** is a Dirichlet-smoothed per-token / per-combination tribe
  distribution from the corpus; low-support tokens shrink toward the global prior.
- Pure arithmetic over a sorted tribe list — **deterministic, no RNG**.
- A **confidence gate** ([`src/kne/decide.py`](src/kne/decide.py)) turns the
  posterior into an assignment or an abstention, with a stricter bar for
  statistically sparse tribes and a "generic name" guard.

All tuning knobs live in `config/default.toml` (override with `--config`). The
shipped thresholds are hand-set starting points, to be tuned against the
independent gold set.

## Evaluating against a gold set

```bash
kne evaluate result.xlsx --gold gold.csv
```

`gold.csv` needs `fname,mname,sname,tribe_gold` and an optional `tier` column.
`kne evaluate` joins it to a `kne classify` output on the normalised
`(fname, mname, sname)` triple and writes `output/eval/evaluate_<gold>.md` +
`.json` with coverage, precision and the abstention breakdown — overall, per
tier, and per tribe — plus a coverage-at-precision sweep and the top confusions.
It changes nothing; re-run it after any corpus or config change as a regression
check.

## Project rules

Permanent constraints for all work in this repo are in
[`AGENTS.md`](AGENTS.md): source data is immutable, original spelling is
preserved, every classification has an auditable evidence trail, unknown and
ambiguous cases are not forced, generic names and broad morphological prefixes do
not independently determine a community, and actual ethnicity is never presented
as established from a name alone.

## Layout

```
src/kne/            the engine
  cli.py            `kne` entry point
  corpus/           ingest labelled xlsx -> SQLite store + derived reference tables
  reference.py      in-memory corpus + evidence layers
  features.py       per-record signal extraction
  model/            log-linear scorer
  decide.py         confidence gate -> status
  pipeline.py       read table -> classify -> write CSV/XLSX + manifest
  report_xlsx.py    formatted workbook writer
config/default.toml tuning knobs
reference/          evidence dictionary + admission-policy docs
tests/              pytest suite
archive/            retired source inputs and legacy staged-pipeline code (audit only)
```

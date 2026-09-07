# Archived source files

These files are the original, immutable inputs to the project. They are **retired
as pipeline inputs on 2026-09-06** — the engine now reads the labelled corpus at
`data/corpus/reference_dataset_classified.xlsx` instead — but are kept here
unchanged for audit, per AGENTS.md rule 1 ("Original source data must never be
modified" / "must remain available for audit and must not be silently relocated").

| file | original location | SHA-256 | rows |
|---|---|---|---|
| `tribes.txt` | repo root | `f7bfc6ecefef03a28c1052700ef5ed9b62d25add5b8952682a691df84b41c2f9` | 154,599 data rows (TSV: `fname`, `mname`, `sname`) |
| `sname.txt` | repo root | `67561b996ad9a99eea9c4a32912e0ee5cdb079afbbbc96bda3371b24a31e9dfc` | 154,599 data rows (one `sname` per line) |

The corpus Excel file is the 154,599 rows of `tribes.txt` with an LLM-populated
`Tribe` column, plus 17 rows where a compound first name was split into
`fname` / `mname`. See `data/corpus/MANIFEST.json`.

Hashes above are from the Stage 2 profile (`output/data_profile.md`). Verify with:

```bash
python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" archive/tribes.txt
```

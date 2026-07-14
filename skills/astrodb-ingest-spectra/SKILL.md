---
name: astrodb-ingest-spectra
description: "Generate and run a Python script that ingests spectra into an AstroDB Spectra table using astrodb_utils.spectra.ingest_spectrum. Use this skill when the user says: ingest spectra, add spectra to the database, populate the Spectra table, or provides a table of spectrum files/URLs and wants them loaded into database. Always use this skill even if the user only says 'ingest this spectrum' for a single file. Requires sources to already exist in the Sources table (run astrodb-ingest-sources first if they don't) and references to already exist in Publications. Works standalone or as the step after astrodb-ingest-sources."
compatibility: python, astropy, specutils, astrodb_utils
---

# Ingest Spectra Skill

Generate and run a Python script that ingests rows from a data table into the `Spectra`
table of an AstroDB SQLite database using `astrodb_utils.spectra.ingest_spectrum`.

Read `references/ingest_spectrum_api.md` before starting — it has the full signatures for
`check_spectrum_plottable`, `find_spectra`, and `ingest_spectrum`, plus common warnings and fixes.

Also before starting, copy the items from the `## Completion Checklist` at the bottom of this
document — verbatim and unchecked — into
`astrodb-ingest-artifacts/astrodb-ingest-spectra-checklist.md` (create the folder if needed;
overwrite any copy left by a previous run). The moment an item is done, flip its `[ ]` to `[x]` in
that file and add a one-line evidence note. Keep it current as you go — you will read it back
before reporting completion.

## Prerequisites

1. **`database.toml`** (astrodb-template-db layout) — required to load the database. Check
   for it in this order:
   1. A path the user explicitly stated in the conversation
   2. `database.toml` in the current working directory
   3. **If not found, stop and ask the user to provide it before continuing.**
2. **Packages**: `astrodb_utils`, `astropy`, `specutils`
3. **Data table**: CSV, ECSV, FITS, or any astropy/pandas-readable format, with at minimum
   a source-name column and either a spectrum URL/path column or enough info to build one.
4. **Sources already ingested** — every `source` value must already exist in the `Sources`
   table (with all its alternate names in `Names`). If sources are missing, **offer to run
   the `astrodb-ingest-sources` skill first** as a sub-step — do not just tell the user to
   do it manually and stop.
5. **Publications populated** — every `reference` value must already exist in `Publications`.
   If any are missing, offer to run `ingest_publication` as a sub-step.
6. **Instruments populated** — every `(telescope, instrument, mode)` combo must already exist
   in `Instruments`/`Telescopes`. If missing, offer to run `ingest_instrument` as a sub-step.
7. **Regimes** — every `regime` value (`optical`, `nir`, `mir`, etc.) must exist in `RegimeList`.

## Required Inputs

1. Path to the data table file (CSV, ECSV, FITS, etc.)
2. Path to `database.toml` (see Prerequisites #1)

---

## Step 1: Load and inspect the data table

```python
import pandas as pd
data = pd.read_csv("path/to/file.csv")  # or Table.read() for FITS/ECSV
print(data.columns.tolist())
print(data.head(3))
```

Show the user the **column names**, **dtypes**, and a **3-row preview**.

---

## Step 2: Reconcile source names against the Sources table

**Do not assume the data table's name column matches `Sources.source` exactly.** Names commonly
diverge when a source was ingested under its SESAME/SIMBAD-resolved canonical name while the
data table still uses the original discovery-paper name (stored as an alternate in `Names`).

For every unique name in the source-name column:

```python
def resolve_source_name(db, name):
    """Return the canonical Sources.source value for a name, checking Names.other_name too."""
    sources_tbl = db.query(db.Sources).table()
    if name in sources_tbl["source"]:
        return name
    names_tbl = db.query(db.Names).table()
    match = names_tbl[names_tbl["other_name"] == name]
    if len(match) == 1:
        return match["source"][0]
    if len(match) > 1:
        return None  # ambiguous — ask the user
    return None  # not found at all — ask the user
```

Build a `{data_table_name: canonical_source}` mapping. Report:
- Names that matched directly
- Names resolved via `Names.other_name` (show the mapping so the user can sanity-check it)
- Names with **no match** — these must be ingested first via `astrodb-ingest-sources`
  (offer to run it), or the row must be skipped with the user's confirmation

Use the **canonical name** (never the raw data-table name) as `source=` in every
`ingest_spectrum` call in Step 5.

---

## Step 3: Confirm column mappings

Ask the user to confirm the input file's column roles:

| Role | Required? | Notes |
|------|-----------|-------|
| Source name | **Yes** | Resolved via Step 2 |
| Spectrum permalink (URL) | **Yes** | See Step 3.5 — must be a real, stable URL |
| Local spectrum path | No | Only if the user has local files; passed as `local_spectrum` |
| Regime | **Yes** | Must exist in `RegimeList` |
| Telescope | **Yes** | Must exist in `Telescopes` |
| Instrument | **Yes** | Must exist in `Instruments` |
| Mode | **Yes** | Paired with telescope+instrument in `Instruments` |
| Observation date | **Yes** |  Parse to ISO format |
| Reference | **Yes** | Must exist in `Publications` |
| Original/raw spectrum URL | No | Passed as `original_spectrum` |
| Comments | No | |

### Step 3.5: Spectrum permalink — always ask, never assume a hosting pattern

The skill has **no default file host**. Ask the user directly:

> Where are your spectrum files hosted? I need either:
> (a) a column in your data table that already has full URLs, or
> (b) a base URL to prepend to a filename column (e.g. `https://your-bucket.s3.amazonaws.com/spectra/` + `filename`)
>
> Note: URL-encode special characters (e.g. `+` → `%2B`) if filenames contain them.

Never hardcode a specific bucket, domain, or path convention — construct the URL from
whatever the user provides this run.

---

## Step 4: Validate spectra before ingesting

For every row, **before** calling `ingest_spectrum`:

```python
from astrodb_utils.spectra import check_spectrum_plottable

try:
    check_spectrum_plottable(spectrum_url, raise_error=False, show_plot=False)
except Exception as e:
    # log and flag — do not silently skip; report to the user in the summary
    ...
```

Also run `find_spectra(db, source=canonical_source, reference=reference, regime=regime)`
first to check for existing duplicates — skip (with a logged reason) rather than double-ingest.

**Rows with a missing or unparseable `obs_date` cannot be ingested at all** — `observation_date`
is part of the `Spectra` table's composite primary key (source+regime+mode+obs_date+reference),
so it can't be null. Flag these rows and report them separately in the summary rather than
silently dropping them or guessing a date. Two spectra only count as true duplicates if they
match on **all five** PK columns — differing on any one (e.g. same source+regime but a
different `obs_date`) means both are legitimately distinct rows.

---

## Step 5: Write `astrodb-ingest-artifacts/ingest_{REF}_spectra.py`

Read `scripts/ingest_spectra.py` to understand the script pattern — variable names,
structure, logging setup, and ingest loop. **Do not copy it verbatim.** Write a
**tailored script** using the user's confirmed mappings from Steps 1–3, saved to
`astrodb-ingest-artifacts/ingest_{REF}_spectra.py` (use the data table's filename,
without extension, as `{REF}` — ask for a short label if it's long, same convention
as `astrodb-ingest-sources`).

The output script must:
- Use the canonical source names from Step 2, the user's real column names, file path, and
  `database.toml` location
- Call `build_db_from_json(settings_file=SETTINGS_FILE)`
- Run `check_spectrum_plottable` and `find_spectra` per row before `ingest_spectrum`
- Only pass optional params (`local_spectrum`, `obs_date`, `original_spectrum`, `comments`)
  that are actually present in the data
- Set `SAVE_DB = False` for the first run
- Use the dry-run log message: `"Dry run complete — NOT saved. Set SAVE_DB = True to write the database to JSON files."`
- **End with a comment block reporting the ingest results**, per the issue requirement:
  ```python
  # Ingest summary:
  # Total spectra attempted: N
  # Successfully ingested: X
  # Skipped (duplicate): Y
  # Skipped (not plottable / other error): Z
  ```
  Populate this by counting outcomes during the run, not with placeholder numbers.

Every variable must contain a real value — never write placeholder text to the file.

---

## Step 6: Run the script

Run `astrodb-ingest-artifacts/ingest_{REF}_spectra.py` with `SAVE_DB = False`. Report:
- How many spectra were ingested successfully
- Any rows skipped, with their specific reason (not-plottable, duplicate, unresolved source, etc.)
- Confirmation that the database was **not** saved

---

## Step 7: Confirm and save

After a successful dry run, ask the user:
> Ingestion preview complete: **X** ingested, **Y** skipped out of **Z** rows.
> Would you like to save these changes to the database? (Re-runs with `SAVE_DB = True`)

**Never set `SAVE_DB = True` automatically** — only on explicit user confirmation.

---

## Step 8 (optional): Visual QA notebook

`check_spectrum_plottable` only confirms a spectrum *loads* — not that it looks *right*
(wrong flux units, flipped/truncated axes, bad continuum can all still "plot fine"). If the
user asks for a visual check, generate a notebook (or a single multi-panel figure) that plots
every successfully-ingested spectrum with its source name, regime, and instrument as a title,
using matplotlib + specutils. Only build this on request — it's a QA convenience, not a
required part of ingestion.

---

## Completion Checklist

Track these items in `astrodb-ingest-artifacts/astrodb-ingest-spectra-checklist.md`, created at
the start of this skill. Flip a box to `[x]` only when verifiably done, with a one-line evidence
note. Never tick a box by claiming a check you didn't actually run.

Before telling the user spectra are ingested:

1. **Read the checklist file back.** Any unchecked box means you are not done.
2. **Reproduce the checklist in your completion message**, each item with its evidence note.

- [ ] `database.toml` was located (asked the user rather than inventing one when not found).
- [ ] Every source name in the data table was resolved to a canonical `Sources.source` value
      via Step 2 (direct match or `Names.other_name` lookup) — unresolved names were flagged
      and `astrodb-ingest-sources` was offered as a sub-step, not silently skipped.
- [ ] Every reference, telescope/instrument/mode combo, and regime was confirmed to exist in
      `Publications`/`Instruments`/`RegimeList` — missing ones were offered as sub-steps.
- [ ] The user was asked directly for the spectrum permalink source (URL column or base URL +
      filename column) — no hosting pattern was assumed or hardcoded.
- [ ] `check_spectrum_plottable` and `find_spectra` were run per row before `ingest_spectrum`.
- [ ] The tailored script at `astrodb-ingest-artifacts/ingest_{REF}_spectra.py` uses real column names/paths, only
      includes optional params present in the data, and sets `SAVE_DB = False`.
- [ ] The script ends with a comment block reporting real ingested/skipped counts (not
      placeholder numbers).
- [ ] A dry run was executed and results (ingested/skipped with reasons) were reported to the user.
- [ ] `SAVE_DB = True` was set **only** after explicit user confirmation.
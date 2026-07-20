---
name: astrodb-ingest-photometry
description: "Generate and run a Python script that ingests photometry (magnitudes / brightness measurements) into an AstroDB Photometry table from a data table. Use this skill when the user says: ingest photometry, add magnitudes, add brightness measurements, populate the Photometry table, add JHK/WISE/SDSS/Gaia magnitudes, or provides a FITS/CSV/ECSV file with magnitude columns and wants them in the database. Sets up the required PhotometryFilters, Telescopes, and Instruments (from SVO filter IDs) before the magnitudes. Works standalone or as the step after astrodb-ingest-sources."
compatibility: python, astropy, astrodb_utils
---

# Ingest Photometry Skill

Generate and run a Python script that ingests rows from a data table into the `Photometry`
table of an AstroDB SQLite database using `astrodb_utils.photometry.ingest_photometry`. Because a
photometry measurement points at a **band**, a **source**, and a **reference**, this skill also makes
sure the band's `PhotometryFilters` row (and its `Telescopes` / `Instruments` rows) exist **before**
any magnitude is ingested — using SVO Filter Profile Service IDs for band names.

Read `references/ingest_photometry_api.md` before starting — it has the full signatures for
`ingest_photometry` / `ingest_photometry_filter` / `fetch_svo`, the SVO band-ID rules, and common
warnings with fixes.

## Step 0: Read context documents

1. Read `references/astrodb-directions.md` — it defines the `workflow.md`, artifact-folder, and
   completion-checklist conventions this skill follows.
2. Check whether `workflow.md` exists in the current working directory. If it does, read it
   to carry forward context from prior skills.
3. Record this skill's checklist per the completion-checklist convention — create the artifact
   directory if needed, then add a `## astrodb-ingest-photometry` section holding the items from
   `## Completion Checklist` (bottom of this file) to `astrodb-ingest-artifacts/checklists.md`.

## Prerequisites

1. **`database.toml`** (astrodb-template-db layout) — required to load the database. Check for it in
   this order:
   1. A path the user explicitly stated in the conversation
   2. `database.toml` in the current working directory
   3. **If not found, stop and ask the user to provide it before continuing.**
      Do not attempt to build the database without it.
2. **Packages**: `astrodb_utils`, `astropy`.
3. **Data table**: FITS, CSV, ECSV, or any astropy-readable format, with at minimum a source name
   column, at least one magnitude column, and a reference column.
4. **Publications table populated**: every `reference` value must already exist in `Publications`.
   If any reference is missing, **offer to run `astrodb-ingest-publications` as a sub-step** before
   proceeding — do not just tell the user to do it manually and stop.
5. **Sources table populated**: every `source` must already exist in `Sources` (or resolve through
   `Names`). Photometry attaches to an existing source; it does **not** create one. If sources are
   missing, **offer to run `astrodb-ingest-sources` as a sub-step** first.
6. **Internet (required)**: filter setup queries the SVO Filter Profile Service for each band's
   effective wavelength and width. Without it, `PhotometryFilters` rows cannot be created.

## Required Inputs

1. Path to the data table file (CSV, ECSV, FITS, etc.)
2. Path to `database.toml` — check in order:
   1. A path the user explicitly stated in the conversation
   2. `database.toml` in the current working directory (root of the project)
   3. If not found, ask the user for the path before continuing

---

## Step 1: Load and inspect the data table

```python
from astropy.table import Table
data = Table.read("path/to/file.fits")  # astropy auto-detects .fits, .csv, .ecsv
# If auto-detect fails: Table.read(..., format="fits")
print(data.colnames)
print(data[:3])
```

Show the user the **column names**, **dtypes**, and a **3-row preview** so they can confirm the
mapping in the next steps. Note that photometry tables are frequently **wide** — one magnitude column
per band (`Jmag`, `Hmag`, `W1mag`, `gmag`, …) plus matching error columns (`e_Jmag`, `Jmag_err`, …).
Identify every band column and its error column now.

## Step 2: Reconcile source names against the Sources table

Every measurement attaches to an existing `Sources.source`. Before writing the script, resolve each
name in the data table so unresolved ones are caught early rather than at ingest time. Use
`find_source_in_db`, which checks `Sources` and its `Names` aliases (the same lookup
`ingest_photometry` does internally):

```python
from astrodb_utils.sources import find_source_in_db

name_map = {}      # {data_table_name: canonical Sources.source}
unresolved = []    # names with no unique match
for raw in set(str(r) for r in data[SOURCE_COL]):
    matches = find_source_in_db(db, raw)   # list of matched source names
    if len(matches) == 1:
        name_map[raw] = matches[0]
    else:
        unresolved.append(raw)             # 0 matches, or ambiguous
```

- **All resolve** → confirm and move on.
- **Some unresolved** → show the list. These sources must be ingested first — **offer to run
  `astrodb-ingest-sources`** for them, or let the user correct the names. Do not invent sources.

Always pass the **canonical** name (`name_map[raw]`) as `source=` in the script.

## Step 3: Confirm column mappings

Present the actual column names from Step 1 and confirm the role of each. Do **not** assume defaults.

| Role | Required? | Notes |
|------|-----------|-------|
| Source name | **Yes** | Resolved to `Sources.source` in Step 2 |
| Band / magnitude columns | **Yes** | One per band; the column value is the magnitude |
| Magnitude error | No | The matching `e_*` / `*_err` column for each band |
| Reference | **Yes** | Must already exist in `Publications` |
| Telescope | No | If given, must exist in `Telescopes` (Step 4 creates it) |
| Epoch | No | Observation epoch (float, e.g. decimal year) |
| Regime | No | e.g. `optical`, `infrared`; only written if present |
| Comments | No | |

**Flag, don't silently drop:** `ingest_photometry` supports only a **symmetric** `magnitude_error`.
If the table has asymmetric `magnitude_error_upper` / `magnitude_error_lower` columns, tell the user
these are not supported by the helper and ask how to proceed (e.g. use one side, average, or skip the
uncertainty) rather than dropping them silently.

For a wide table, record which magnitude column maps to which **band**, and which error column pairs
with it — this feeds both Step 4 (filter setup) and the ingest loop.

## Step 4: Resolve bands to SVO IDs and set up filters/telescopes/instruments FIRST

`ingest_photometry` will **reject** a measurement whose `band` is not already a row in
`PhotometryFilters`. So resolve and create the filters before any magnitude is ingested.

1. **Map each band to an SVO Filter Profile Service ID** (`Facility/Instrument.Band`). See the table
   in `references/ingest_photometry_api.md` (and `astrodb-build-schema-match/references/photometry-filters.md`).
   Examples: `J → 2MASS/2MASS.J`, `W1 → WISE/WISE.W1`, `g → SDSS/SDSS.g`, `G → Gaia/Gaia3.G`,
   `V → Generic/Johnson.V`.
   **If a band's telescope/instrument is ambiguous** (e.g. a bare `V` that could be Johnson or Gaia),
   **stop and ask the user** to confirm the SVO ID — do not guess.

2. **Check which SVO IDs already exist**, and create the missing ones. `ingest_photometry_filter`
   fetches the filter's metadata from SVO and, as a side effect, **creates the `Telescopes` row and
   the `Instruments` row (mode `"Imaging"`)** if they are missing — this is how telescope/instrument
   get set up "first":

   ```python
   from astrodb_utils import AstroDBError
   from astrodb_utils.photometry import ingest_photometry_filter

   # BAND_SETUP: {svo_id: (telescope, instrument, filter_name)} for every band in the data
   for svo_id, (telescope, instrument, filter_name) in BAND_SETUP.items():
       exists = db.query(db.PhotometryFilters).filter(
           db.PhotometryFilters.c.band == svo_id
       ).table()
       if len(exists):
           continue
       try:
           ingest_photometry_filter(
               db, telescope=telescope, instrument=instrument, filter_name=filter_name
           )
       except AstroDBError as e:
           # already-present is fine; a genuine SVO/lookup failure needs the user
           logger.warning(f"Filter {svo_id}: {e}")
   ```

   The SVO ID that ends up in `PhotometryFilters.band` is what `fetch_svo` returns for
   `{telescope}/{instrument}.{filter_name}` — so the `band` you later pass to `ingest_photometry`
   must be that **same** SVO ID string.

Report to the user which filters/telescopes/instruments were created vs already present before moving
on.

## Step 5: Write `astrodb-ingest-artifacts/ingest_{LABEL}_photometry.py`

Read `scripts/ingest_photometry.py` to understand the pattern — config block, the filter-setup phase,
the ingest loop, and the summary. Then write a **tailored script** using the confirmed mappings.
`{LABEL}` is the input file name without extension (ask for a short label if it is very long).

Do not copy `scripts/ingest_photometry.py` verbatim. The output script must:

- Use the user's actual column names, file path, and `database.toml` location.
- Call `build_db_from_json(settings_file=SETTINGS_FILE)`.
- Set `BANDS` (one `(magnitude_column, svo_id, error_column, telescope)` entry per band column) and
  `BAND_SETUP` (`{svo_id: (telescope, instrument, filter_name)}`) from Steps 3–4, and
  `SOURCE_NAME_MAP` to the canonical names from Step 2.
- Run the **filter-setup phase before** the photometry loop.
- Ingest each (source, band) magnitude with `ingest_photometry(..., raise_error=True)` inside a
  try/except, bucketing skips by reason (duplicate / band-missing / source-missing / reference-missing
  / other) from the `AstroDBError` message.
- Only include optional arguments (`magnitude_error`, `telescope`, `epoch`, `regime`, `comments`)
  that are actually present.
- Set `SAVE_DB = False`.
- Use the dry-run log message: `"Dry run complete — NOT saved. Set SAVE_DB = True to write the database to JSON files."`

Every variable must contain a real value — never write placeholder text to the file.

## Step 6: Dry run

Run `astrodb-ingest-artifacts/ingest_{LABEL}_photometry.py` with `SAVE_DB = False`. Report:

- Which filters / telescopes / instruments were created (or already existed).
- How many measurements were ingested successfully.
- How many were skipped, **grouped by reason** (duplicate, band not in PhotometryFilters, source not
  found, reference not in Publications, other), with the warning for each.
- Confirmation that the database was **not** saved.

See `references/ingest_photometry_api.md` for the common-warnings table and how to fix each one.

## Step 7: Confirm and save

After a clean dry run, ask the user:
> Ingestion preview complete: **X** measurements ingested, **Y** skipped out of **Z** rows
> (filters created: **N**). Save these changes to the database? (Re-runs with `SAVE_DB = True`)

**Never set `SAVE_DB = True` automatically** — only on explicit user confirmation.

## Final Step: Update `workflow.md`

Follow the convention in `references/astrodb-directions.md`. Append one new entry to `workflow.md` in
the current working directory (create it with the standard header if it doesn't exist yet). Record:
which bands were resolved to which SVO IDs (and any that needed user confirmation), which
filters/telescopes/instruments were created, how many measurements were ingested / skipped and why,
and whether the user explicitly confirmed before saving.

## Completion Checklist

Before telling the user photometry is ingested, verify every item in your section of the workflow
checklist file and reproduce the evidence-annotated list here, per the **completion-checklist
convention** in `references/astrodb-directions.md`.

- [ ] `database.toml` was located (you asked the user rather than inventing one when it wasn't found).
- [ ] Every source name was resolved to a unique `Sources.source` (directly or through `Names`), and any that did not resolve were flagged — with `astrodb-ingest-sources` offered as a sub-step rather than inventing sources or ingesting against a non-existent one.
- [ ] Every `reference` already exists in `Publications` — and for any that were missing, you offered to run `astrodb-ingest-publications` rather than just telling the user to do it.
- [ ] Every band was mapped to a **verified SVO filter ID**, ambiguous bands were confirmed with the user rather than guessed, and its `PhotometryFilters` / `Telescopes` / `Instruments` rows were ensured to exist **before** any magnitude was ingested.
- [ ] If the data had asymmetric `magnitude_error_upper` / `magnitude_error_lower` columns, you told the user they are not supported by `ingest_photometry` and asked how to handle them rather than dropping them silently.
- [ ] The tailored script at `astrodb-ingest-artifacts/ingest_{LABEL}_photometry.py` uses the user's real column names, paths, `BANDS` / `BAND_SETUP`, and `SOURCE_NAME_MAP`, includes only optional columns that are actually present, and sets `SAVE_DB = False`.
- [ ] A dry run was executed, and you reported how many measurements were ingested / skipped (grouped by reason, with warnings) plus which filters were created, and that the database was not saved.
- [ ] `SAVE_DB = True` was set **only** after the user explicitly confirmed — never automatically.

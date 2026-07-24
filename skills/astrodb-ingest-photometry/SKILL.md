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
any magnitude is ingested — using SVO Filter Profile Service IDs for band names. The band's SVO filter
also lets the skill figure out the `telescope` and the `regime` for each measurement, so those don't
have to be columns the user maps by hand.

Read `references/ingest_photometry_api.md` before starting — it has the full signatures for
`ingest_photometry` / `ingest_photometry_filter` / `fetch_svo`, the SVO band-ID rules, and common
warnings with fixes.

## Step 0: Read context documents

1. Read `references/astrodb-ingest-directions.md` — the conventions for the ingest workflow: the
   `ingest-workflow.md` decision log and the completion-checklist convention. It points to
   `references/astrodb-directions.md` for the shared artifact-folder and "ask, don't assume" rules.
2. If `astrodb-ingest-artifacts/ingest-workflow.md` exists, read it to carry forward context from
   prior ingest skills.

(The ingest skills **verify** their completion checklist and report it in the final message — they do
not write it out to a file. See `references/astrodb-ingest-directions.md`.)

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
| Magnitude error | No | The matching `e_*` / `*_err` column for each band (symmetric) |
| Reference | **Yes** | Must already exist in `Publications` |
| Epoch | No | Decimal year the measurement was taken. Optional, but **encourage the user to include it** when the data has it — an undated magnitude is much less useful later. |
| Comments | No | |
| Telescope | Derived | The band's telescope, from its SVO filter (Step 4) — not a column you map by hand |
| Regime | Derived | Figured out from the band's SVO effective wavelength (Step 4) — not a column you map by hand |

**Asymmetric errors — supported by the table, just not by the helper.** The `Photometry` table has
`magnitude_error_upper` and `magnitude_error_lower` columns, but `ingest_photometry` only accepts a
single symmetric `magnitude_error`. If the data has asymmetric error columns, don't drop them and
don't silently collapse them: use `ingest_photometry` as a **reference** to write a small custom
insert that validates source/band/reference the same way and populates
`magnitude_error_upper` / `magnitude_error_lower` directly (see "Ingesting asymmetric errors" in
`references/ingest_photometry_api.md`). Confirm the column mapping with the user first.

**Uniqueness is `(source, band, reference)`** — `epoch` is **not** part of the key. If the table has
more than one measurement of the same source in the same band from the same reference (e.g. a
time series across epochs), only one row fits this key; the rest will come back as duplicates. Flag
this to the user rather than silently losing rows.

For a wide table, record which magnitude column maps to which **band**, and which error column pairs
with it — this feeds both Step 4 (filter setup) and the ingest loop.

## Step 4: Resolve bands to SVO IDs; set up filters/telescopes/instruments and derive regimes FIRST

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

3. **Derive each band's `regime` from its SVO effective wavelength.** Setting up the filter stored
   `effective_wavelength_angstroms` in `PhotometryFilters`; bin it into a regime and resolve that
   against the controlled `RegimeList` with `get_db_regime` (case- and hyphen-insensitive):

   ```python
   from astrodb_utils.utils import get_db_regime

   def regime_from_wavelength(wave_ang):
       if wave_ang < 3000:   return "ultraviolet"
       if wave_ang < 10000:  return "optical"
       if wave_ang < 30000:  return "nir"      # near-infrared (J/H/K)
       return "mir"                            # mid-infrared (WISE, etc.)

   eff = db.query(db.PhotometryFilters).filter(
       db.PhotometryFilters.c.band == svo_id).table()["effective_wavelength_angstroms"][0]
   regime = get_db_regime(db, regime_from_wavelength(eff), raise_error=False)
   ```

   `get_db_regime` returns the canonical `RegimeList` value, or `None` if that regime isn't in the
   table (its warning prints the available regimes). If it's `None`, **ask the user** — either add the
   regime to `RegimeList` or pick an existing one; don't guess, and don't try to ingest a regime that
   isn't in the controlled list (it would fail the foreign key). Keep a `{svo_id: regime}` map for the
   ingest loop, alongside each band's `telescope`.

Report to the user which filters / telescopes / instruments / regimes were created (or already
present) before moving on.

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
- Pass `telescope` and `regime` — both **figured out from each band's SVO filter** in Step 4, not left
  blank just because they weren't columns in the table — plus the optional `magnitude_error`, `epoch`,
  and `comments` when the data has them.
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

## Final Step: Update `ingest-workflow.md`

Follow the convention in `references/astrodb-ingest-directions.md`. **Prepend** one dated entry (most
recent on top) to `astrodb-ingest-artifacts/ingest-workflow.md` (create it with the standard header if
it doesn't exist). Record: which bands resolved to which SVO IDs (and any confirmed with the user), the
regimes derived, which filters / telescopes / instruments / regimes were created, how many measurements
were ingested / skipped and why, and whether the user confirmed before saving.

## Completion Checklist

Before telling the user photometry is ingested, verify every item in the checklist below, per the
**completion-checklist convention** in `references/astrodb-ingest-directions.md` — verify and report
each item in your final message; do **not** write the checklist out to a file.

- [ ] `database.toml` was located (you asked the user rather than inventing one when it wasn't found).
- [ ] Every source name was resolved to a unique `Sources.source` (directly or through `Names`), and any that did not resolve were flagged — with `astrodb-ingest-sources` offered as a sub-step rather than inventing sources or ingesting against a non-existent one.
- [ ] Every `reference` already exists in `Publications` — and for any that were missing, you offered to run `astrodb-ingest-publications` rather than just telling the user to do it.
- [ ] Every band was mapped to a **verified SVO filter ID**, ambiguous bands were confirmed with the user rather than guessed, and its `PhotometryFilters` / `Telescopes` / `Instruments` rows were ensured to exist **before** any magnitude was ingested.
- [ ] Each band's `regime` was derived from its SVO effective wavelength and resolved against `RegimeList` (adding it, or picking an existing one with the user, when `get_db_regime` returned nothing), and `telescope` was populated on the `Photometry` rows.
- [ ] If the data had asymmetric `magnitude_error_upper` / `magnitude_error_lower` columns, you wrote a custom script (modeled on `ingest_photometry`) to ingest them into those columns rather than dropping or silently collapsing them.
- [ ] The user was encouraged to include `epoch` when the data had it.
- [ ] The tailored script at `astrodb-ingest-artifacts/ingest_{LABEL}_photometry.py` uses the user's real column names, paths, `BANDS` / `BAND_SETUP`, and `SOURCE_NAME_MAP`, and sets `SAVE_DB = False`.
- [ ] A dry run was executed, and you reported how many measurements were ingested / skipped (grouped by reason, with warnings) plus which filters were created, and that the database was not saved.
- [ ] `SAVE_DB = True` was set **only** after the user explicitly confirmed — never automatically.

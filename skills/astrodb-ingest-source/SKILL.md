---
name: ingest-sources
description: "Generate and run a Python script that ingests sources (astronomical objects) into an AstroDB Sources table from a data table. Use this skill when the user says: ingest sources, ingest objects, add new sources to the database, add objects to the database, or provides a FITS/CSV/ECSV file and wants to populate the Sources table. Works standalone or as the step after match-schema."
compatibility: python, astropy, astrodb_utils, astroquery
---

# Ingest Sources Skill

Generate and run a Python script that ingests rows from a data table into the `Sources`
table of an AstroDB SQLite database using `astrodb_utils.sources.ingest_source`.

Read `references/ingest_source_api.md` before starting — it has the full signature,
parameter meanings, and common warnings with fixes.

## Prerequisites

1. **`database.toml`** (astrodb-template-db layout) — this file is required to load the
   database. Check for it in this order:
   1. A path the user explicitly stated in the conversation
   2. `database.toml` in the current working directory
   3. **If not found, stop and ask the user to provide it before continuing.**
      Do not attempt to build the database without it.
2. **Packages**: `astrodb_utils`, `astropy`, `astroquery`
3. **Data table**: FITS, CSV, ECSV, or any astropy-readable format, with at minimum a source name column and a discovery reference column.
4. **Publications table populated**: every `reference` value must already exist in
   `Publications`. If any reference is missing, **offer to run `ingest_publication`
   as a sub-step** before proceeding with source ingestion — do not just tell the user
   to do it manually and stop.
5. **Internet (recommended)**: `ingest_source` queries SIMBAD for coordinates when
   RA/Dec are not in the table.

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
data = Table.read("path/to/file.fits") # astropy auto detects .fits, .csv, .ecsv
# If auto-detect fails: Table.read(..., format="fits")
print(data.colnames)
print(data[:3])
```

Show the user the **column names**, **dtypes**, and a **3-row preview** so they can confirm mapping in the next step.
**Common FITS dtype display:**
 
| Raw dtype | Meaning |
|-----------|---------|
| `>f8` | float64 |
| `>f4` | float32 |
| `>i4` | int32 |
| `\|S12` | fixed-length string |

---

## Step 2: Confirm column mappings
Ask the user to confirm two things: **(A) input file columns** and **(B) DB schema column names**.

### A. Input file columns
 
Present the actual column names from Step 1 — **do not assume defaults**.

| Role | Required? | Notes |
|------|-----------|-------|
| Source name | **Yes** | String column |
| Discovery reference | **Yes** | Must already exist in `Publications` |
| RA (decimal degrees) | No | If absent → SIMBAD fallback |
| Dec (decimal degrees) | No | If absent → SIMBAD fallback |
| Epoch | No | e.g. `"2000.0"` |
| Equinox | No | e.g. `"J2000"` |
| Comment | No | |
| Other reference | No | |

Example prompt to user:
> The table has these columns: `Name, RA, Dec, Dist, Reference`
> Which column is the source name? Which is the discovery reference?


After confirmation, use the **input file name** (without extension) as `{REF}` to
name the output script — e.g. `NearbyGalaxies_Jan2021_PUBLIC` →
`tmp/ingest_NearbyGalaxies_Jan2021_PUBLIC_sources.py`. If the filename is very long,
ask the user for a short label to use instead (e.g. `Burg24`).

### B. DB schema column names
 
These are the column names **in the database `Sources` table** — not the input file.
They vary by database. **Always ask the user which DB they are targeting**, then use the
known defaults for that DB:
 
| Database | ra_col_name | dec_col_name | epoch_col_name |
|----------|-------------|--------------|----------------|
| astrodb-template-db | `ra_deg` | `dec_deg` | `epoch_year` |
| SIMPLE-db | `ra` | `dec` | `epoch` |
| Unknown | **ask the user** | **ask the user** | **ask the user** |
 
To check an unknown DB:
```python
# Note: the Sources table name may vary (e.g. "sources", "galaxies") —
# ask the user if their DB uses a non-standard table name before running this.
print(db.metadata.tables["Sources"].columns.keys())
```

**Example prompt:**
> Which database are you ingesting into — SIMPLE-db, astrodb-template-db, or another?
> (This determines the column names used internally for RA, Dec, and epoch.)


---

## Step 3: Write `tmp/ingest_{REF}_sources.py`

Read `scripts/ingest_source.py` to understand the script pattern — variable names,
structure, logging setup, and ingest loop. Then write a **tailored script**
using the user's confirmed mappings from Steps 1–2.
 
Do not copy `scripts/ingest_source.py` verbatim. The output script must:
- Use the user's actual column names, file path, and `database.toml` location
- Call `build_db_from_json(settings_file=SETTINGS_FILE)`
- Only include optional columns (EPOCH_COL, EQUINOX_COL, etc.) that are present in the data
- Use the correct `ra_col_name`, `dec_col_name`, `epoch_col_name` for the target DB
- Set `SAVE_DB = False`
- Use the dry-run log message: `"Dry run complete — NOT saved. Set SAVE_DB = True to write the database to JSON files."`
Every variable must contain a real value — never write placeholder text to the file.

---

## Step 4: Run the script

Run `tmp/ingest_{REF}_sources.py` with `SAVE_DB = False`. Report:

-  How many sources were ingested successfully
- Any rows skipped with their warning messages
- Confirmation that the database was **not** saved

See `references/ingest_source_api.md` for the common warnings table and how to fix each one.


## Step 5: Confirm and save

After a successful dry run, ask the user:
> Ingestion preview complete: **X** ingested, **Y** skipped out of **Z** rows.
> Would you like to save these changes to the database? (Re-runs with `SAVE_DB = True`)

**Never set `SAVE_DB = True` automatically** — only on explicit user confirmation.
---
name: astrodb-build-schema-validate
description: Validate an AstroDB schema mapping by checking that data columns are compatible with the schema fields they've been mapped to. Use this skill whenever the user has completed a schema mapping (e.g., from the astrodb-build-schema-match skill) and wants to check whether the actual data is safe to ingest — specifically (1) are there null values in data columns that map to non-nullable schema fields, and (2) do data column types match the expected types in schema.yaml? Always use this skill proactively after astrodb-build-schema-match produces a mapping, before the user proceeds to write ingestion code. Trigger on phrases like "validate","check my mapping", "will this ingest cleanly", "are there any type mismatches", "null check", "nullable violations", or "verify schema compatibility".
compatibility: python, astropy, pyyaml
metadata:
  authors: ["Claude"]
---

# Validate Schema Mapping

Check that a completed column mapping is safe to ingest by comparing what the data actually
contains against what the schema requires.

## Step 0: Read context documents

1. Read `references/astrodb-directions.md` (shared conventions) and
   `references/astrodb-build-directions.md` (build specifics: the `build-workflow.md` decision log and the
   `checklists.md` completion-checklist tracking).
2. Check whether `astrodb-build-artifacts/build-workflow.md` exists. If it does, read it
   to carry forward context from prior skills.
3. Check whether `astrodb-build-artifacts/directions.md` exists. If it does, read it — it may describe
   known nullable or type edge cases relevant to this validation.
4. Record this skill's checklist per the completion-checklist convention — create the artifact
   directory if needed, then add a `## astrodb-build-schema-validate` section holding the items from
   `## Completion Checklist` (bottom of this file) to `astrodb-build-artifacts/checklists.md`.

Two classes of problems can block a clean ingest:
1. **Nullable violations** — the schema marks a field as `nullable: false`, but the data
   column has missing/null values. Inserting these rows will raise a database constraint error.
2. **Type mismatches** — the schema specifies a type (e.g., `double`, `string`, `boolean`)
   but the data column holds a different type (e.g., a float column mapped to a string field,
   or a string column mapped to a numeric field). These may cause silent truncation, coercion
   errors, or failed inserts.

## Inputs

You need three things:

1. **The mapping table** — the markdown table from astrodb-build-schema-match, with columns:
   `Input Column | Description | Units | Type | DB Table | DB Field | Confidence | Notes`
   (or a similar structure — adapt if column names differ slightly)

2. **The data file path** — the original astronomical table (FITS, CSV, ECSV, HDF5, VOTable, etc.)

3. **The schema.yaml path** — the Felis-format schema file for the target database.
   Common locations to check if not provided: `schema/schema.yaml`, `schema.yaml`,
   `<db-name>/schema.yaml`. Ask the user if you can't find it.

If the user doesn't provide the data file or schema.yaml paths, ask for them before
proceeding — you cannot do this validation without both.

## Step 1: Parse the schema.yaml

Load the schema.yaml using PyYAML. For each table, extract every column's `name`, `datatype`,
`nullable` (defaults to `true` if absent), and any `length` constraint. Build a lookup
structure indexed as `schema_fields[table_name][field_name]` → `{datatype, nullable, length}`.

The Felis `datatype` values map to Python/numpy types roughly as:

| Felis datatype | Compatible Python/numpy types |
|---|---|
| `string` | `str`, `object`, `bytes` |
| `double` | `float64`, `float32`, `float16` |
| `float` | `float32`, `float64` |
| `int` / `long` | `int32`, `int64`, `int16`, `int8` |
| `boolean` | `bool` |
| `timestamp` | `datetime64`, `str` (ISO format) |

A float32 mapped to a `double` field is **compatible** (widening). A string mapped to a
`double` field is **incompatible**. Use broad compatibility rather than strict equality —
the goal is to catch real problems, not flag harmless precision differences.

## Step 2: Load the data and check each mapping

For each row in the mapping table where DB Table and DB Field are filled in (skip unmapped
rows and rows mapped to "—" or "N/A"):

Write a short Python script to:
- Load the data file. First check for the sidecar written by astrodb-build-parse-table:
  ```python
  import json, os
  sidecar = "astrodb-build-artifacts/astrodb-parse-result.json"
  if os.path.exists(sidecar):
      meta = json.load(open(sidecar))
      reader      = meta["reader"]        # "astropy" or "pandas"
      fmt         = meta["format"]        # astropy format hint, or None
      pandas_meth = meta["pandas_method"] # e.g. "read_csv", or None
  else:
      reader, fmt, pandas_meth = "astropy", None, None
  ```
  Then load with the same reader that astrodb-build-parse-table already verified:
  ```python
  from astropy.table import Table
  import pandas as pd

  if reader == "astropy":
      kwargs = {"format": fmt} if fmt else {}
      t = Table.read(data_file, **kwargs)
  else:
      t = getattr(pd, pandas_meth)(data_file)
  ```
  Fall back to `astropy.table.Table.read()` with no arguments if neither path works.
- (use `astropy.table.Table.read()` — it handles FITS, ECSV, CSV, VOTable, HDF5)
- For each mapped column:
  - Count null/missing values: `np.sum(np.isnan(col))` for floats, `np.sum(col == None)` / masked array checks for strings. For FITS masked arrays, check `.mask` if present.
  - Get the column's numpy dtype

Save the script to `astrodb-build-artifacts/validate_mapping.py` and run it to get the per-column null counts and dtypes.

## Step 3: Produce the validation report

Follow the exact report structure in `references/validation-report.md`, and write the full report
to `astrodb-build-artifacts/schema-validation-report.md` with the Write tool — the same
`astrodb-build-artifacts/` directory the Step 2 script went to. Tell the user the path.

## Edge cases to handle gracefully

- **Column not in data file**: warn that the mapped column name wasn't found in the data —
  this usually means the mapping used a renamed/transformed column, not the raw column name.
- **Schema field not found**: warn if a DB Table/Field from the mapping doesn't exist in
  schema.yaml — possible if the mapping used a custom table.
- **All-null columns**: flag these explicitly — they'll violate any non-nullable constraint
  and may indicate a parsing problem upstream.
- **FITS masked arrays**: treat masked values as nulls.
- **String columns with empty strings**: count `""` as effectively null for non-nullable
  string fields — empty strings often slip through where None would be caught.

## Completion Checklist

Before telling the user validation is done, verify every item in your section of the workflow checklist file and reproduce
the evidence-annotated list here, per the **completion-checklist convention** in
`references/astrodb-build-directions.md`.

- [ ] You had the mapping table, the data file path, and the schema.yaml path — asking the user for any that were missing rather than guessing.
- [ ] You parsed schema.yaml for each field's datatype, nullable flag, and length.
- [ ] You ran a script (saved to `astrodb-build-artifacts/validate_mapping.py`) that loaded the data with the reader recorded in the parse-table sidecar when present and, for each mapped column, counted null/missing values — including FITS masked values and empty strings for non-nullable string fields — and read its dtype.
- [ ] You checked both classes of problem: nullable violations and type mismatches (using broad compatibility, not strict equality).
- [ ] Edge cases were handled (column not in data, field not in schema, all-null columns) rather than crashing or skipping silently.
- [ ] You wrote the validation report to `astrodb-build-artifacts/schema-validation-report.md` (structured per `references/validation-report.md`) and told the user the path.

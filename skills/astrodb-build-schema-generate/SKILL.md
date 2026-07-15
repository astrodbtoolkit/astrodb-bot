---
name: astrodb-build-schema-generate
description: Generate a Felis YAML schema for a user-provided astronomical data file, using the output of the astrodb-build-schema-match and astrodb-build-schema-validate skills. Produces a standards-compliant schema.yaml covering each mapped table and column, with proper Felis syntax (@id references, datatypes, nullable flags, units, and foreign key constraints). Always use this skill when the user has completed a schema mapping (with or without validation) and wants to produce a Felis YAML, create a schema file for their data, generate schema.yaml, export their mapping as a schema, or document their database tables. Also trigger when the user says "generate schema", "create felis yaml", "make a schema file", or "turn this mapping into a schema".
compatibility: python, pyyaml
metadata:
  authors: ["Claude"]
---

# Generate Felis Schema

Take a completed AstroDB schema mapping — and optionally a validation report — and produce a
well-formed Felis YAML schema file covering all the tables and columns that will be populated
by the user's data.

## What is Felis YAML?

Felis is the schema description language used by AstroDB and LSST. A Felis YAML file defines
tables, columns, datatypes, constraints, and metadata in a format that tools can use to create
and validate databases. The canonical spec is at https://felis.lsst.io/.

Read `references/felis-syntax.md` for the exact syntax rules and examples before writing any YAML.

## Step 0: Confirm the schema name

**Before doing anything else**, ask the user what to name the schema:

> What should I call this schema? This becomes the top-level `name:` in `schema.yaml` and
> the SQLite filename (e.g. `mirion` → `mirion.sqlite`). It should match your database name,
> not the template default.

Wait for an explicit answer. Do not derive the name silently from the data file name, from
the existing `schema.yaml`, or from any other source — the name the user types here is the
only acceptable value.

**Never accept `astrodb_template`, `astrodb-template`, or `template` as the schema name.**
If the user types one of these, tell them that is the template placeholder and ask them to
provide the actual dataset name.

Hold this name for use in Step 3 (`name:` and `@id:`) and Step 4 (output filename).

## Inputs

You need at minimum:

1. **The mapping table** from `astrodb-build-schema-match` — rows like:
   `Input Column | Description | Units | Type | DB Table | DB Field | Confidence | Notes`

2. **Schema name** — confirmed in Step 0 above. Do not re-derive or re-ask here.

Optionally also accept:

3. **The validation report** from `astrodb-build-schema-validate` — identifies nullable violations
   and type mismatches. If provided, use it to set `nullable` flags and resolve type conflicts.

4. **The data file path** — used to infer datatypes for any columns that need them.

If the user hasn't run `astrodb-build-schema-validate` yet, note that the schema will be generated
without null/type checks, and suggest they validate before ingesting.

## Step 1: Identify unmatched and problematic columns

Before generating any YAML, audit the mapping table:

**Unmatched columns**: rows where DB Table or DB Field is blank, "—", "N/A", or "unmatched".

**Problematic columns** (if validation report is present):
- Nullable violations: a column has nulls but its mapped field is `nullable: false`
- Type mismatches: column dtype is incompatible with the schema field's datatype

For each category, **ask the user** how to handle them before proceeding. Present all
unmatched/problematic columns in a single message — one question per category, not one per column.

### Unmatched column options (ask the user to choose for each, or apply a default):
- **Skip it** — don't include it in the schema (good for metadata columns, row numbers, etc.)
- **Add to an existing table** — user specifies which table and what field name to use
- **Create a new table** — user provides a table name and any other columns it should have
- **Flag only** — include it as a commented-out stub in the YAML so it's documented but inactive

### Problematic column options:
- **Nullable violation**: mark the field `nullable: true` in the new schema, OR exclude that column
- **Type mismatch**: use the data's actual type in the new schema, OR use the schema's expected type
  (with a note that a cast will be needed at ingest)

If there are no unmatched or problematic columns, skip this step and proceed directly to generation.

## Step 2: Group columns by table

Group all columns that will appear in the schema by their DB Table. Each group becomes one
table block in the YAML.

For each table:
- Collect: table name, all mapped columns (with their DB Field names, types, units, descriptions)
- Note which column(s) form the primary key. If not obvious from the mapping, ask the user.
  Common defaults: `source` or `source_id` for data tables; the main identifier column otherwise.

## Step 3: Generate the Felis YAML

Follow the syntax in `references/felis-syntax.md` exactly. Key rules:
- Schema-level `@id` = `"#<SchemaName>"`
- Table `@id` = `"#<TableName>"`
- Column `@id` = `"#<TableName>.<columnName>"`
- `primaryKey` is a list of column `@id` strings
- Use the data column's actual numpy/astropy type, mapped to a Felis datatype
- Include `fits:tunit` for any column that has units
- Include `ivoa:ucd` where you can infer it confidently (see `references/felis-syntax.md`)
- Add foreign key constraints for any `source`, `reference`, `telescope`, `instrument`
  columns that link to standard AstroDB lookup tables
- **Always include stub definitions for lookup tables that are referenced via FK** —
  even if the data file doesn't populate them directly. At minimum define `Sources`
  (with `source` column) and `Publications` (with `reference` column) whenever those
  FKs appear. Without a table definition in the same schema file, the FK constraint
  references a table that doesn't exist in the document, which will fail Felis validation.

### Datatype mapping (data type → Felis datatype):
| Data type | Felis datatype |
|---|---|
| float64, float32 | `double` |
| float32 only | `float` |
| int64, int32 | `long` / `int` |
| int16, int8 | `short` / `byte` |
| bool | `boolean` |
| str, object, bytes | `string` (add `length`) |
| datetime64 | `timestamp` |

For `string` columns, set `length` to the observed max string length rounded up to a
reasonable ceiling (e.g., 30, 50, 100, 256). If you can't observe the data, use 100 as a default.

### Nullable rules:
- Default: `nullable: true` (omit the field — Felis treats absent as true)
- Set `nullable: false` only for primary key columns and columns the user confirms are required
- If validation found a nullable violation and the user chose to relax it: set `nullable: true`

## Step 4: Write the schema file

Before writing, verify the YAML you are about to write has:
- `name: <user-confirmed schema name>` — not `astrodb_template`, not derived from the file
- `"@id": "#<user-confirmed schema name>"` — matching the `name:` field exactly

If either field still contains a template placeholder, stop and fix it before writing.

Save the generated YAML to `astrodb-build-artifacts/<schema-name>-schema.yaml` using the Write tool. This is required — always produce a real `.yaml` file. Do not only paste the YAML in the chat; the file is what the user will use.

Tell the user:
- The file path (so they can open or copy it)
- How many tables and columns were included
- Which columns were skipped or flagged (if any)
- Whether any assumptions were made (e.g., inferred primary keys, default string lengths)

Do not reproduce the full YAML in the chat — just reference the file path. The user can view it with `cat <file-path>`.

## Step 5: Validate with felis

After writing the file, run `felis validate` on it. If there is a `.venv` directory in the current working directory, use `.venv/bin/felis`; otherwise try `felis` on PATH:

```bash
.venv/bin/felis validate astrodb-build-artifacts/<schema-name>-schema.yaml
# or
felis validate astrodb-build-artifacts/<schema-name>-schema.yaml
```

**If validation passes:** tell the user the schema is valid.

**If validation fails:** read the error messages carefully. The most common errors are:
- A FK constraint references a column in a table that is not defined in the schema (e.g., `#Publications.reference` when `Publications` has no entry in `tables:`). Fix by adding stub table definitions for all referenced tables (see the rule in Step 3 about lookup table stubs).
- An `@id` is duplicated across tables/columns.
- A `string` column is missing its `length` field.

Fix the errors, rewrite the file, and re-run validation. Repeat until the schema passes, then tell the user it passed (and briefly mention what was fixed if anything needed fixing).

## Completion Checklist

Before telling the user the schema is generated, confirm every item below. Anything unmet must be done —
or explicitly waived by the user — first.

- [ ] Unmatched and (if a validation report was provided) problematic columns were audited and raised with the user — one question per category — or there were none.
- [ ] Columns are grouped by table, and each table has a primary key identified (you asked the user when it wasn't obvious).
- [ ] The Felis YAML follows `references/felis-syntax.md`: correct `@id` references, datatypes, units, nullable flags, and foreign keys — and includes stub table definitions for every lookup table referenced by a FK (at minimum `Sources` and `Publications`), so no FK points at a table absent from the document.
- [ ] The schema was written to a real file at `astrodb-build-artifacts/<schema-name>-schema.yaml` (not just pasted into the chat).
- [ ] `felis validate` was actually run on the file and **passes** — if it failed, you fixed the errors, rewrote the file, and re-ran until it passed.
- [ ] You reported the file path, the table/column counts, any skipped or flagged columns, and any assumptions made (inferred primary keys, default string lengths).

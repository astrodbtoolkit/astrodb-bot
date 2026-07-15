---
name: astrodb-build-schema-match
description: Match columns from an astronomical data table to fields in the AstroDB template database schema. Use this skill whenever the user wants to ingest, import, or load a data table (FITS, CSV, ECSV, etc.) into an AstroDB database, wants to know which database table or field a column belongs to, asks about schema mapping, column mapping, or data ingestion, or has output from the astrodb-build-parse-table skill and wants to figure out where each column goes. This skill should also trigger when the user shares a table of columns (with names, descriptions, units, types) and asks about AstroDB, SIMPLE, or any astrodb-toolkit database. Always use this skill proactively after astrodb-build-parse-table runs if the user seems to be working toward database ingestion.
compatibility: python, astropy
metadata:
  authors: ["Claude"]

---

# Match Schema

Map columns from an astronomical data table to the AstroDB template database schema, so you know
exactly which table and field each column belongs to before ingesting data.

**All outputs from this skill must be written inside a folder named `astrodb-build-artifacts/` in the current working directory.** Create this folder before writing any files:

```bash
mkdir -p astrodb-build-artifacts
```

If this fails, stop and tell the user you cannot create the output directory.

## Directions Document

Before matching, look for a **directions document** — the user's notes on which columns go where, what
to ignore, custom tables, and known edge cases. Work through these in order and stop at the first hit:

1. **The user provided a path.** Read it, then copy it to `astrodb-build-artifacts/directions.md` so it
   persists for later skills and later runs.
2. **`astrodb-build-artifacts/directions.md` already exists** — from a prior run, or copied there by
   `astrodb-build-parse-table`. Read it as-is.
3. **Neither.** Proceed without one; it's optional.

Where a directions document speaks to a column, honor it over the default matching heuristics in this
skill. Column matching is guesswork built on naming conventions, and the user writes these notes exactly
where those conventions mislead — a `J` column that's a magnitude in one survey and a coordinate in
another. Their explicit call beats the heuristic every time.

## Input

Accept input in either form:

1. **A markdown table** (e.g., output from the `astrodb-build-parse-table` skill) with columns: Column,
   Description, Units, Type
2. **A data file path** — run the `astrodb-build-parse-table` skill on it first, then proceed with its output

If given a file path, invoke `astrodb-build-parse-table` first and wait for its output before continuing.

## The AstroDB Template Schema

The full table and field listing is in `references/schema.md` — read it now before proceeding.
It covers all Lookup Tables, Main Tables, and Data Tables with every field name.

## Astropy Unit Normalization

When input comes from the `astrodb-build-parse-table` skill, units may be in astropy's canonical spaced
format. Treat these as equivalent to their compact forms when matching:

| Astropy format | Equivalent to |
|---|---|
| `km / s` | `km/s` |
| `mas / yr` | `mas/yr` |
| `mag / arcsec2` | `mag/arcsec²` |
| `solMass` | M☉ (solar masses) |
| `dimensionless_unscaled` | dimensionless (no units) |

## Matching Strategy

Read `references/column-patterns.md` for the full matching rules. It covers three layers in order:
1. **Column name patterns** — specific known aliases for each field (strongest signal)
2. **Units** — unit-to-field lookup when the name is ambiguous
3. **Description text** — keyword scanning as a tiebreaker

It also documents how to handle uncertainty columns (`_error`, `_error_upper`, `_error_lower`) and catch-all tables (`ModeledParameters`, `CompanionParameters`) for unmapped physical parameters. It also lists column types that commonly fall through all three layers (absolute magnitudes, generic URLs, quality flags) — see "Resolving Unmatched Columns" below for what to do with them.

Read the **guiding principle at the top of `references/column-patterns.md` first**: `Sources` is deliberately minimal (only `source`, `ra_deg`, `dec_deg`, `epoch_year`, `equinox`, `reference`, `other_references`, `comments`) and is **never** a catch-all. Alternate names and survey shortnames go to `Names.other_name`; measured quantities go to their own tables (`ProperMotions`, `RadialVelocities`, `Parallaxes`, …); the `adopted` field is a boolean flag, not a mapping target; and genuinely miscellaneous non-physical columns are routed to a proposed `Misc` table rather than dumped into `Sources.comments`.

## Photometry Filter IDs

Read `references/photometry-filters.md` for the full rules on resolving band names to SVO Filter
Profile Service IDs before populating `PhotometryFilters.band`.

## Resolving Unmatched Columns

After working through all three matching layers and the special cases in
`references/column-patterns.md`, you'll often be left with a handful of columns that genuinely
have nowhere to go in the current schema. Produce the mapping table and HTML file as usual,
with these marked **Unmatched** — don't hold up the rest of the mapping while these get sorted
out.

Then, in the **same response**, ask the user about all Unmatched columns in one combined
message — one question covering every unmatched column, not one per column. For each one, give:
- The column name, description, and units
- A short reason it didn't match (reuse the explanations from `column-patterns.md` where they
  apply, e.g. "AstroDB only stores apparent magnitudes")
- The options below, with a suggested default where one is obvious from the data

**Options to offer for each unmatched column:**
1. **Ignore it** — leave it out of the mapping (good for row numbers, internal flags, etc.)
2. **Map to an existing field** — user names the `Table.field` it should go to
3. **Add a new field to an existing table** — user picks the table; suggest a field name based
   on the column name/description if you can. **Do not propose new fields on `Sources`** to hold
   leftover data — `Sources` stays at its eight fixed fields. A leftover column that needs a home
   belongs in a `Misc` table (option 4), not as a new `Sources` column.
4. **Add a new table** — user gives a short name and purpose for the table. For genuinely
   miscellaneous non-physical leftovers (survey bookkeeping, generic URLs, quality flags), the
   suggested default is a **`Misc`** table (see the `Misc` table section in
   `references/column-patterns.md`) — **not** `Sources.comments` and **not** a new `Sources` field.
   `Sources` is deliberately minimal and is never a catch-all.

If the user doesn't engage with this question, that's fine — the output is already complete
with these columns marked Unmatched, ready for them to revisit later.

### Applying the user's decisions

If the user does respond with choices, **update the existing mapping table and HTML file**
(rewrite it with the `Write` tool) to replace each resolved column's row using these confidence
levels (see "Confidence levels" under Output below):

| User's choice | DB Table | DB Field | Confidence | Notes |
|---|---|---|---|---|
| Ignore | `—` | `—` | Ignored | Original reason it didn't match |
| Map to existing field | user-given table | user-given field | User-assigned | Brief note |
| Add new field | user-given existing table | proposed field name | Proposed (new field) | "Needs schema update — see Proposed Schema Additions" |
| Add new table | proposed table name | proposed field name | Proposed (new table) | "Needs schema update — see Proposed Schema Additions" |

For every "Add new field" or "Add new table" choice, also add a row to the **Proposed Schema
Additions** section of the HTML output (see `references/html-output.md`). Keep this lightweight
— the proposed table/field name plus unit and datatype (taken from the input column where
known) and a short description is enough. Don't try to work out Felis-level details like
nullability or primary keys here; that's what `astrodb-build-schema-generate` does next, using this
proposal as its starting point.

## Output

Output the results as a markdown table, adding columns onto the output from `astrodb-build-parse-table` for the matched AstroDB Table, AstroDB Field, Confidence level, and Notes on the match.

Write both output files inside `astrodb-build-artifacts/`, in a subdirectory named after the input file's base name with a `-schema-match` suffix. **Do not overwrite an existing directory** — if it already exists, append `-1`, `-2`, etc. until a free name is found. For example, if the input is `data/catalog.fits`, write:

- `astrodb-build-artifacts/catalog-schema-match/catalog-schema-match.md`
- `astrodb-build-artifacts/catalog-schema-match/catalog-schema-match.html`

Also write the results to an HTML file using the `Write` tool. Follow the full visual spec in `references/html-output.md` — read it now before writing the file.

As part of the HTML file, also generate a **Lookup Table Checklist** section — one mini-table
per lookup table that will need new entries before ingestion can proceed. See
`references/html-output.md` for the visual spec and the rules for which lookup tables to check.

If the "Resolving Unmatched Columns" step produced any "Add new field" or "Add new table"
choices, also generate the **Proposed Schema Additions** section described in
`references/html-output.md`.

After writing the file, give a short plain-text summary in the chat (2–4 sentences) noting how
many columns matched at each confidence level and flagging anything critical. If there are
proposed schema additions, mention that running `astrodb-build-schema-generate` next can turn them
into `schema.yaml` changes.
Tell the user the exact file paths to both the markdown table and the HTML file inside `astrodb-build-artifacts/`.

**Confidence levels:**
- **High**: Name clearly matches a known pattern, or name + units together are unambiguous
- **Medium**: Units or description match but name is generic; or name matches but units are unexpected
- **Low**: Only a weak contextual signal; flagging as possible match with uncertainty
- **Unmatched**: No field fits after all three layers — see "Resolving Unmatched Columns" above
- **Ignored**: User chose to leave this column out of the mapping entirely (set when the user responds to the Unmatched prompt)
- **User-assigned**: User specified the exact `Table.field` for this column (set when the user responds to the Unmatched prompt)
- **Proposed (new field)**: User chose to add a new field to an existing table — needs a schema update before ingestion
- **Proposed (new table)**: User chose to add a new table — needs a schema update before ingestion

## Completion Checklist

Before telling the user the mapping is done, confirm every item below. Anything unmet must be done — or
explicitly waived by the user — first.

- [ ] You read `references/schema.md` before mapping, and applied all three matching layers (name patterns, units, description) plus the special-case rules in `references/column-patterns.md`.
- [ ] Any photometry band names were resolved to SVO Filter Profile Service IDs per `references/photometry-filters.md`.
- [ ] Every input column has a row with DB Table, DB Field, Confidence, and Notes — columns with nowhere to go are marked **Unmatched** rather than dropped.
- [ ] Unmatched columns were raised with the user in a single combined question; if they responded, their choices were applied (and any new field/table added to Proposed Schema Additions).
- [ ] Output was written both as a markdown table and as an HTML file per `references/html-output.md`, including the Lookup Table Checklist section (and Proposed Schema Additions if any were proposed).
- [ ] You gave a short plain-text summary in the chat and told the user the paths to both files.

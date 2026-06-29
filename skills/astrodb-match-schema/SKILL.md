---
name: astrodb-match-schema
description: Match columns from an astronomical data table to fields in the AstroDB template database schema. Use this skill whenever the user wants to ingest, import, or load a data table (FITS, CSV, ECSV, etc.) into an AstroDB database, wants to know which database table or field a column belongs to, asks about schema mapping, column mapping, or data ingestion, or has output from the astrodb-parse-data-table skill and wants to figure out where each column goes. This skill should also trigger when the user shares a table of columns (with names, descriptions, units, types) and asks about AstroDB, SIMPLE, or any astrodb-toolkit database. Always use this skill proactively after astrodb-parse-data-table runs if the user seems to be working toward database ingestion.
compatibility: python, astropy
metadata:
  authors: ["Claude"]

---

# Match Schema

Map columns from an astronomical data table to the AstroDB template database schema, so you know
exactly which table and field each column belongs to before ingesting data.

## Directions Document

Before matching, check whether `artifacts/directions.md` exists in the current working directory.
If it does, read it now — it contains dataset-specific decisions (which columns go where, what to
ignore, custom tables, known edge cases) that should directly inform how you map columns. Honor any
explicit direction over the default matching heuristics.

## Input

Accept input in either form:

1. **A markdown table** (e.g., output from the `astrodb-parse-data-table` skill) with columns: Column,
   Description, Units, Type
2. **A data file path** — run the `astrodb-parse-data-table` skill on it first, then proceed with its output

If given a file path, invoke `astrodb-parse-data-table` first and wait for its output before continuing.

## The AstroDB Template Schema

The full table and field listing is in `references/schema.md` — read it now before proceeding.
It covers all Lookup Tables, Main Tables, and Data Tables with every field name.

## Astropy Unit Normalization

When input comes from the `astrodb-parse-data-table` skill, units may be in astropy's canonical spaced
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

It also documents how to handle uncertainty columns (`_error`, `_error_upper`, `_error_lower`) and catch-all tables (`ModeledParameters`, `CompanionParameters`) for unmapped physical parameters.

If a column remains unmatched after all three layers, prompt the user to either ignore it, assign it to an existing field, create a new field in an existing table, or add a new table to the schema. Give useful suggesstions. Flag unmatched columns clearly in the output.

## Photometry Filter IDs

Read `references/photometry-filters.md` for the full rules on resolving band names to SVO Filter
Profile Service IDs before populating `PhotometryFilters.band`.

## Output

Output the results as a markdown table, adding columns onto the output from `astrodb-parse-data-table` for the matched AstroDB Table, AstroDB Field, Confidence level, and Notes on the match. 

Also write the results to an HTML file using the `Write` tool. Follow the full visual spec in `references/html-output.md` — read it now before writing the file.

As part of the HTML file, also generate a **Lookup Table Checklist** section — one mini-table
per lookup table that will need new entries before ingestion can proceed. See
`references/html-output.md` for the visual spec and the rules for which lookup tables to check.

After writing the file, give a short plain-text summary in the chat (2–4 sentences) noting how
many columns matched at each confidence level and flagging anything critical.
Tell the user the file path to both the markdown table and the html file.  

**Confidence levels:**
- **High**: Name clearly matches a known pattern, or name + units together are unambiguous
- **Medium**: Units or description match but name is generic; or name matches but units are unexpected
- **Low**: Only a weak contextual signal; flagging as possible match with uncertainty

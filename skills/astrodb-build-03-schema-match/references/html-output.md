# HTML Output Spec for astrodb-match-schema

This file defines the visual design for the `tmp/schema-match-result.html` output file.

## Two phases

This file gets written up to twice per session:

1. **Initial mapping** — written right after matching. Any column with nowhere to go is marked
   **Unmatched** and listed in the Unmatched Columns section, alongside the question asked in
   "Resolving Unmatched Columns" (SKILL.md).
2. **After resolution** — if the user responds to that question, rewrite the file: move each
   resolved column out of the Unmatched Columns section and into the main table with its new
   confidence level (Ignored / User-assigned / Proposed (new field) / Proposed (new table)),
   and add the Ignored Columns / Proposed Schema Additions sections as needed.

If the user never responds, the initial file stands as the final output — that's fine.

---

## Page structure

```
<h1> AstroDB Schema Match
<p>  Source: <filename or "unknown"> · <today's date>
<p>  Legend (see below)
<table> Mapping table
<h2> Lookup Table Checklist
<p>  intro sentence
<h3> PhotometryFilters  (if applicable)
<table> one row per band
<h3> ParameterList  (if applicable)
<table> one row per parameter
... (one <h3>+<table> per affected lookup table)
<h2> Proposed Schema Additions  (after the user resolves "new field"/"new table" columns)
<table> one row per proposed field
<h2> Unit Conversions
<table> one row per column that needs conversion
<h2> Unmatched Columns  (columns not yet resolved by the user)
<ul>  one item per unmatched column
<h2> Ignored Columns  (columns the user chose to skip)
<ul>  one item per ignored column
<h2> Ingestion Notes
<ul>  one item per issue (excluding unit conversions)
```

---

## Mapping table columns

| Column | Content | Styling |
|---|---|---|
| Input Column | Raw column name from source file | `<code>` chip: `background:#e8edf2`, `border-radius:4px`, `padding:2px 6px`, monospace font — reads as a raw data identifier |
| Description | Plain text description | Plain |
| Units | Unit string | Plain, centered |
| DB Table | AstroDB table name | Sans-serif, `font-weight:600`, prefixed with `→` to signal destination |
| DB Field | AstroDB field name | `<code>` chip: `background:#e8f4e8`, same radius/padding as Input Column chip — green tint distinguishes it from the blue-gray input chip |
| Confidence | Match confidence | Badge: `🟢 High` / `🟡 Medium` / `🔴 Low` / `⚫ Unmatched` / `🔵 User-assigned` / `🟣 Proposed (new field)` / `🟣 Proposed (new table)` / `⚪ Ignored`, centered |
| Notes | Short explanation | Plain, smaller font |

The visual contrast between the **blue-gray input chip** and the **green DB field chip** is the
primary way to distinguish raw source column names from AstroDB schema identifiers.

---

## Row shading by confidence

| Confidence | Row `background-color` |
|---|---|
| High | `#f0fff0` (very light green) |
| Medium | `#fffbea` (very light yellow) |
| Low | `#fff3f0` (very light salmon) |
| Unmatched | `#f5f5f5` (light gray); DB Table and DB Field cells show `—` |
| User-assigned | `#f0fff0` (very light green) — same as High; the user confirmed this mapping directly |
| Proposed (new field) / Proposed (new table) | `#f3ecfd` (very light purple) — signals a schema change is needed before ingestion |
| Ignored | `#f5f5f5` (light gray); DB Table and DB Field cells show `—` |

---

## Header row

Sticky header: `background:#2c3e50`, `color:#ffffff`, `position:sticky`, `top:0`.
This keeps column labels visible when scrolling a long table.

---

## Legend

Place a small legend above the table explaining:
- Blue-gray chip = input column name (from source file)
- Green chip = AstroDB field name (schema destination)
- Row color = confidence level (green = high/user-confirmed, yellow = medium, salmon = low,
  purple = proposed schema addition, gray = unmatched/ignored)

---

## Unmatched Columns section

Include this section in the **initial** write-up if at least one column was marked
**Unmatched**. `<h2>Unmatched Columns</h2>` followed by a `<ul>`. Each `<li>` should:
- Name the column (in a blue-gray input chip)
- Briefly explain why it didn't match
- Suggest the options from "Resolving Unmatched Columns" (SKILL.md), with a default where one
  is obvious

When the file is rewritten after the user responds, remove the columns they resolved from this
section (and from this section entirely if none remain).

---

## Ignored Columns section

Only include this section if at least one column was marked **Ignored** during "Resolving
Unmatched Columns". `<h2>Ignored Columns</h2>` followed by a `<ul>`. Each `<li>` should:
- Name the column (in a blue-gray input chip)
- Briefly explain why it didn't match
- Note that the user chose to leave it out of the mapping

---

## Lookup Table Checklist section

`<h2>Lookup Table Checklist</h2>` followed by a brief intro sentence:
*"The following lookup tables need entries added before ingestion. Rows in data tables reference
these by foreign key — inserting a row that references a missing lookup value will fail."*

Then render **one mini-table per affected lookup table**. Only include lookup tables that are
actually triggered by the mapped columns — omit any that are not relevant.

### Which lookup tables to check

| Lookup Table | When to include | What to list |
|---|---|---|
| PhotometryFilters | Any column mapped to `Photometry.magnitude` | One row per band: the **SVO filter ID** (e.g. `2MASS/2MASS.J`, `Gaia/Gaia3.G`) as the `band` value, plus any known effective wavelength. See https://svo2.cab.inta-csic.es/theory/fps3/ for IDs. |
| ParameterList | Any column mapped to `ModeledParameters.parameter` or `CompanionParameters.parameter` | One row per parameter name (e.g. "distance", "Teff", "logg") |
| CompanionList | Any column mapped to `CompanionRelationships.companion` | One row per unique companion name found in the mapped column |
| AssociationList | Any column mapped to `Associations.association` | One row per unique association name |
| SourceTypeList | Any column mapped to `SourceTypes.source_type` | One row per unique spectral type or classification value (if known) |
| Telescopes | Any column mapped to `Spectra.telescope` or `Photometry.telescope` | One row per telescope name |
| Instruments | Any column mapped to `Spectra.instrument` | One row per instrument name |
| RegimeList | Any data table row that uses a `regime` field (Photometry, Spectra) | One row per regime (e.g. "optical", "infrared", "nir") |

### Mini-table format

Each mini-table has an `<h3>` heading with the lookup table name, followed by a small `<table>`
with a light yellow-orange header (`background:#f0a500`, white text) to distinguish it from the
main mapping table. Include only the columns that are relevant and known from the input data:

**PhotometryFilters columns:** `band` (SVO filter ID, e.g. `2MASS/2MASS.J`) | `ucd` (if known) | `effective_wavelength_angstroms` (if known) | `width_angstroms` (if known)

The `band` cell should show the full SVO filter ID. If the ID could not be resolved unambiguously,
show the raw band name in a red placeholder cell with a tooltip or note: *confirm SVO ID at https://svo2.cab.inta-csic.es/theory/fps3/*

**ParameterList columns:** `parameter` | `description` (suggested text)

**CompanionList columns:** `companion` | `description` (if inferable)

**AssociationList columns:** `association` | `association_type` (if inferable) | `reference` (if known)

**SourceTypeList columns:** `source_type` | `comments` (if useful)

**Telescopes columns:** `telescope` | `description` (if known)

**Instruments columns:** `instrument` | `telescope` | `mode` (if known)

**RegimeList columns:** `regime` | `description`

For any field that cannot be determined from the input data, use a placeholder cell styled with
italic gray text: `<em style="color:#aaa">unknown — fill in</em>`.

Add a note below each mini-table if the entries likely already exist in the database
(e.g. common bands like 2MASS J, H, K or well-known telescopes) and ingestion may only
require verification rather than insertion.

---

## Proposed Schema Additions section

Only include this section if "Resolving Unmatched Columns" produced at least one "Add new
field" or "Add new table" choice. `<h2>Proposed Schema Additions</h2>` followed by an intro
sentence: *"These columns need a schema update before they can be ingested. The
astrodb-generate-schema skill can turn this table into schema.yaml changes."*

Render a `<table>` with a light purple header (`background:#8e44ad`, white text) and one row
per proposed field:

| Input Column | Proposed Table | Proposed Field | Unit | Datatype | Description |
|---|---|---|---|---|---|

- For "Add new field" choices, **Proposed Table** is the existing table the user picked.
- For "Add new table" choices, **Proposed Table** is the new table's name — repeat it for
  every field that belongs to that new table so they read as a group.
- **Unit** and **Datatype** come from the input column's Units/Type where available; leave the
  cell as `<em style="color:#aaa">unknown — fill in</em>` if not.
- **Description** can reuse the input column's description, lightly edited if needed.

---

## Unit Conversions section

`<h2>Unit Conversions</h2>` followed by a brief intro sentence:
*"These columns require conversion before ingestion — the DB field expects different units than
the source data provides."*

Render a `<table>` with a light blue header (`background:#2980b9`, white text) and one row per
column that needs conversion:

| Column | Input Units | DB Field | Required Units | Conversion Formula |
|---|---|---|---|---|

Example rows:
- `Prot` | `d` | `RotationalParameters.period_hr` | `hr` | `value × 24`
- `e_Prot` | `d` | `RotationalParameters.period_error` | `hr` | `value × 24`
- `dist_pc` | `pc` | `Parallaxes.parallax_mas` | `mas` | `1000 / value`
- `e_dist` | `pc` | `Parallaxes.parallax_error` | `mas` | `(1000 / dist_pc²) × e_dist`
- `plx_arcsec` | `arcsec` | `Parallaxes.parallax_mas` | `mas` | `value × 1000`

Style the Input Units and Required Units cells to make the mismatch obvious: Input Units in
`color:#c0392b` (red), Required Units in `color:#27ae60` (green).

If no columns require unit conversion, omit this section entirely.

---

## Ingestion Notes section

`<h2>Ingestion Notes</h2>` followed by a `<ul>`. Flag any of (do NOT repeat unit conversions
already covered in the Unit Conversions section):
- Columns where one input column maps to **multiple rows** (e.g., a photometry column becomes one row per band in the Photometry table)
- Columns that appear to be **duplicates** of each other (e.g., two RA columns)
- **Required fields** missing from the input — the `source` identifier is required in every data table row; flag if no obvious source column exists
- Any other structural issues (FK constraints, ordering of inserts, missing lookup values, etc.)

---

## General styles

```css
body        { font-family: sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }
table       { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
th, td      { padding: 8px 12px; border: 1px solid #ddd; vertical-align: top; }
code.input  { background: #e8edf2; border-radius: 4px; padding: 2px 6px; font-family: monospace; }
code.field  { background: #e8f4e8; border-radius: 4px; padding: 2px 6px; font-family: monospace; }
.db-table   { font-weight: 600; }
.notes      { font-size: 0.82rem; color: #555; }
```

Use `class="input"` on Input Column `<code>` tags and `class="field"` on DB Field `<code>` tags
so the two chip colors are applied consistently.

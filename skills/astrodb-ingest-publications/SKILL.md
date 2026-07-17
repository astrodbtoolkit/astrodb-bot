---
name: astrodb-ingest-publications
description: "Generate and run a Python script that adds publications (references/citations) to an AstroDB Publications lookup table. Use this skill when the user says: ingest a publication, add a paper/reference/citation, populate the Publications table, 'add this DOI/bibcode', or names a paper by author+year (e.g. 'add Cruz et al. 2003') even when NO DOI is given. Also use to backfill or complete missing metadata (bibcode, DOI, description) for reference shortnames that ALREADY exist in a Publications table but are blank — e.g. 'look at Publications and fill everything out'. Also use when a data table's discovery references are missing from Publications and must be added before sources/photometry/spectra can be ingested. Handles a single paper, a batch of references from a table column, or backfilling an existing table — including the common case where the user has only a reference shortname or author+year and the paper must first be looked up online. Works standalone or as the prerequisite step before ingest-sources."
compatibility: python, astrodb_utils
---

# Ingest Publications Skill

Add publications to the `Publications` lookup table of an AstroDB database using
`astrodb_utils.publications.ingest_publication`. Every reference used elsewhere (discovery
references for sources, photometry, spectra, parallaxes, etc.) must exist as a row in
`Publications` first.

Read `references/ingest_publication_api.md` before starting — it has the full function
signatures, ADS token setup, the reference naming convention, and common warnings.

## Step 0: Read context documents

1. Read `references/astrodb-directions.md` — it defines the `workflow.md`, artifact-folder, and
   completion-checklist conventions this skill follows.
2. Check whether `workflow.md` exists in the current working directory. If it does, read it
   to carry forward context from prior skills.
3. Record this skill's checklist per the completion-checklist convention — create the artifact
   directory if needed, then add a `## astrodb-ingest-publications` section holding the items from
   `## Completion Checklist` (bottom of this file) to `astrodb-ingest-artifacts/checklists.md`.

## Reference naming convention

Every entry in `Publications` has a `reference` shortname. Always construct it as:

**First four letters of the first author's last name + two-digit year**

| Author | Year | Shortname |
|--------|------|-----------|
| Smith et al. | 2020 | `Smit20` |
| Bonaca et al. | 2020 | `Bona20` |
| Wu & Xi | 2021 | `WuXi21` (or `Wu__21` for very short names) |

**Disambiguation** — if two papers would share the same first-author/year shortname, append
the last 4 characters of the DOI to **every** conflicting paper's shortname as a suffix:

| Author | Year | DOI | Shortname |
|--------|------|-----|-----------|
| Bonaca et al. | 2020 | `10.3847/2041-8213/ab800c` | `Bona20.800c` |
| Bonaca et al. | 2020 | `10.3847/1538-4357/aba51a` | `Bona20.a51a` |

Use a `.` separator between the base shortname and the 4-character DOI suffix. Apply the
suffix to all papers in the collision — there is no "first gets the bare shortname"
exception. This applies whether you are adding them together or encounter the conflict when
a second paper is ingested later.

**Always use DOI-based suffixes** — never bare letter suffixes (e.g. `Bona20a`). Letters
that happen to appear in a DOI suffix (e.g. `Bona20.a51a`) are fine. When ADS is available
it generates a compliant shortname automatically; when using `ignore_ads=True`, construct it
yourself with this rule.

## Critical constraint: `ingest_publication` requires a DOI or bibcode

`ingest_publication` queries NASA ADS with a DOI or bibcode to fill in metadata. It
**cannot** resolve a bare reference shortname (`Cruz03`) or an "author + year" string on
its own. In most real requests the user does **not** have a DOI — they give you a shortname,
an author and year, or a file whose reference column is full of shortnames.

The primary workflow is always:

```
shortname / author+year  ──(Google Scholar / NASA ADS / Crossref)──►  actual paper
                                                                              │
                                                             verify it's the RIGHT paper
                                                                              │
                                                                  DOI + bibcode + title
                                                                              │
                                                               ingest_publication(doi=...)
```

**Never pass a bare shortname to `ingest_publication`.** A shortname like `Cruz03` is
ambiguous — there may be many "Cruz 2003" papers across different topics. A row written
from the wrong paper is worse than an empty one. Always resolve and verify first.

## Prerequisites

1. **The database.** Either a `database.toml` (astrodb-template-db JSON layout) or a
   standalone `.sqlite` file. For `database.toml`, check: (1) a path the user stated,
   (2) the project root, (3) otherwise ask — do not invent one.
2. **Package**: `astrodb_utils`.
3. **ADS token (recommended)** — lets `ingest_publication` auto-fill `bibcode`/`description`
   from a DOI. Check with `from astrodb_utils.publications import check_ads_token; check_ads_token()`.
   If missing, offer to set it up (see the API reference) or proceed with `ignore_ads=True`
   and hand-supplied metadata.
4. **Internet** — needed for the paper lookup step and for ADS queries.

## Required Inputs

1. The reference(s) to ingest — one of: a shortname (`Cruz03`), author+year
   (`Cruz et al. 2003`), DOI, ADS bibcode, or a data file whose reference column
   lists shortnames.
2. Path to `database.toml` or the `.sqlite` file — check in order:
   1. A path the user explicitly stated
   2. `database.toml` / `.sqlite` in the current working directory
   3. If not found, ask the user before continuing

---

## Step 1: Gather the references and pick the mode

Identify which mode applies:

- **Single paper** — the user names one paper, shortname, author+year, DOI, or bibcode.
- **Batch from a file** — a data table (CSV/ECSV/FITS) whose reference column contains
  shortnames that must all exist in `Publications` before sources can be ingested. Extract
  unique, non-empty values:
  ```python
  from astropy.table import Table
  data = Table.read("path/to/file.ecsv")
  refs = sorted({str(r).strip() for r in data["reference"] if str(r).strip()})
  ```
- **Backfill an existing table** — `Publications` already has the `reference` rows but
  `bibcode`/`doi`/`description` are blank. See "Backfilling existing references" below.

## Step 2: Look up each reference (skip this step only if a DOI or bibcode is already provided)

If the user supplies a DOI or ADS bibcode directly, skip to Step 3.

If you have only a shortname or author+year, you must look the paper up before calling
anything:

1. **Disambiguate with context.** A shortname alone maps to many possible papers. Use what
   the database or data file tells you: which object or stream is this reference attached to?
   Check `Associations`, `Sources`, `Photometry`, or a `stream`/`object` column in the file:
   ```python
   cur.execute("SELECT DISTINCT association FROM Associations WHERE reference=?", ("Bonaca2020",))
   # -> 'GD-1'  => look for a Bonaca 2020 paper about GD-1, not some other topic
   ```
   If context is insufficient and the shortname is genuinely ambiguous, **ask the user**
   which paper they mean rather than guessing.

2. **Search for the paper** using author + year + object/topic:
   - **Google Scholar** — confirms author, year, and title quickly
   - **NASA ADS** (`https://ui.adsabs.harvard.edu/`) — gives the ADS bibcode
   - **Crossref** — most reliable for obtaining a DOI from a title:
     ```
     https://api.crossref.org/works?query.bibliographic=<author year object/title>&rows=1
     ```

3. **Verify before proceeding.** Confirm author and year match, and that the title fits the
   object/topic the reference is attached to. Do not proceed with a guess.

4. **Show the user the resolved table and wait for confirmation** before writing anything:

   | reference | title | DOI | bibcode | context |
   |-----------|-------|-----|---------|---------|
   | Bona20 | High-resolution Spectroscopy of the GD-1 Stream... | 10.3847/2041-8213/ab800c | 2020ApJ...892L..37B | GD-1 stream |

## Step 3: Deduplicate with `find_publication`

For each resolved reference, check whether it is already in the database:

```python
from astrodb_utils.publications import find_publication
found, result = find_publication(db, doi=doi, bibcode=bibcode, reference=reference)
```

Report already-present references as "already present" — do not re-ingest.

## Step 4: Write `astrodb-ingest-artifacts/ingest_{LABEL}_publications.py`

Read `scripts/ingest_publication.py` for the pattern, then write a **tailored** script
(not a verbatim copy). It must:

- Load the DB — `build_db_from_json(settings_file=...)` for the JSON layout, or a direct
  connection for a standalone `.sqlite`.
- Fill `PUBLICATIONS` with the **resolved, verified** DOIs/bibcodes — never placeholders,
  never an unresolved bare shortname.
- Set `IGNORE_ADS` correctly: `False` when a token is present and DOIs/bibcodes are
  available; `True` only as a genuine fallback (then supply `reference` and `description`).
- Call `find_publication` before each `ingest_publication`.
- Set `SAVE_DB = False`.

`{LABEL}` is the input filename (batch) or the lead reference shortname (single paper).

## Step 5: Dry run

Run the script with `SAVE_DB = False`. Report:

- How many publications were added / already present / failed
- The warning message for each failure
- Confirmation that nothing was saved

## Step 6: Confirm and save

After a clean dry run, ask:
> Preview complete: **X** added, **Y** already present, **Z** failed. Save to the database?

**Never set `SAVE_DB = True` automatically** — only on explicit user confirmation. Saving
writes the JSON files back via `db.save_database()` (JSON layout) or commits the UPDATEs
(sqlite).

---

## Backfilling existing references

Use this when `Publications` already has the `reference` rows but `bibcode`/`doi`/
`description` are blank ("look at Publications and fill everything out"). Read
`scripts/backfill_publications.py`.

Step 2 (resolve + verify) is the whole job here — you have shortnames and nothing else.
Resolve each to the right paper using the object/stream context the database provides,
then show the user the full resolved table and **wait for explicit confirmation** before
writing anything. Only after confirmation, fill:

- **Standalone `.sqlite`** (what users usually hand you): connect and
  `UPDATE Publications SET bibcode=?, doi=?, description=? WHERE reference=?` per reference.
  A direct update is correct because the row already exists — re-ingesting would collide on
  the `reference` primary key.
- **JSON template layout** (`database.toml` + `data/`): with a token,
  `ingest_publication(doi=..., reference=...)` fills from ADS; check `get_db_publication`
  first and update a blank existing row rather than inserting a duplicate. Then
  `db.save_database()`.

Backfill is idempotent: skip references whose metadata is already populated. When done,
verify zero rows still have NULL `bibcode`/`doi`/`description`.

## Final Step: Update `workflow.md`

Follow the convention in `references/astrodb-directions.md`. Append one new entry to
`workflow.md` in the current working directory (create it with the standard header if it
doesn't exist yet). Record: which references were ingested, any that were already present or
failed, how ambiguous shortnames were resolved, and whether the user explicitly confirmed
before saving.

## Completion Checklist

Before telling the user publications are ingested, verify every item in your section of the workflow checklist file and
reproduce the evidence-annotated list here, per the **completion-checklist convention** in
`references/astrodb-directions.md`.

- [ ] The database was located — a `database.toml` or standalone `.sqlite` the user pointed you to or that you found in the project root; you asked rather than inventing a path when it wasn't found.
- [ ] You checked for an ADS token with `check_ads_token()`; if it was missing, you offered to set it up or proceeded with `ignore_ads=True` and hand-supplied metadata.
- [ ] Every reference was resolved to the *specific, verified* paper (DOI or bibcode), disambiguated by context — a bare shortname or author+year was never passed to `ingest_publication`. When you had to look a paper up (rather than being given a DOI/bibcode directly), you showed the resolved table and waited for the user's confirmation before writing.
- [ ] Every `reference` shortname follows the naming convention — first four letters of the first author's last name + two-digit year — and any collisions were disambiguated with a `.` + last-4-characters-of-DOI suffix applied to **every** colliding paper, never bare letter suffixes like `Bona20a`.
- [ ] `find_publication` was called before each `ingest_publication`, and references already present were reported as such rather than re-ingested.
- [ ] The tailored script at `astrodb-ingest-artifacts/ingest_{LABEL}_publications.py` contains only real resolved values (no placeholders), with `IGNORE_ADS` set correctly and `SAVE_DB = False`.
- [ ] A dry run was executed, and you reported how many were added / already present / failed (with each failure's warning) and that nothing was saved.
- [ ] `SAVE_DB = True` was set **only** after the user explicitly confirmed — never automatically.
- [ ] If — and only if — this was a backfill of an existing `Publications` table: rows whose metadata was already populated were skipped (idempotent), updates used the path matching the layout (direct `UPDATE` for a standalone `.sqlite`; `ingest_publication` + `db.save_database()` for the JSON layout), and you verified at the end that zero rows still have NULL `bibcode`/`doi`/`description`.

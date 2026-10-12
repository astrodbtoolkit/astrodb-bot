---
name: astrodb-convert-spectra
description: "Convert raw spectrum files (FITS, ASCII/TXT, CSV, ECSV) into specutils-readable tabular-fits files with complete, astrodb-compliant headers, ready for astrodb-ingest-spectra and ingestion into an AstroDB Spectra table. Use when the user says: convert spectra, make spectra SIMPLE/specutils-readable, convert this spectrum to FITS, fix/create spectrum headers, fix/create FITS headers for spectra, prepare spectra for ingestion, or when check_spectrum_plottable fails. Always run it before astrodb-ingest-spectra when spectra are not already plottable."
compatibility: python, astropy, specutils, astrodb_utils
---

# Convert Spectra Skill

Convert raw spectrum files into
`specutils`-readable **tabular-fits** files with a complete header, so they pass
`astrodb_utils.spectra.check_spectrum_plottable` and 
`astrodb_utils.fits.check_header`. These files can be ingested by the
`astrodb-ingest-spectra` skill.

Read `references/convert_spectra_api.md` before starting — it lists the conversion pattern, the required header keywords, and the optional keywords that can be added to the FITS header. It also explains the `convert_spectrum` function and lists the common warnings and fixes of `astrodb_utils.fits`, `check_spectrum_plottable`, and `Spectrum.write`.
Read `references/input_layouts.md` to understand how to load each input layout (ASCII, CSV, ECSV, FITS, etc.) into a pandas DataFrame or astropy Table. 

Also before starting, copy the items from the `## Completion Checklist` at the bottom of this
document — verbatim and unchecked — into
`astrodb-convert-artifacts/astrodb-convert-spectra-checklist.md` (create the folder if needed;
overwrite any copy left by a previous run). The moment an item is done, flip its `[ ]` to `[x]` in
that file and add a one-line evidence note. Keep it current as you go — you will read it back
before reporting completion.

## Golden rules

1. **Never guess units.** Wavelength and flux units come from the file or from the user. Value-range heuristics from the inspector are *questions
   to ask*, never values to use. A wrong flux unit makes a "valid" file that is scientifically wrong.
2. **Never invent metadata.** No made-up dates, coordinates, or references. Missing → ask, or leave
   the keyword blank and report it.
3. **Never modify input files.** Write new files only, into the output directory.
4. **One bad file never stops the batch.** Every failure gets a category and reason in the report.
5. **Verify the file on disk**, not just the in-memory object (round-trip read + plottable check).

## Prerequisites

1. **Packages**: `astrodb_utils`, `astropy`, `specutils`
2. **Input files**: a directory, or a list of files, containing the raw spectrum files to convert. These can be in any of the following formats:
   - FITS (with or without a header)
   - ASCII/TXT (with or without a header)
   - CSV
   - ECSV
1. **Optional `database.toml`** (astrodb-template-db layout) — if user has their AstroDB, it can supply RA/DEC from `Sources`. Check
for it in this order:
1. A path the user explicitly stated in the conversation
2. `database.toml` in the current working directory
3. **If not found, stop and ask the user to provide it before continuing.**

---

## Step 1: Inventory the inputs
```python
import pandas as pd


```

## Completion Checklist

Track these items in `astrodb-convert-artifacts/astrodb-convert-spectra-checklist.md`, created at
the start of this skill. Flip a box to `[x]` only when verifiably done, with a one-line evidence
note. Never tick a box by claiming a check you didn't actually run.

Before telling the user spectra are converted and ready for ingestion, do these two things:

1. **Read the checklist file back.** Any unchecked box means you are not done.
2. **Reproduce the checklist in your completion message**, each item with its evidence note.

- [ ] Package versions checked (specutils >= 2.0 -> `Spectrium`, else `Spectrum1D`).
- [ ] `scripts/inspect_spectrum.py` was run on every  input files, any warnings were resolved, and the layour summary was shown to the user.
- [ ] Wavelength and flux measurements and units were confirmed with the user or with the data from the input file, never guess the value or unit.
- [ ] Normalized/dimensionless-flix files were flagged and the user chose how to handle them.
- [ ] Per-file metadata (source, obs_date ISO, telescope, instrument, mode, regime, reference, RA/DEC) was assembled; ambiguous dates were asked about, none invented.
- [ ] The tailored script at `astrodb-convert-artifacts/convert_{REF}_spectra.py` contains only needed loaders and real values (no placeholders).
- [ ] A pilot (one file per layout) was run and the QA plot and one output header were reviewed with the user.
- [ ] The script ends with a comment block reporting real converted/skipped counts (not
      placeholder numbers).
- [ ] A full batch run was executed and results (ingested/skipped with reasons) were reported to the user. 
- [ ] Failures reported by category with reasons. `header_ok=False` failures listed with missing keywords.
- [ ] Original input files were not modified; new files were written to the output directory only.
- [ ] `conversion_manifest.csv` was written to the output directory, with a row for every input file and its conversion status, and hand-off to `astrodb-ingest-spectra` is offered.
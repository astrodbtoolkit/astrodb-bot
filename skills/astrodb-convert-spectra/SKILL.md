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

## Step 1: Inventory input files

List every file with: extension, size, and a classification:

| Class | How to detect |
|-------|---------------|
| `already-ok` | `check_spectrum_plottable(path, raise_error=False)` returns True |
| `fits-image-1d` | Primary HDU has 1-D data + `CRVAL1`/`CDELT1` (or `CD1_1`) WCS |
| `fits-image-multi` | Primary HDU is 2-D/3-D (e.g. IRAF multispec, rows = wave/flux/err) |
| `fits-table` | BinTableHDU with wavelength/flux-like columns |
| `ascii` | `.txt/.dat/.csv/.ecsv` — numeric columns, maybe `#` comments |
| `unknown` | anything else → report, do not convert |

Files already `already-ok` are skipped (report them; offer header check only).
Show the user the inventory table before continuing.

## Step 2: Extract arrays for each format

Use `inspect_spectrum()` in `scripts/convert_spectra.py` as the pattern. For each
file obtain `wave`, `flux`, and optionally `err` as plain numpy arrays:

- **fits-image-1d**: `wave = CRVAL1 + (arange(N) + 1 - CRPIX1) * CDELT1`;
  if `DC-FLAG == 1` or `CTYPE1` contains `LOG`, wavelength is `10**wave`.
- **fits-image-multi**: show the shape and header to the user; ask which
  axis/row is wavelength, flux, error (common SpeX layout: `data[0]=wave,
  data[1]=flux, data[2]=err`). Do not guess silently.
- **fits-table**: match columns case-insensitively against
  `wave|wavelength|lambda|lam`, `flux|f_lambda|fnu|counts`,
  `err|error|unc|sigma|ivar`. **If an `ivar` column is used, `err = 1/sqrt(ivar)`.**
- **ascii**: `np.genfromtxt(..., comments="#")`; 2 columns → wave, flux;
  3 → wave, flux, err; >3 → ask the user.

Clean data: drop rows where wave or flux is non-finite; sort by wavelength;
replace negative/zero errors with NaN (don't delete flux). Report how many
points were dropped per file.

## Step 3: Determine units

Evidence order:
1. Header keywords: `CUNIT1`, `XUNITS`, `BUNIT`, `YUNITS`, `TUNITn`.
2. Column names / ASCII comment lines (e.g. `# wavelength (micron)`).
3. Wavelength value range heuristic (see reference table):
   ~0.3–30 → µm; ~3000–30000 → Å; ~300–3000 → nm.
4. Flux magnitude heuristic: ~1e-20–1e-12 → likely `erg/s/cm2/Å`; ~1e-3–1e3
   → possibly mJy/Jy or normalized; ~1 median → **normalized** (use
   `u.dimensionless_unscaled` and note it).

Present one table per unique file layout (not per file, if 100 files share one
layout) with: inferred wave unit, flux unit, evidence, confidence. **Ask the
user to confirm or correct.** Low-confidence units are a hard stop.

Also cross-check the regime: wavelengths in µm 0.3–1.0 → optical, 0.9–2.5 →
nir, 3–30 → mir. If it disagrees with the metadata table's `regime`, flag it
(this catches wrong-unit errors).

## Step 4: Gather required metadata

For each file, assemble header metadata from (priority): user-confirmed metadata
table → original header → ask the user. Map to keywords listed in
`references/convert_spectra_api.md` (e.g. `OBJECT`, `RA_TARG`/`DEC_TARG`,
`DATE-OBS`, `TELESCOP`, `INSTRUME`, `VOREF`/`REFERENC`, `SPECBAND`/regime…).
Report every file still missing a required keyword. Never fabricate values.

## Step 5: Write `astrodb-convert-artifacts/convert_{REF}_spectra.py`

Read `scripts/convert_spectra.py` for structure. **Do not copy it verbatim** —
write a tailored script with the user's real paths, confirmed units, column/axis
mapping, and metadata mapping. `{REF}` = input directory or metadata file stem
(ask for a short label if long).

The script must:
- Set `WRITE_FILES = False` for the dry run (inspect, build `Spectrum` objects
  in memory, validate, report — write nothing).
- Build `Spectrum(spectral_axis=wave*WAVE_UNIT, flux=flux*FLUX_UNIT,
  uncertainty=StdDevUncertainty(err*FLUX_UNIT))` (omit uncertainty if no err).
- Set `spectrum.meta["header"]` = original header (cleaned of WCS/NAXIS keys that
  no longer apply) + required metadata + provenance (`ORIGFILE`, `HISTORY`
  conversion note with date and tool versions).
- Write with `format="tabular-fits"`, `overwrite=False` by default, to
  `OUTPUT_DIR/<stem>_SIMPLE.fits`.
- Validate each written file with `check_spectrum_plottable(path,
  raise_error=True, show_plot=False)` inside try/except; a per-file failure
  never stops the batch.
- Track counts: `converted`, `already_ok`, `skipped_unknown_format`,
  `skipped_unit_unconfirmed`, `skipped_missing_metadata`, `failed_validation`.
- Write a manifest CSV (`conversion_manifest.csv`): original path, output path,
  status, reason, wave unit, flux unit, n_points, wave_min, wave_max. This
  manifest can feed `astrodb-ingest-spectra` directly.
- End with a comment block of **real** counts from the run.

## Step 6: Dry run

Run with `WRITE_FILES = False`. Report counts, per-file reasons for skips, and
any regime/unit mismatches. Nothing is written except the manifest preview.

## Step 7: Confirm, write, validate

Ask: *"Dry run: X convertible, Y skipped of Z. Write converted files to
OUTPUT_DIR?"* Only on explicit yes, set `WRITE_FILES = True`, re-run, and
confirm every written file passed `check_spectrum_plottable`.

## Step 8: Visual QA (strongly recommended)

Plottable ≠ correct. Generate a multi-panel PNG (one panel per spectrum, title =
object, instrument, regime, units) and, where available, overlay the original
data to prove the conversion preserved shape and scale. Ask the user to eyeball
it before handing off to ingestion.

## Step 9: Hand off

Offer to run `astrodb-ingest-spectra` using the manifest. Remind the user the
`_SIMPLE.fits` files must be uploaded to a stable permalink host first (the
ingest skill asks for that URL — this skill never uploads anything).

---

## Completion Checklist

Track these items in `astrodb-convert-artifacts/astrodb-convert-spectra-checklist.md`, created at
the start of this skill. Flip a box to `[x]` only when verifiably done, with a one-line evidence
note. Never tick a box by claiming a check you didn't actually run.

Before telling the user spectra are converted and ready for ingestion, do these two things:

1. **Read the checklist file back.** Any unchecked box means you are not done.
2. **Reproduce the checklist in your completion message**, each item with its evidence note.

- [ ] Package versions checked (specutils >= 2.0 -> `Spectrum`, else `Spectrum1D`).
- [ ] `scripts/inspect_spectrum.py` was run on every  input files, any warnings were resolved, and the layout summary was shown to the user.
- [ ] Wavelength and flux measurements and units were confirmed with the user or with the data from the input file, never guess the value or unit.
- [ ] Normalized/dimensionless-flux files were flagged and the user chose how to handle them.
- [ ] Per-file metadata (source, obs_date ISO, telescope, instrument, mode, regime, reference, RA/DEC) was assembled; ambiguous dates were asked about, none invented.
- [ ] The tailored script at `astrodb-convert-artifacts/convert_{REF}_spectra.py` contains only needed loaders and real values (no placeholders).
- [ ] A pilot (one file per layout) was run and the QA plot and one output header were reviewed with the user.
- [ ] The script ends with a comment block reporting real converted/skipped counts (not
      placeholder numbers).
- [ ] A full batch run was executed and results (ingested/skipped with reasons) were reported to the user. 
- [ ] Failures reported by category with reasons. `header_ok=False` failures listed with missing keywords.
- [ ] Original input files were not modified; new files were written to the output directory only.
- [ ] `conversion_manifest.csv` was written to the output directory, with a row for every input file and its conversion status, and hand-off to `astrodb-ingest-spectra` is offered.
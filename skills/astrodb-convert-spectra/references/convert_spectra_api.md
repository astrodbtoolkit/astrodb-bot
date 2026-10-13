# astrodb_utils.fits.py API reference

# Conversion API Reference (astrodb_utils 1.1.0, specutils 2.0)

Sources of truth:
- https://github.com/astrodbtoolkit/astrodb_utils/blob/main/astrodb_utils/fits.py
- https://github.com/astrodbtoolkit/astrodb_utils/blob/main/astrodb_utils/spectra.py
- Docs: https://astrodb-utils.readthedocs.io/en/stable/pages/utilities/spectra/converting_spectra/converting_spectra.html
DO NOT copy these modules into the skill. Always use the installed packages.
---

## `specutils.Spectrum` (specutils ≥ 2.0; `Spectrum1D` before)

```python
import astropy.units as u
from astropy.nddata import StdDevUncertainty
from specutils import Spectrum

spec = Spectrum(
    spectral_axis=wave * u.um,                        # Quantity, any length unit
    flux=flux * (u.erg / u.s / u.cm**2 / u.AA),       # Quantity, spectral flux density
    uncertainty=StdDevUncertainty(err * flux_unit),   # optional; must be StdDev, not variance
)
spec.meta["header"] = header                          # astropy.io.fits.Header
spec.write("out_SIMPLE.fits", format="tabular-fits", overwrite=False)
```

Output layout: HDU0 = empty primary with **your header**; HDU1 `DATA` = BinTable with
`wavelength`, `flux`, `uncertainty` columns and `TUNITn` units. Reads back with
`Spectrum.read(path)` (auto-detected) or `format="tabular-fits"`.

**Gotcha:** every card in `meta["header"]` is copied into the new primary header verbatim,
including stale `CRVAL1/CDELT1/BANDIDn/BUNIT` from the original image. They no longer describe
the data and mislead readers. Strip them (see `STRUCTURAL_KEY_RE` in the template).

Uncertainty conversions: variance → `np.sqrt(var)`; inverse variance → `1/np.sqrt(ivar)` (guard 0).

---

## `check_spectrum_plottable(spectrum_path, raise_error=True, show_plot=False, format=None)`

Accepts a **path/URL string or a `Spectrum` object**. Checks, in order:
1. readable by `Spectrum.read` (path input only)
2. spectral axis convertible to microns
3. flux physical type is **`spectral flux density`** (Jy-like) **or `spectral flux density wav`**
   (erg/s/cm²/Å-like). **Dimensionless, counts, ADU, or normalized flux FAIL.**
4. not all-NaN (partial NaNs are fine)

Returns `True`/`False` with `raise_error=False`; raises `AstroDBError` otherwise.
Use it twice: on the in-memory `Spectrum` before writing, and on the written path after.

---

## `astrodb_utils.fits`

### `add_missing_keywords(header=None, format="ivoa-spectrum-dm-1.2", keywords=None) -> Header`
Adds every keyword of the data model that is missing, with `None` value. **Returns** the header.
Sets `VOCLASS='Spectrum-1.2'` for the IVOA format. Prints a copy-paste block of `header.set(...)`
lines to stdout. Wrap in `contextlib.redirect_stdout` in batch scripts.

### `add_observation_date(header=None, date=None) -> None`
Parses `date` with `dateparser` and sets `DATE-OBS` as `YYYY-MM-DD`. **Mutates in place, returns None.**
Raises `ValueError` if `date` is None or unparseable.
**Gotcha:** `dateparser` will happily parse `04/05/2014` as April 5 with no warning. Only pass dates that
are already unambiguous (ISO) or that the user confirmed.

### `add_wavelength_keywords(header=None, wavelength_data=None) -> None`
Sets `SPECBAND`, `SPEC_VAL`, `SPEC_BW`, `TDMIN1`, `TDMAX1` from a wavelength Quantity and adds a HISTORY
card. **Mutates in place and returns None.** Do not write `header = add_wavelength_keywords(...)`.
**Gotcha (bug in 1.1.0):** `SPECBAND` comes from `photometry.assign_ucd`, which calls
`.to(u.Angstrom)` but discards the result and compares the raw value to Angstrom bins. Micron or nm
input gives `SPECBAND=None`. **Always pass `wave.to(u.AA)`.** (Worth an upstream PR:
`wave_eff = wave_eff_quantity.to(u.Angstrom).value`.)

### `check_header(header=None, format="ivoa-spectrum-dm-1.2", ignore_simbad=False) -> bool`
Prints missing keywords (`KEY : comment` lines), then fails (`False`) if:
- no coordinates (`RA_TARG`/`DEC_TARG` or `RA`/`DEC`), or RA > 360, |DEC| > 90
- SIMBAD lookup of `OBJECT` fails or is ambiguous (**network call**, skipped with `ignore_simbad=True`)
- `DATE-OBS` missing or unparseable

Missing *optional* keywords (TITLE, TMID, APERTURE…) are printed but do **not** make it return False.
**Gotcha:** `make_skycoord` does `float(header["RA"])`, so a sexagesimal string raises `ValueError`.
Convert to degrees and set `RA_TARG`/`DEC_TARG` first.

### Data-model keywords

| Keyword | ivoa-1.2 | simple-spectrum | Set from |
|---|---|---|---|
| OBJECT | ✓ | ✓ | metadata `source` |
| RA_TARG, DEC_TARG | ✓ | ✓ | metadata / header, **degrees** |
| TELESCOP, INSTRUME | ✓ | ✓ | metadata |
| OBSERVAT | ✓ | | user (optional) |
| DATE-OBS | ✓ | ✓ | `add_observation_date` |
| VOCLASS | ✓ (auto) | | `add_missing_keywords` |
| VOPUB, VOREF, TITLE, AUTHOR, CONTRIB1 | ✓ | VOPUB/VOREF/AUTHOR/CONTRIB1 | user |
| TMID, TELAPSE | ✓ | TELAPSE | original header if present |
| SPEC_VAL, SPEC_BW, TDMIN1, TDMAX1, SPECBAND | ✓ | ✓ | `add_wavelength_keywords` |
| APERTURE | ✓ | ✓ | original header / user (slit width, arcsec) |

---

## Common failures and errors used by the template, sorted by category

| Category | Meaning | What to tell the user |
|---|---|---|
| `missing_units` | no wave or flux unit in file or metadata | ask for the unit (paper, data README) |
| `not_plottable` | fails `check_spectrum_plottable` (usually dimensionless flux) | see SKILL Step 3 normalized-flux options |
| `all_nan` | flux entirely NaN/inf | file is broken; ask for a new copy |
| `ambiguous_date` | non-ISO header date | ask which date is correct |
| `missing_date` | no date anywhere | ask; Spectra PK requires it |
| `load_failed` | loader raised (wrong layout/columns) | re-inspect; adjust loader |
| `exists` | output exists, `OVERWRITE=False` | confirm before overwriting |
| `roundtrip_mismatch` | flux read back ≠ written | investigate; do not ingest |
| `unexpected` | anything else | show the traceback message |

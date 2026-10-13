# Input Raw Spectra Files Layouts and How To Load Them

Each section matches a `layout` value printed by `scripts/inspect_spectrum.py`. Every loader must
return plain arrays plus the unit strings found in the file (or None), so unit resolution happens in
one place. See `scripts/convert_spectra.py` for working code.

## 1. `image-1d-wcs`: 1D image with linear wavelength WCS
```
HDU0 PrimaryHDU shape=(N,)   CRVAL1, CDELT1 (or CD1_1), CRPIX1, CUNIT1, BUNIT
```
`wave = CRVAL1 + CDELT1 * (pix + 1 - CRPIX1)` (FITS pixels are 1-based).
- `DC-FLAG = 1` (IRAF) means log-linear: `wave = 10**wave`.
- `CTYPE1 = 'WAVE-LOG'` also means a log scale; check the WCS paper convention.
- `specutils` can often auto-read these (`wcs1d-fits`) and returns the axis in **meters**. That's fine,
  but you still need to set a missing BUNIT.
- Shape `(1, N)` or `(1, 1, N)` → `np.squeeze`.

## 2. `image-2d-stacked`: rows of [wave, flux, (err)]
```
HDU0 PrimaryHDU shape=(3, N)  (sometimes (N, 3), sometimes 4 rows with a quality/mask row)
```
Common for IRTF/SpeX (Spextool), many IDL pipelines. Unit hints often in `XUNITS`/`YUNITS`
(Spextool) and occasionally only in the paper. Spextool rows: 0=wave (µm), 1=flux, 2=error,
3=quality flag (optional). **Confirm row order with the user.** It is not standardized. specutils
cannot auto-read this layout.

## 3. `bintable`: binary table extension
```
HDU0 PrimaryHDU (header only), HDU1 BinTableHDU columns e.g. WAVE, FLUX, ERR / IVAR
```
- Column names vary (`WAVELENGTH`, `LAMBDA`, `loglam` (SDSS: `10**loglam` Å), `FLUX`, `IVAR`, `ERROR`).
- Units in `TUNITn`, often missing for flux.
- SDSS-style: `flux` in `1e-17 erg/s/cm²/Å` → unit `1e-17 erg / (s cm2 Angstrom)` (astropy supports scaled units).
- `IVAR` → `err = 1/np.sqrt(ivar)` where ivar > 0, NaN elsewhere.
- Table cells may be arrays (one row, vector columns) → `.ravel()`.
- Science metadata (OBJECT, RA, DATE-OBS) is usually in the **primary** header, not the table header.

## 4. `iraf-multispec`: IRAF `apall` output
```
HDU0 PrimaryHDU shape=(nbands, napertures, N)   BANDID1..n, WAT*, CRVAL1/CDELT1 or multispec WAT2 strings
```
- Typical bands: 1 = optimally extracted ("spectrum"), 2 = raw, 3 = background, 4 = sigma.
  **Read the `BANDIDn` strings; don't assume.**
- Linear dispersion: CRVAL1/CDELT1 as in §1. If dispersion is only in `WAT2_xxx` "multispec" strings
  (non-linear / per-aperture), use `specutils.Spectrum.read(path, format="iraf")` or parse `WAT2`.
  Ask the user for help if that fails.
- Multiple apertures (`napertures > 1`) → one output file per aperture; confirm which are science.
- BUNIT is commonly absent (data may be counts, not flux calibrated → **not ingestible** until calibrated).

## 5. `ascii-columns`: .txt / .dat / .csv / .ecsv
- `np.genfromtxt(path, comments="#")`; CSV → `delimiter=","`; ECSV → `astropy.table.Table.read` (units included!).
- **Units usually live in comment lines** (`# wavelength(micron) flux(erg/s/cm2/A)`). The inspector
  prints them; confirm with the user.
- Watch for: header row without `#` (use `skip_header=1`), Fortran `D` exponents (`1.0D-15`),
  wavelength in a different column order, trailing flag columns.
- ASCII files carry no RA/DEC/date, so all metadata must come from the metadata table.

## 6. Not handled automatically. Stop and ask.
- **Echelle** (2D with many orders): needs order merging or one file per order; scientific decision.
- **2D spectral images** (spatial × spectral): need extraction, which is out of scope.
- **Counts/ADU, not flux calibrated**: can't pass `check_spectrum_plottable`; needs calibration first.
- **Already-converted** files (`VOCLASS` present, plottable): offer header-only fixes instead.

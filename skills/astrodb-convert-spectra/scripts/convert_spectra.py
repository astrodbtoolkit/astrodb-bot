"""
REFERENCE TEMPLATE -- read this to understand the conversion pattern.

Do NOT copy this file verbatim into a real run. Write a tailored script to
astrodb-convert-artifacts/convert_{REF}_spectra.py that:
  * keeps ONLY the loaders for layouts actually found by scripts/inspect_spectrum.py (Step 2),
  * uses the units the user confirmed in Step 3 (never guessed),
  * uses the metadata table / values the user confirmed in Step 4.

The CONFIG block below is filled with the eval fixture values (evals/data/) so this
template is runnable as a self-test:  python scripts/convert_spectra.py
"""

import contextlib
import io
import logging
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import StdDevUncertainty
from specutils import Spectrum

from astrodb_utils.fits import (
    add_missing_keywords,
    add_observation_date,
    add_wavelength_keywords,
    check_header,
)
from astrodb_utils.spectra import check_spectrum_plottable

warnings.filterwarnings("ignore", module="specutils")
logging.getLogger("astrodb_utils").setLevel(logging.WARNING)
logger = logging.getLogger("astrodb_convert_spectra")
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

# --- Config (fill with real values confirmed in the conversation; never placeholders) ---
HERE = Path(__file__).resolve().parent.parent
INPUT_DIR = HERE / "evals/data"
METADATA_FILE = HERE / "evals/data/metadata.csv"  # one row per file; see SKILL.md Step 4
OUTPUT_DIR = HERE / "astrodb-convert-artifacts/converted"
OUTPUT_SUFFIX = "_SIMPLE"  # output = {stem}{OUTPUT_SUFFIX}.fits
HEADER_FORMAT = "ivoa-spectrum-dm-1.2"  # or "simple-spectrum"
CHECK_SIMBAD = False  # True = network SIMBAD name check in check_header (slow)
CONTRIBUTOR = "astrodb-convert-spectra skill"  # ask the user for their name
VOPUB = None  # publisher, e.g. the archive name; ask the user
OVERWRITE = False
MAKE_QA_PLOT = True

# Layout per file, copied from inspect_spectrum.py output (Step 2).
LAYOUTS = {
    "img1d_wcs.fits": "image-1d-wcs",
    "spex_stack.fits": "image-2d-stacked",
    "bintable_desc.fits": "bintable",
    "normalized.fits": "image-1d-wcs",
    "ascii_spectrum.txt": "ascii-columns",
    "iraf_multispec.fits": "iraf-multispec",
    "all_nan.fits": "image-1d-wcs",
}

# Keys that describe the ORIGINAL array layout. They become false/misleading once the data
# are rewritten as a binary table, so they are stripped from the inherited header.
STRUCTURAL_KEY_RE = re.compile(
    r"^(SIMPLE|BITPIX|NAXIS\d*|EXTEND|PCOUNT|GCOUNT|BSCALE|BZERO|BLANK|BUNIT|DATAMIN|DATAMAX|"
    r"CRVAL\d|CDELT\d|CRPIX\d|CD\d_\d|PC\d_\d|CTYPE\d|CUNIT\d|LTV\d|LTM\d_\d|WCSDIM|WAT\d_\d+|"
    r"BANDID\d+|APNUM\d+|DC-FLAG|DCLOG\d+|XUNITS|YUNITS|TTYPE\d+|TFORM\d+|TUNIT\d+|TFIELDS|"
    r"EXTNAME|XTENSION|CHECKSUM|DATASUM)$"
)


class ConversionError(Exception):
    """Raised with a category so the batch can report it and keep going."""

    def __init__(self, category, msg):
        super().__init__(msg)
        self.category = category


# ---------------------------------------------------------------- unit handling
def resolve_unit(override, from_file, what):
    """Metadata override > unit stored in the file. Never guess from value ranges."""
    for cand in (override, from_file):
        if cand is not None and str(cand).strip() not in ("", "nan", "None"):
            try:
                unit = u.Unit(str(cand).replace("microns", "micron").replace("ergs", "erg"), parse_strict="raise")
            except ValueError:
                # FITS-style strings like "ergs s-1 cm-2 A-1" -- try the FITS parser
                unit = u.Unit(str(cand), format="fits", parse_strict="raise")
            if unit == u.dimensionless_unscaled:
                break
            return unit
    raise ConversionError(
        "missing_units",
        f"No {what} unit in file or metadata. Ask the user -- do not infer it from the values.",
    )


def wcs_wavelength(h, npix):
    step = h.get("CDELT1", h.get("CD1_1"))
    pix = np.arange(npix)
    wave = h["CRVAL1"] + step * (pix + 1 - h.get("CRPIX1", 1.0))
    if h.get("DC-FLAG") == 1:  # IRAF log-linear dispersion
        wave = 10**wave
    return wave


# ---------------------------------------------------------------- loaders
# Each returns (wave_values, flux_values, err_values_or_None, file_wave_unit, file_flux_unit, header).
def load_image_1d_wcs(path):
    with fits.open(path, ignore_missing_simple=True) as hdul:
        hdu = next(h for h in hdul if getattr(h, "data", None) is not None)
        h = hdu.header.copy()
        flux = np.squeeze(hdu.data).astype(float)
    return wcs_wavelength(h, flux.size), flux, None, h.get("CUNIT1"), h.get("BUNIT"), h


def load_image_2d_stacked(path):
    with fits.open(path, ignore_missing_simple=True) as hdul:
        h = hdul[0].header.copy()
        arr = np.squeeze(hdul[0].data).astype(float)
    if arr.shape[0] > 4:
        arr = arr.T
    err = arr[2] if arr.shape[0] > 2 else None
    return arr[0], arr[1], err, h.get("XUNITS"), h.get("YUNITS"), h


def load_bintable(path, wave_col="WAVE", flux_col="FLUX", err_col="ERR"):
    with fits.open(path, ignore_missing_simple=True) as hdul:
        hdu = next(h for h in hdul if isinstance(h, fits.BinTableHDU))
        h = hdul[0].header.copy()  # science metadata usually in the primary header
        cols = {c.name: c for c in hdu.columns}
        wave = np.asarray(hdu.data[wave_col], dtype=float).ravel()
        flux = np.asarray(hdu.data[flux_col], dtype=float).ravel()
        err = np.asarray(hdu.data[err_col], dtype=float).ravel() if err_col in cols else None
    return wave, flux, err, cols[wave_col].unit, cols[flux_col].unit, h


def load_iraf_multispec(path, flux_band=0, err_band=3):
    with fits.open(path, ignore_missing_simple=True) as hdul:
        h = hdul[0].header.copy()
        cube = hdul[0].data.astype(float)
    flux = cube[flux_band, 0, :]
    err = cube[err_band, 0, :] if err_band is not None else None
    return wcs_wavelength(h, flux.size), flux, err, h.get("CUNIT1"), h.get("BUNIT"), h


def load_ascii_columns(path):
    data = np.genfromtxt(path, comments="#")
    err = data[:, 2] if data.shape[1] > 2 else None
    return data[:, 0], data[:, 1], err, None, None, fits.Header()


LOADERS = {
    "image-1d-wcs": load_image_1d_wcs,
    "image-2d-stacked": load_image_2d_stacked,
    "bintable": load_bintable,
    "iraf-multispec": load_iraf_multispec,
    "ascii-columns": load_ascii_columns,
}


# ---------------------------------------------------------------- header
def clean_value(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) or str(v).strip() in ("", "nan") else v


def coords_to_degrees(h, meta):
    """Return (ra_deg, dec_deg) or (None, None). Handles sexagesimal strings."""
    ra = clean_value(meta.get("ra")) or h.get("RA_TARG") or h.get("RA")
    dec = clean_value(meta.get("dec")) or h.get("DEC_TARG") or h.get("DEC")
    if ra is None or dec is None:
        return None, None
    try:
        if isinstance(ra, str) and ":" in ra:
            c = SkyCoord(ra, dec, unit=(u.hourangle, u.deg))
        else:
            c = SkyCoord(float(ra), float(dec), unit=(u.deg, u.deg))
        return round(c.ra.deg, 6), round(c.dec.deg, 6)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not parse coordinates ({ra}, {dec}): {e}")
        return None, None


def resolve_obs_date(h, meta):
    """Metadata date wins. A header date is only trusted if it is unambiguous ISO."""
    date = clean_value(meta.get("obs_date"))
    if date:
        return str(date)
    raw = h.get("DATE-OBS") or h.get("DATE_OBS")
    if raw and re.match(r"^\d{4}-\d{2}-\d{2}", str(raw)):
        return str(raw)[:10]
    if raw:
        raise ConversionError("ambiguous_date", f"Header date {raw!r} is not ISO -- ask the user (DD/MM vs MM/DD?)")
    raise ConversionError("missing_date", "No observation date in file or metadata -- ask the user")


def build_header(orig, meta, wave_q, source_file):
    header = fits.Header()
    for card in orig.cards:
        if card.keyword and not STRUCTURAL_KEY_RE.match(card.keyword) and card.keyword not in ("COMMENT", ""):
            try:
                header.append(card)
            except Exception:  # noqa: BLE001 -- skip non-standard cards rather than fail
                pass

    with contextlib.redirect_stdout(io.StringIO()):  # add_missing_keywords prints copy-paste hints
        header = add_missing_keywords(header, format=HEADER_FORMAT)

    header.set("OBJECT", meta["source"], "Name of observed object")
    for key, col in (("TELESCOP", "telescope"), ("INSTRUME", "instrument"), ("VOREF", "voref"), ("AUTHOR", "author")):
        val = clean_value(meta.get(col))
        if val is not None:
            header.set(key, str(val))
    ra, dec = coords_to_degrees(orig, meta)
    if ra is not None:
        header.set("RA_TARG", ra, "[deg] target position")
        header.set("DEC_TARG", dec, "[deg] target position")
    if VOPUB:
        header.set("VOPUB", VOPUB)
    header.set("CONTRIB1", CONTRIBUTOR)

    obs_date = resolve_obs_date(orig, meta)
    with contextlib.redirect_stdout(io.StringIO()):
        add_observation_date(header, date=obs_date)  # mutates in place
    # Pass Angstrom: assign_ucd (used for SPECBAND) compares raw .value to Angstrom bins
    # without converting (astrodb_utils 1.1.0), so micron input silently gives SPECBAND=None.
    add_wavelength_keywords(header, wavelength_data=wave_q.to(u.AA))  # mutates in place, returns None
    header["HISTORY"] = f"Converted from {source_file} by astrodb-convert-spectra on {datetime.now(timezone.utc):%Y-%m-%d}"
    return header, obs_date


# ---------------------------------------------------------------- per-file pipeline
def convert_one(path, meta, layout):
    try:
        wave, flux, err, f_wave_unit, f_flux_unit, orig = LOADERS[layout](path)
    except Exception as e:  # noqa: BLE001
        raise ConversionError("load_failed", f"{type(e).__name__}: {e}") from e

    if not np.any(np.isfinite(flux)):
        raise ConversionError("all_nan", "Flux is entirely NaN/inf")

    wave_unit = resolve_unit(meta.get("wave_unit"), f_wave_unit, "wavelength")
    flux_unit = resolve_unit(meta.get("flux_unit"), f_flux_unit, "flux")

    order = np.argsort(wave)  # specutils + plotting expect ascending
    wave_q = wave[order] * wave_unit
    spec = Spectrum(
        spectral_axis=wave_q,
        flux=flux[order] * flux_unit,
        uncertainty=StdDevUncertainty(err[order] * flux_unit) if err is not None else None,
    )

    # Validate the in-memory spectrum BEFORE spending effort on the header
    if not check_spectrum_plottable(spec, raise_error=False):
        raise ConversionError("not_plottable", f"Fails check_spectrum_plottable (flux unit {flux_unit})")

    header, obs_date = build_header(orig, meta, wave_q, path.name)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        header_ok = check_header(header, format=HEADER_FORMAT, ignore_simbad=not CHECK_SIMBAD)
    missing = re.findall(r"^([A-Z0-9_\-]+) : ", buf.getvalue(), flags=re.M)
    spec.meta["header"] = header

    out_path = OUTPUT_DIR / f"{path.stem}{OUTPUT_SUFFIX}.fits"
    if out_path.exists() and not OVERWRITE:
        raise ConversionError("exists", f"{out_path.name} exists and OVERWRITE=False")
    spec.write(out_path, format="tabular-fits", overwrite=OVERWRITE)

    # Round-trip: the file on disk -- not the in-memory object -- is what gets ingested
    check_spectrum_plottable(str(out_path), raise_error=True)
    back = Spectrum.read(out_path, format="tabular-fits")
    if not np.allclose(back.flux.to_value(flux_unit), spec.flux.value, equal_nan=True):
        raise ConversionError("roundtrip_mismatch", "Flux read back from disk differs from what was written")

    return {
        "output": out_path.name, "obs_date": obs_date, "header_ok": header_ok, "missing_keywords": ";".join(missing),
        "wave_unit": str(wave_unit), "flux_unit": str(flux_unit), "n_points": int(spec.flux.size),
        "wave_min": float(wave_q.min().value), "wave_max": float(wave_q.max().value), "spectrum": spec,
    }


def qa_plot(results, out_png):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ok = [r for r in results if r["status"] == "converted"]
    if not ok:
        return
    ncol = 3
    nrow = int(np.ceil(len(ok) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(5 * ncol, 3.2 * nrow), squeeze=False)
    for ax, r in zip(axes.flat, ok):
        s = r.pop("spectrum")
        w = s.spectral_axis.to(u.micron)
        ax.plot(w, s.flux, lw=0.7)
        ax.set_title(f"{r['source']}\n{r['file']}", fontsize=8)
        ax.set_xlabel("micron", fontsize=7)
        ax.set_ylabel(str(s.flux.unit), fontsize=7)
        ax.tick_params(labelsize=7)
    for ax in axes.flat[len(ok):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    logger.info(f"QA plot written to {out_png}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    meta_tbl = pd.read_csv(METADATA_FILE, dtype=str).set_index("filename")
    results = []

    for fname, layout in LAYOUTS.items():
        path = INPUT_DIR / fname
        meta = meta_tbl.loc[fname].to_dict() if fname in meta_tbl.index else {}
        row = {"file": fname, "layout": layout, **{k: meta.get(k) for k in
               ("source", "telescope", "instrument", "mode", "regime", "reference")}}
        if not meta.get("source"):
            row.update(status="failed", category="no_metadata", reason="No metadata row / source name")
            results.append(row)
            logger.warning(f"{fname}: no metadata row")
            continue
        try:
            row.update(convert_one(path, meta, layout), status="converted", category="", reason="")
            logger.info(f"{fname}: converted -> {row['output']} (header_ok={row['header_ok']})")
        except ConversionError as e:
            row.update(status="failed", category=e.category, reason=str(e))
            logger.warning(f"{fname}: FAILED [{e.category}] {e}")
        except Exception as e:  # noqa: BLE001 -- one bad file never stops the batch
            row.update(status="failed", category="unexpected", reason=f"{type(e).__name__}: {e}")
            logger.error(f"{fname}: UNEXPECTED {type(e).__name__}: {e}")
        results.append(row)

    if MAKE_QA_PLOT:
        qa_plot(results, OUTPUT_DIR / "qa_converted_spectra.png")
    for r in results:
        r.pop("spectrum", None)

    # Manifest -- column names match what astrodb-ingest-spectra expects
    manifest = pd.DataFrame(results)
    manifest["spectrum_filename"] = manifest.get("output")
    manifest["original_spectrum_filename"] = manifest["file"]
    manifest_path = OUTPUT_DIR / "conversion_manifest.csv"
    manifest.to_csv(manifest_path, index=False)

    counts = manifest.groupby(["status", "category"]).size()
    print("\n=== Conversion summary ===")
    print(f"Total files: {len(manifest)}")
    print(counts.to_string())
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()

# Conversion summary (fill in with real counts from the run above, not placeholders):
# Total files:
# Converted:
# Failed (missing units):
# Failed (not plottable):
# Failed (date missing/ambiguous):
# Failed (other):

"""
REFERENCE TEMPLATE -- read this to understand the conversion pattern.

Do NOT copy this file verbatim into a real run. Write a tailored script to
astrodb-convert-artifacts/convert_{REF}_spectra.py that:
  * keeps ONLY the loaders for layouts actually found by scripts/inspect_spectrum.py (Step 1),
  * uses the units the user confirmed in Step 3 (never guessed),
  * uses the metadata table / values the user confirmed in Step 4
"""
import contextlib
import csv
import io
import json
import logging
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import StdDevUncertainty
from astropy.wcs import FITSFixedWarning

try:
    from specutils import Spectrum
except ImportError:  # specutils < 2.0
    from specutils import Spectrum1D as Spectrum
import specutils

import astrodb_utils
from astrodb_utils.spectra import check_spectrum_plottable
from astrodb_utils.fits import add_missing_keywords, add_observation_date, add_wavelength_keywords, check_header

logging.getLogger("astrodb_utils").setLevel(logging.ERROR)  # its own warnings are repeated in our report
logger = logging.getLogger("astrodb_utils.convert_spectra")
logger.setLevel(logging.INFO)
logger.propagate = False  # astrodb_utils has its own handler; without this every line prints twice

# --- Config (fill with real, user-confirmed values; never placeholders) ---
WRITE_FILES = False                 # dry run first; True only after the user confirms (Step 7)
OVERWRITE = False                   # never replace existing output files unless the user asks

INPUT_DIR = Path("evals/data")
OUTPUT_DIR = Path("astrodb-convert-artifacts/converted")

MANIFEST = Path("astrodb-convert-artifacts/conversion_manifest.csv")
INSPECT_JSON = Path("astrodb-convert-artifacts/inspect.json")  # from scripts/inspect_spectrum.py --json
METADATA_FILE = Path("evals/data/metadata.csv")                # one row per input file (SKILL.md Step 4)
QA_PLOT = Path("astrodb-convert-artifacts/qa_converted_spectra.png")
HEADER_FORMAT = "ivoa-spectrum-dm-1.2"   # or "simple-spectrum"
CONTRIBUTOR = "astrodb-convert-spectra skill"  # ask the user for their name
OUTPUT_SUFFIX = "_SIMPLE"

# Unit strings as they appear in real headers -> what astropy should parse.
# Without this, "ergs s-1 cm-2 A-1" parses WITHOUT an error as erg per AMPERE,
# and the squashed forms written by some pipelines do not parse at all.
UNITS = {
    "microns": "um",
    "micron": "um",
    "ergs s-1 cm-2 A-1": "erg s-1 cm-2 Angstrom-1",
    "erg s-1 cm-2 A-1": "erg s-1 cm-2 Angstrom-1",
    "ergss-1cm-2A-1": "erg s-1 cm-2 Angstrom-1",
    "Wm-2um-1": "W m-2 um-1",
}

# Header cards that describe the ORIGINAL array layout. They are false once the data
# are rewritten as a binary table, so they are not copied into the new header.
STRUCTURAL_KEYS = re.compile(
    r"^(SIMPLE|BITPIX|NAXIS\d*|EXTEND|PCOUNT|GCOUNT|BSCALE|BZERO|BLANK|BUNIT|DATAMIN|DATAMAX|"
    r"CRVAL\d|CDELT\d|CRPIX\d|CD\d_\d|PC\d_\d|CTYPE\d|CUNIT\d|LTV\d|LTM\d_\d|WCSDIM|WAT\d_\d+|"
    r"BANDID\d+|APNUM\d+|DC-FLAG|DCLOG\d+|XUNITS|YUNITS|TTYPE\d+|TFORM\d+|TUNIT\d+|TFIELDS|"
    r"EXTNAME|XTENSION|CHECKSUM|DATASUM)$"
)

MANIFEST_COLUMNS = [
    "file", "layout", "status", "category", "reason", "output",
    "source", "telescope", "instrument", "mode", "regime", "obs_date", "reference",
    "wave_unit", "flux_unit", "n_points", "n_dropped", "wave_min", "wave_max",
    "header_ok", "missing_keywords", "notes",
]


class ConversionError(Exception):
    """A per-file failure with a category from references/convert_spectra_api.md."""
    def __init__(self, category, reason):
        super().__init__(reason)
        self.category = category


def is_plottable(spectrum):
    """Safe wrapper: check_spectrum_plottable(path, raise_error=False) raises UnboundLocalError
    (astrodb_utils 1.1.0) instead of returning False when it cannot read the file."""
    try:
        return bool(check_spectrum_plottable(spectrum, raise_error=False, show_plot=False))
    except Exception:
        return False


def blank_to_none(value):
    """Treat empty metadata cells as missing."""
    if value is None or str(value).strip() in ("", "nan", "None"):
        return None
    return str(value).strip()


def open_fits(path):
    """Open a FITS file, tolerating SIMPLE = 'True' (string), which some pipelines write."""
    return fits.open(path, ignore_missing_simple=True)


# --- Loaders: one per layout from scripts/inspect_spectrum.py -------------------------------
# Each returns (wave, flux, err or None, wave_unit or None, flux_unit or None, header, notes).
# Units are only what the FILE says; the user's confirmed units override them in convert_spectrum. Do not guess units.

def wcs_wavelength(header, npix):
    """Wavelength array from linear (or IRAF log-linear) WCS keywords."""
    step = float(header.get("CDELT1", header.get("CD1_1")))
    pix = np.arange(npix)
    wave = float(header["CRVAL1"]) + step * (pix + 1 - float(header.get("CRPIX1", 1)))
    if str(header.get("DC-FLAG")) == "1" or "LOG" in str(header.get("CTYPE1", "")).upper():
        wave = 10**wave
    return wave

def load_image_1d_wcs(path, hints):
    """1D flux array with wavelength in CRVAL1/CDELT1/CRPIX1."""
    with open_fits(path) as hdul:
        hdu = hdul[hints.get("hdu", 0)]
        header = hdul[0].header.copy()
        flux = np.squeeze(hdu.data).astype(float)
        wave = wcs_wavelength(hdu.header, flux.size)
        return wave, flux, None, hdu.header.get("CUNIT1"), hdu.header.get("BUNIT"), header, []

def load_image_2d_stacked(path, hints):
    """Rows of [wave, flux, err(, flag)], e.g. SpeX/Spextool. Row order confirmed with the user."""
    with open_fits(path) as hdul:
        header = hdul[0].header.copy()
        data = np.squeeze(hdul[hints.get("hdu", 0)].data).astype(float)
    if data.shape[0] > 4:
        data = data.T
    notes = []
    if data.shape[0] == 4:
        notes.append("row 3 (quality flag) ignored")
    err = data[2] if data.shape[0] > 2 else None
    return data[0], data[1], err, header.get("XUNITS"), header.get("YUNITS"), header, notes

def load_bintable(path, hints):
    """Binary table; column names come from the inspector's loader_hints."""
    with open_fits(path) as hdul:
        header = hdul[0].header.copy()  # science metadata is usually in the primary header
        hdu = hdul[hints.get("hdu", 1)]
        units = {c.name: c.unit for c in hdu.columns}
        wave_col, flux_col, err_col = hints.get("wave_col"), hints.get("flux_col"), hints.get("err_col")
        if not wave_col or not flux_col:
            raise ConversionError("load_failed", "No wavelength/flux column identified -- ask the user")
        wave = np.asarray(hdu.data[wave_col], dtype=float).ravel()
        flux = np.asarray(hdu.data[flux_col], dtype=float).ravel()
        err = None
        notes = []
        if err_col:
            err = np.asarray(hdu.data[err_col], dtype=float).ravel()
            if err_col.lower() == "ivar":
                with np.errstate(divide="ignore"):
                    err = np.where(err > 0, 1 / np.sqrt(err), np.nan)
                notes.append("uncertainty = 1/sqrt(ivar)")
    return wave, flux, err, units.get(wave_col), units.get(flux_col), header, notes

def load_iraf_multispec(path, hints):
    """IRAF apall output (bands, apertures, pixels). Flux/sigma bands picked from BANDIDn."""
    with open_fits(path) as hdul:
        header = hdul[0].header.copy()
        cube = hdul[hints.get("hdu", 0)].data.astype(float)
    bands = {int(k[6:]): str(v).lower() for k, v in header.items() if k.startswith("BANDID")}
    flux_band = next((b for b, d in sorted(bands.items()) if d.startswith("spectrum")), 1)
    err_band = next((b for b, d in sorted(bands.items()) if d.startswith("sigma")), None)
    flux = cube[flux_band - 1, 0, :]
    err = cube[err_band - 1, 0, :] if err_band else None
    notes = [f"flux = band {flux_band}" + (f", uncertainty = band {err_band}" if err_band else "")]
    if cube.shape[1] > 1:
        notes.append(f"{cube.shape[1]} apertures; only aperture 1 converted -- ask the user about the rest")
    return wcs_wavelength(header, flux.size), flux, err, header.get("CUNIT1"), header.get("BUNIT"), header, notes

def load_ascii_columns(path, hints):
    """Whitespace or comma separated columns: wave, flux(, err). Units only from the user."""
    delimiter = "," if path.suffix.lower() == ".csv" else None
    data = np.genfromtxt(path, comments="#", delimiter=delimiter)
    if data.ndim != 2 or data.shape[1] < 2:
        raise ConversionError("load_failed", "Expected at least 2 numeric columns")
    if data.shape[1] > 3:
        raise ConversionError("load_failed", f"{data.shape[1]} columns -- ask the user which are wave/flux/err")
    err = data[:, 2] if data.shape[1] == 3 else None
    return data[:, 0], data[:, 1], err, None, None, fits.Header(), []

LOADERS = {
    "image-1d-wcs": load_image_1d_wcs,
    "image-2d-stacked": load_image_2d_stacked,
    "bintable": load_bintable,
    "iraf-multispec": load_iraf_multispec,
    "ascii-columns": load_ascii_columns,
}

def load_spectrum(path, layout, hints):
    """Load wave/flux/err and the original header using the loader for this file's layout."""
    if layout not in LOADERS:
        raise ConversionError("load_failed", f"No loader for layout '{layout}' -- stop and ask the user")
    try:
        return LOADERS[layout](path, hints)
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError("load_failed", f"{type(e).__name__}: {e}") from e

# --- Units, metadata, header -----------------------------------------------------------------

def resolve_unit(confirmed, from_file, what):
    """The user's confirmed unit wins; otherwise the unit stated in the file. Never guess."""
    for value in (blank_to_none(confirmed), blank_to_none(from_file)):
        if value is None:
            continue
        value = UNITS.get(value, value)
        try:
            unit = u.Unit(value, parse_strict="raise")
        except ValueError as e:
            raise ConversionError("missing_units", f"Cannot parse {what} unit {value!r} -- ask the user") from e
        if unit == u.dimensionless_unscaled:
            break  # normalized flux: SKILL.md Step 3, the user decides
        return unit
    raise ConversionError("missing_units", f"No {what} unit in the file or metadata -- ask the user")


def resolve_obs_date(header, meta):
    """Metadata date wins. A header date is only used if it is unambiguous ISO (YYYY-MM-DD)."""
    date = blank_to_none(meta.get("obs_date"))
    if date:
        return date
    raw = blank_to_none(header.get("DATE-OBS") or header.get("DATE_OBS"))
    if raw and re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        return raw[:10]
    if raw:
        raise ConversionError("ambiguous_date", f"Header date {raw!r} is not ISO -- ask the user")
    raise ConversionError("missing_date", "No observation date in the file or metadata -- ask the user")


def resolve_coordinates(header, meta):
    """RA/DEC in degrees from metadata or header; sexagesimal strings are converted.
    Telescope pointing (e.g. TCS_RA/TCS_DEC) is NOT used -- it is not the target position."""
    ra = blank_to_none(meta.get("ra")) or blank_to_none(header.get("RA_TARG")) or blank_to_none(header.get("RA"))
    dec = blank_to_none(meta.get("dec")) or blank_to_none(header.get("DEC_TARG")) or blank_to_none(header.get("DEC"))
    if ra is None or dec is None:
        return None, None
    try:
        if ":" in ra or " " in ra.strip():
            coord = SkyCoord(ra, dec, unit=(u.hourangle, u.deg))
        else:
            coord = SkyCoord(float(ra), float(dec), unit=(u.deg, u.deg))
    except Exception as e:
        logger.warning(f"Could not parse coordinates ({ra}, {dec}): {e}")
        return None, None
    return round(coord.ra.deg, 6), round(coord.dec.deg, 6)


def fill_missing_keywords(header, meta):
    """Fill header keywords from the confirmed metadata table. Never assume values: anything still
    missing is left blank and reported by check_header, so it can be asked about in the conversation."""
    with contextlib.redirect_stdout(io.StringIO()):  # add_missing_keywords prints copy-paste hints
        header = add_missing_keywords(header, format=HEADER_FORMAT)

    header.set("OBJECT", meta["source"], "Name of observed object")
    for key, column in [("TELESCOP", "telescope"), ("INSTRUME", "instrument"), ("VOREF", "voref"),
                        ("AUTHOR", "author"), ("VOPUB", "vopub"), ("TITLE", "title")]:
        value = blank_to_none(meta.get(column))
        if value is not None:
            header.set(key, value)

    ra, dec = resolve_coordinates(header, meta)
    if ra is not None:
        header.set("RA_TARG", ra, "[deg] target position")
        header.set("DEC_TARG", dec, "[deg] target position")
    header.set("CONTRIB1", CONTRIBUTOR)
    return header


def build_header(path, wave, header, meta):
    """Build a new FITS header with the required keywords for astrodb_utils ingestion."""
    # Start from the original header, minus cards that described the old array layout
    new_header = fits.Header()
    for card in header.cards:
        if card.keyword and card.keyword != "COMMENT" and not STRUCTURAL_KEYS.match(card.keyword):
            try:
                new_header.append(card)
            except Exception:  # skip non-standard cards rather than fail the file
                pass

    new_header = fill_missing_keywords(new_header, meta)

    # Observation date (add_observation_date changes the header in place and returns None)
    obs_date = resolve_obs_date(header, meta)
    with contextlib.redirect_stdout(io.StringIO()):
        add_observation_date(new_header, date=obs_date)

    # Wavelength keywords are computed, never asked for. Pass Angstrom: assign_ucd (used for
    # SPECBAND) compares raw values to Angstrom bins, so micron input gives SPECBAND=None.
    add_wavelength_keywords(new_header, wavelength_data=wave.to(u.AA))

    new_header["HISTORY"] = (f"Converted from {path.name} by astrodb-convert-spectra on "
                             f"{datetime.now(timezone.utc):%Y-%m-%d} (specutils {specutils.__version__}, "
                             f"astrodb_utils {astrodb_utils.__version__})")
    return new_header, obs_date


def build_spectrum(wave, flux, err, wave_unit, flux_unit, header):
    """Build a Spectrum object from the given wave, flux, err, and header, with confirmed units."""
    # Drop points with no wavelength or flux, sort ascending, and blank out impossible errors
    good = np.isfinite(wave) & np.isfinite(flux)
    n_dropped = int(np.sum(~good))
    order = np.argsort(wave[good])
    wave, flux = wave[good][order], flux[good][order]
    uncertainty = None
    if err is not None:
        err = err[good][order]
        err = np.where(err > 0, err, np.nan)
        uncertainty = StdDevUncertainty(err * flux_unit)
    spectrum = Spectrum(spectral_axis=wave * wave_unit, flux=flux * flux_unit,
                        uncertainty=uncertainty, meta={"header": header})
    return spectrum, n_dropped


# --- Per-file convert spectrum pipeline -----------------------------------------------------------------------

def convert_spectrum(path, layout, hints, meta):
    """Convert one file. Returns a manifest row; raises ConversionError with a category on failure."""
    row = {"file": path.name, "layout": layout}

    # Check if the spectrum is already converted: readable, plottable, AND has a data-model header.
    # Files that are merely readable (e.g. 1D WCS images) are still converted to get a full header.
    if path.suffix.lower() in (".fits", ".fit") and is_plottable(str(path)):
        with open_fits(path) as hdul:
            if hdul[0].header.get("VOCLASS"):
                row.update(status="already_ok", reason="already plottable with a data-model header")
                return row

    if not blank_to_none(meta.get("source")):
        raise ConversionError("missing_metadata", "No metadata row / source name for this file")
    row.update({k: meta.get(k) for k in ("source", "telescope", "instrument", "mode", "regime", "reference")})

    # Get the arrays and the original header with the loader for this layout
    wave, flux, err, file_wave_unit, file_flux_unit, header, notes = load_spectrum(path, layout, hints)
    if not np.any(np.isfinite(flux)):
        raise ConversionError("all_nan", "Flux is entirely NaN/inf")

    wave_unit = resolve_unit(meta.get("wave_unit"), file_wave_unit, "wavelength")
    flux_unit = resolve_unit(meta.get("flux_unit"), file_flux_unit, "flux")
    spectrum, n_dropped = build_spectrum(wave, flux, err, wave_unit, flux_unit, header)

    # Validate the in-memory spectrum before spending time on the header
    if not is_plottable(spectrum):
        raise ConversionError("not_plottable", f"Fails check_spectrum_plottable (flux unit {flux_unit})")

    new_header, obs_date = build_header(path, spectrum.spectral_axis, header, meta)
    report = io.StringIO()
    with contextlib.redirect_stdout(report):
        header_ok = check_header(new_header, format=HEADER_FORMAT, ignore_simbad=True)
    missing = re.findall(r"^([A-Z0-9_\-]+) : ", report.getvalue(), flags=re.M)
    spectrum.meta["header"] = new_header

    output_path = OUTPUT_DIR / f"{path.stem}{OUTPUT_SUFFIX}.fits"
    row.update(
        status="converted" if WRITE_FILES else "dry_run_ok", output=output_path.name, obs_date=obs_date,
        wave_unit=str(wave_unit), flux_unit=str(flux_unit), n_points=spectrum.flux.size, n_dropped=n_dropped,
        wave_min=float(spectrum.spectral_axis.min().value), wave_max=float(spectrum.spectral_axis.max().value),
        header_ok=header_ok, missing_keywords=";".join(missing), notes="; ".join(notes),
    )

    if WRITE_FILES:
        if output_path.exists() and not OVERWRITE:
            raise ConversionError("exists", f"{output_path.name} exists and OVERWRITE=False")
        spectrum.write(str(output_path), overwrite=OVERWRITE, format="tabular-fits")
        # Verify the file on disk, not just the object in memory (Golden rule 5)
        if not is_plottable(str(output_path)):
            raise ConversionError("not_plottable", "Written file fails check_spectrum_plottable")
        reread = Spectrum.read(str(output_path), format="tabular-fits")
        if not np.allclose(reread.flux.to_value(flux_unit), spectrum.flux.value, equal_nan=True):
            raise ConversionError("roundtrip_mismatch", "Flux read back from disk differs from what was written")

    row["spectrum"] = spectrum  # kept in memory for the QA plot; not written to the manifest
    return row


def load_layouts():
    """Layout + loader hints per file, from the inspector's JSON report (SKILL.md Step 1)."""
    if not INSPECT_JSON.exists():
        raise SystemExit(f"{INSPECT_JSON} not found -- run scripts/inspect_spectrum.py with --json first")
    with open(INSPECT_JSON) as f:
        report = json.load(f)
    return {Path(r["file"]).name: (r["layout"], r.get("loader_hints") or {}) for r in report}


def load_metadata():
    """Confirmed per-file metadata, keyed by filename."""
    with open(METADATA_FILE, newline="") as f:
        return {row["filename"]: row for row in csv.DictReader(f)}


def write_manifest(rows):
    """One row per input file -- columns also feed astrodb-ingest-spectra."""
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"Manifest written to {MANIFEST}")


def qa_plot(rows):
    """Multi-panel plot of every spectrum that passed. Plottable is not the same as correct: look at it."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not installed -- skipping QA plot")
        return
    good = [r for r in rows if "spectrum" in r]
    if not good:
        return
    ncol = 3
    nrow = int(np.ceil(len(good) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(5 * ncol, 3.2 * nrow), squeeze=False)
    for ax, r in zip(axes.flat, good):
        s = r["spectrum"]
        ax.plot(s.spectral_axis.to(u.um), s.flux, lw=0.7)
        ax.set_title(f"{r['source']} | {r.get('instrument') or ''} | {r.get('regime') or ''}\n{r['file']}", fontsize=8)
        ax.set_xlabel("wavelength (um)", fontsize=7)
        ax.set_ylabel(str(s.flux.unit), fontsize=7)
        ax.tick_params(labelsize=7)
    for ax in axes.flat[len(good):]:
        ax.axis("off")
    fig.tight_layout()
    QA_PLOT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(QA_PLOT, dpi=110)
    logger.info(f"QA plot written to {QA_PLOT}")


def convert_all(files):
    """Convert all spectrum files in the given list. One bad file never stops the batch."""
    layouts = load_layouts()
    metadata = load_metadata()
    if WRITE_FILES:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for file in files:
        layout, hints = layouts.get(file.name, ("not-inspected", {}))
        try:
            row = convert_spectrum(file, layout, hints, metadata.get(file.name, {}))
        except ConversionError as e:
            row = {"file": file.name, "layout": layout, "status": "failed", "category": e.category, "reason": str(e)}
        except Exception as e:
            row = {"file": file.name, "layout": layout, "status": "failed", "category": "unexpected",
                   "reason": f"{type(e).__name__}: {e}"}

        if row["status"] == "already_ok":
            logger.info(f"File {file.name} is already OK. Skipping.")
        elif row["status"] == "failed":
            logger.error(f"Failed to convert {file.name} [{row['category']}]: {row['reason']}")
        else:
            logger.info(f"{'Converted' if WRITE_FILES else 'Dry run OK'}: {file.name} -> {row['output']} "
                        f"(header_ok={row['header_ok']})")
        rows.append(row)

    qa_plot(rows)
    write_manifest(rows)

    counts = {}
    for r in rows:
        key = r["status"] if r["status"] != "failed" else f"failed ({r['category']})"
        counts[key] = counts.get(key, 0) + 1
    print(f"\nTotal files: {len(rows)}")
    for key, n in sorted(counts.items()):
        print(f"{key}: {n}")
    if not WRITE_FILES:
        print("Dry run complete -- no spectrum files written. Set WRITE_FILES = True after the user confirms.")
    return rows


if __name__ == "__main__":
    files = sorted(p for p in INPUT_DIR.iterdir() if p.is_file() and p.name in load_layouts())
    convert_all(files)


# Conversion summary (fill with REAL counts from the run):
# Total files:
# Converted (or dry_run_ok):
# Already OK:
# Failed (missing_units):
# Failed (not_plottable):
# Failed (all_nan):
# Failed (missing/ambiguous date):
# Failed (missing_metadata):
# Failed (load_failed / other):

"""
Inspect one or more spectrum files and classify their layout BEFORE writing a converter.

This is a real, runnable diagnostic tool (unlike convert_spectra.py, which is a template).
Run it on every input file in Step 2 of SKILL.md and show the user the summary.

    python scripts/inspect_spectrum.py path/to/file.fits [more files or globs ...]
    python scripts/inspect_spectrum.py "data/*.fits" --json inspect.json

It never modifies input files. Unit "guesses" are heuristics from value ranges --
they are suggestions for the user to confirm, never values to use silently.
"""

import argparse
import glob
import json
import logging
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits

warnings.filterwarnings("ignore")
logging.getLogger("astrodb_utils").setLevel(logging.ERROR)

INTERESTING_KEYS = [
    "OBJECT", "RA", "DEC", "RA_TARG", "DEC_TARG", "TELESCOP", "INSTRUME", "OBSERVAT",
    "DATE-OBS", "DATE_OBS", "DATE", "MJD-OBS", "EXPTIME", "AUTHOR", "VOREF",
    "BUNIT", "CUNIT1", "CTYPE1", "CRVAL1", "CDELT1", "CD1_1", "CRPIX1", "DC-FLAG",
    "XUNITS", "YUNITS", "WAT0_001", "WAT1_001", "BANDID1", "BANDID2", "BANDID3", "BANDID4",
    "VOCLASS", "SPECBAND",
]
WAVE_NAMES = ("wave", "wavelength", "lambda", "lam", "wl", "loglam", "spectral_axis")
FLUX_NAMES = ("flux", "fnu", "flam", "f_lambda", "spec", "counts")
ERR_NAMES = ("err", "error", "sigma", "unc", "uncertainty", "noise", "ivar", "var")
ASCII_EXT = {".txt", ".dat", ".csv", ".ecsv", ".ascii", ".tbl", ".asc", ".spec"}


def guess_wave_unit(values):
    v = np.nanmedian(np.abs(values))
    if 0.05 < v < 50:
        return "um (median {:.3g})".format(v)
    if 50 <= v < 3000:
        return "nm? (median {:.3g}) -- or Angstrom if UV".format(v)
    if 3000 <= v < 300000:
        return "Angstrom (median {:.3g})".format(v)
    if 2 < v < 6:
        return "log10(Angstrom)? (median {:.3g})".format(v)
    return "UNKNOWN (median {:.3g})".format(v)


def guess_flux_kind(values):
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return "ALL NaN/inf -- cannot be converted"
    med = np.median(np.abs(finite))
    if 0.2 < med < 5:
        return f"looks NORMALIZED (median {med:.3g}) -- check_spectrum_plottable rejects dimensionless flux; ask user"
    if 1e-25 < med < 1e-8:
        return f"looks like F_lambda cgs (median {med:.3g}), e.g. erg/s/cm2/A -- confirm"
    if 1e-8 <= med < 1e3:
        return f"could be Jy/mJy or counts (median {med:.3g}) -- confirm"
    return f"unusual magnitude (median {med:.3g}) -- confirm"


def nan_fraction(arr):
    arr = np.asarray(arr, dtype=float)
    return float(np.mean(~np.isfinite(arr))) if arr.size else 1.0


def try_specutils(path):
    """Attempt an auto-read + astrodb_utils plottable check. Returns dict."""
    out = {"auto_read": False}
    try:
        from specutils import Spectrum
    except ImportError:
        out["error"] = "specutils not installed"
        return out
    try:
        spec = Spectrum.read(str(path))
        out["auto_read"] = True
        out["n_points"] = int(spec.spectral_axis.size)
        out["flux_shape"] = list(spec.flux.shape)
        out["wave_unit"] = str(spec.spectral_axis.unit)
        out["flux_unit"] = str(spec.flux.unit) or "(dimensionless)"
        out["wave_range"] = [float(np.nanmin(spec.spectral_axis.value)), float(np.nanmax(spec.spectral_axis.value))]
        out["has_uncertainty"] = spec.uncertainty is not None
        try:
            from astrodb_utils.spectra import check_spectrum_plottable
            out["plottable"] = bool(check_spectrum_plottable(spec, raise_error=False))
        except Exception as e:  # noqa: BLE001
            out["plottable"] = False
            out["plottable_error"] = str(e)[:200]
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {str(e).splitlines()[0][:160]}"
    return out


def classify_fits(hdul):
    """Return (layout, notes, arrays-for-heuristics)."""
    notes = []
    prim = hdul[0]
    h = prim.header

    if str(h.get("VOCLASS", "")).startswith("Spectrum") and len(hdul) > 1 and isinstance(hdul[1], fits.BinTableHDU):
        notes.append("Header has VOCLASS -- may already be converted; check before reconverting")

    # Binary tables anywhere
    for i, hdu in enumerate(hdul):
        if isinstance(hdu, fits.BinTableHDU) and hdu.data is not None:
            cols = [c.name for c in hdu.columns]
            low = [c.lower() for c in cols]
            w = next((cols[j] for j, c in enumerate(low) if c in WAVE_NAMES or c.startswith("wave")), None)
            f = next((cols[j] for j, c in enumerate(low) if c in FLUX_NAMES or c.startswith("flux")), None)
            e = next((cols[j] for j, c in enumerate(low) if c in ERR_NAMES or c.startswith("err")), None)
            units = {c.name: (c.unit or "") for c in hdu.columns}
            notes.append(f"HDU{i} BinTable columns={cols} units={units}")
            if w and f:
                if not units.get(f):
                    notes.append(f"flux column '{f}' has NO unit -- must ask user")
                if not units.get(w):
                    notes.append(f"wave column '{w}' has NO unit -- must ask user")
                wv = np.asarray(hdu.data[w], dtype=float).ravel()
                if wv.size > 1 and wv[0] > wv[-1]:
                    notes.append("wavelength is DESCENDING -- sort ascending in converter")
                arrays = (wv, np.asarray(hdu.data[f], dtype=float).ravel())
                return "bintable", notes, arrays, {"hdu": i, "wave_col": w, "flux_col": f, "err_col": e}
            return "bintable-unrecognized-columns", notes, None, {"hdu": i}

    # Image data
    for i, hdu in enumerate(hdul):
        data = getattr(hdu, "data", None)
        if data is None or not hasattr(data, "shape") or data.ndim == 0:
            continue
        hh = hdu.header
        shape = data.shape
        has_wcs = hh.get("CRVAL1") is not None and (hh.get("CDELT1") is not None or hh.get("CD1_1") is not None)
        squeezed = np.squeeze(data)

        if data.ndim == 3 and hh.get("BANDID1") is not None:
            bands = {k: hh[k] for k in hh if k.startswith("BANDID")}
            notes.append(f"IRAF multispec bands: {bands}")
            notes.append("Typical choice: flux=band 1 (optimal extraction), uncertainty=band named 'sigma'")
            if hh.get("DC-FLAG") == 1:
                notes.append("DC-FLAG=1 -> log-linear wavelength solution; wave = 10**(CRVAL1 + CDELT1*(pix-CRPIX1+1))")
            return "iraf-multispec", notes, None, {"hdu": i, "shape": list(shape), "bands": bands}

        if squeezed.ndim == 1:
            if has_wcs:
                pix = np.arange(squeezed.size)
                step = hh.get("CDELT1", hh.get("CD1_1"))
                wv = hh["CRVAL1"] + step * (pix + 1 - hh.get("CRPIX1", 1))
                if hh.get("DC-FLAG") == 1:
                    notes.append("DC-FLAG=1 -> log-linear WCS")
                    wv = 10 ** wv
                if not hh.get("CUNIT1"):
                    notes.append("No CUNIT1 -- wavelength unit must be confirmed")
                if not hh.get("BUNIT"):
                    notes.append("No BUNIT -- flux unit must be confirmed")
                return "image-1d-wcs", notes, (wv, squeezed.astype(float)), {"hdu": i}
            notes.append("1D data with NO wavelength WCS -- wavelength must come from another HDU/file")
            return "image-1d-no-wcs", notes, None, {"hdu": i}

        if squeezed.ndim == 2 and min(squeezed.shape) <= 4:
            arr = squeezed if squeezed.shape[0] <= 4 else squeezed.T
            notes.append(f"Stacked rows (SpeX/IDL style): {arr.shape[0]} rows x {arr.shape[1]} pix; "
                         "assume row0=wave,row1=flux,row2=err -- CONFIRM")
            for k in ("XUNITS", "YUNITS"):
                if hh.get(k):
                    notes.append(f"{k}={hh[k]!r} (unit hint)")
            wv = arr[0].astype(float)
            if wv.size > 1 and wv[0] > wv[-1]:
                notes.append("wavelength row is DESCENDING -- sort ascending")
            return "image-2d-stacked", notes, (wv, arr[1].astype(float)), {"hdu": i, "rows": arr.shape[0]}

        notes.append(f"Image shape {shape} not recognized -- inspect manually (echelle? 2D frame?)")
        return "unknown-image", notes, None, {"hdu": i, "shape": list(shape)}

    return "unknown", notes + ["No data found in any HDU"], None, {}


def inspect_fits(path):
    rep = {"file": str(path), "kind": "fits"}
    # ignore_missing_simple: some pipelines write SIMPLE = 'True' (a string) instead of T,
    # which astropy otherwise rejects as "not a valid FITS file"
    with fits.open(path, ignore_missing_simple=True) as hdul:
        if not isinstance(hdul[0].header.get("SIMPLE"), bool):
            rep.setdefault("pre_notes", []).append(
                f"Non-standard SIMPLE={hdul[0].header.get('SIMPLE')!r}: open with ignore_missing_simple=True; "
                "header values may all be strings -- cast numbers before use")
        rep["hdus"] = [
            {"index": i, "name": h.name, "type": type(h).__name__,
             "shape": list(h.data.shape) if getattr(h, "data", None) is not None and hasattr(h.data, "shape") else None}
            for i, h in enumerate(hdul)
        ]
        merged = {}
        for hdu in hdul:
            for k in INTERESTING_KEYS:
                if k in hdu.header and k not in merged:
                    merged[k] = str(hdu.header[k])
        rep["header_keys"] = merged
        layout, notes, arrays, loader = classify_fits(hdul)
    rep["layout"] = layout
    rep["loader_hints"] = loader
    rep["notes"] = rep.pop("pre_notes", []) + notes
    if arrays is not None:
        wv, fl = arrays
        rep["wave_guess"] = guess_wave_unit(wv)
        rep["flux_guess"] = guess_flux_kind(fl)
        rep["flux_nan_fraction"] = round(nan_fraction(fl), 3)
    rep["specutils"] = try_specutils(path)
    return rep


def inspect_ascii(path):
    rep = {"file": str(path), "kind": "ascii", "layout": "ascii-columns", "notes": []}
    comments = []
    with open(path, errors="replace") as fh:
        for line in fh:
            if line.lstrip().startswith(("#", "%", "\\", "|")):
                comments.append(line.rstrip())
            if len(comments) >= 20:
                break
    rep["comment_lines"] = comments
    if comments:
        rep["notes"].append("Units/metadata often live in comment lines -- read them")
    try:
        data = np.genfromtxt(path, comments="#", invalid_raise=False,
                             delimiter="," if str(path).endswith(".csv") else None)
        if data.ndim == 2:
            rep["n_columns"] = int(data.shape[1])
            rep["n_rows"] = int(data.shape[0])
            rep["first_rows"] = data[:3].tolist()
            rep["wave_guess"] = guess_wave_unit(data[:, 0])
            if data.shape[1] > 1:
                rep["flux_guess"] = guess_flux_kind(data[:, 1])
                rep["flux_nan_fraction"] = round(nan_fraction(data[:, 1]), 3)
            rep["notes"].append("Assumed col0=wave, col1=flux, col2=err -- CONFIRM")
    except Exception as e:  # noqa: BLE001
        rep["notes"].append(f"numpy could not parse: {e}")
    rep["specutils"] = try_specutils(path)
    return rep


def recommend(rep):
    s = rep.get("specutils", {})
    if rep.get("flux_nan_fraction") == 1.0:
        return "UNCONVERTIBLE: flux is entirely NaN/inf -- report to user, do not convert"
    if s.get("auto_read") and s.get("plottable") and len(s.get("flux_shape", [])) == 1:
        return "AUTO: Spectrum.read works and passes check_spectrum_plottable -- just fix header + write tabular-fits"
    if s.get("auto_read") and not s.get("plottable"):
        return "AUTO-READ BUT NOT PLOTTABLE: reads, but units/NaNs fail -- set units explicitly (ask user)"
    return f"MANUAL: write a '{rep['layout']}' loader in the converter"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paths", nargs="+")
    p.add_argument("--json", help="also write full report to this JSON file")
    args = p.parse_args()

    files = []
    for pat in args.paths:
        files.extend(sorted(glob.glob(pat)) or [pat])

    reports = []
    for f in files:
        path = Path(f)
        try:
            if path.suffix.lower() in ASCII_EXT:
                rep = inspect_ascii(path)
            else:
                rep = inspect_fits(path)
        except Exception as e:  # noqa: BLE001
            rep = {"file": str(path), "layout": "unreadable", "notes": [f"{type(e).__name__}: {e}"], "specutils": {}}
        rep["recommendation"] = recommend(rep)
        reports.append(rep)

        print("=" * 78)
        print(f"{path.name}  ->  layout: {rep['layout']}")
        for h in rep.get("hdus", []):
            print(f"   HDU{h['index']} {h['name']:<10} {h['type']:<14} shape={h['shape']}")
        if rep.get("header_keys"):
            print("   header:", ", ".join(f"{k}={v}" for k, v in rep["header_keys"].items()))
        for c in rep.get("comment_lines", [])[:5]:
            print("   comment:", c)
        for key in ("wave_guess", "flux_guess", "flux_nan_fraction"):
            if key in rep:
                print(f"   {key}: {rep[key]}")
        for n in rep.get("notes", []):
            print("   note:", n)
        s = rep.get("specutils", {})
        if s.get("auto_read"):
            print(f"   specutils auto-read: OK  wave={s['wave_unit']} flux={s['flux_unit']} "
                  f"n={s['n_points']} plottable={s.get('plottable')}")
        else:
            print(f"   specutils auto-read: FAILED ({s.get('error', '')[:100]})")
        print(f"   >>> {rep['recommendation']}")

    print("=" * 78)
    by_layout = {}
    for r in reports:
        by_layout.setdefault(r["layout"], []).append(Path(r["file"]).name)
    print("SUMMARY by layout:")
    for k, v in by_layout.items():
        print(f"  {k:<26} {len(v):>3}  e.g. {v[0]}")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(reports, fh, indent=2, default=str)
        print(f"Full report written to {args.json}")


if __name__ == "__main__":
    main()

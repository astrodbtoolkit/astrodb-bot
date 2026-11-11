"""
Inspect raw spectrum files and report what a converter needs to know.

Writes two outputs from the same data:
  --json  machine-readable report (input to astrodb-convert-spectra)
  --md    human-readable, shareable Markdown report (for the PI / team)

Usage:
  python inspect_spectrum.py FILE [FILE ...] --json out/inspect.json --md out/inspect.md
  python inspect_spectrum.py --from-json out/inspect.json --md out/inspect.md   # re-render only

Read-only: never modifies input files.
"""
import argparse
import json
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HEADER_KEYS = ["OBJECT", "TELESCOP", "INSTRUME", "DATE-OBS", "DATE_OBS", "DATE",
               "TIME_OBS", "MJD_OBS", "MJD-OBS", "RA", "DEC", "TCS_RA", "TCS_DEC",
               "XUNITS", "YUNITS", "CUNIT1", "BUNIT", "GRAT", "MODENAME", "BIBCODE",
               "VERSION"]
WCS_KEYS = ("CRVAL1", "CDELT1", "CD1_1")
WAVE_COLS = ("wave", "wavelength", "lambda", "lam")
FLUX_COLS = ("flux", "f_lambda", "flam", "fnu", "counts")
ERR_COLS = ("err", "error", "unc", "uncertainty", "sigma", "ivar")
REQUIRED_META = ["OBJECT", "TELESCOP", "INSTRUME", "DATE-OBS", "RA_TARG", "DEC_TARG"]


# ---make guesses about the wavelength and flux units based on the median values of the arrays
def wave_guess(wave):
    med = float(np.nanmedian(wave))
    if 0.1 <= med <= 30:
        unit = "um"
    elif 300 <= med < 3000:
        unit = "nm"
    elif 3000 <= med <= 300000:
        unit = "Angstrom"
    else:
        return f"unknown (median {med:.3g})", None
    return f"{unit} (median {med:.3g})", unit


def flux_guess(flux):
    med = float(np.nanmedian(np.abs(flux)))
    if 1e-22 <= med <= 1e-11:
        return f"looks like F_lambda cgs (median {med:.3g}), e.g. erg/s/cm2/A -- confirm"
    if 0.05 <= med <= 20:
        return f"possibly normalized or Jy/mJy (median {med:.3g}) -- confirm"
    return f"unknown scale (median {med:.3g}) -- confirm"


def regime_from_um(lo, hi):
    mid = (lo + hi) / 2
    if mid < 0.95:
        return "optical"
    if mid < 2.6:
        return "nir"
    if mid < 30:
        return "mir"
    return "unknown"


def filename_hints(name):
    """Metadata candidates encoded in common filename conventions. Always CONFIRM."""
    hints = {}
    m = re.search(r"J(\d{2})(\d{2})(\d{2}(?:\.\d+)?)([+-])(\d{2})(\d{2})(\d{2}(?:\.\d+)?)", name)
    if m:
        h, mi, s, sg, d, dm, ds = m.groups()
        ra = (int(h) + int(mi) / 60 + float(s) / 3600) * 15
        dec = (int(d) + int(dm) / 60 + float(ds) / 3600) * (-1 if sg == "-" else 1)
        hints["designation_coords_deg"] = [round(ra, 5), round(dec, 5)]
    m = re.search(r"obs(\d{2})(\d{2})(\d{2})", name)
    if m:
        hints["obs_date"] = f"20{m[1]}-{m[2]}-{m[3]}"
    m = re.search(r"red(\d{2})(\d{2})(\d{2})", name)
    if m:
        hints["reduction_date"] = f"20{m[1]}-{m[2]}-{m[3]}"
    for inst in ("FIRE", "SpeX", "spex", "NIRSPEC", "LRIS", "GMOS", "BCSpec", "OSIRIS"):
        if inst in name:
            hints["instrument"] = inst
            break
    return hints


def _pick(names, candidates):
    low = {n.lower(): n for n in names}
    for c in candidates:
        if c in low:
            return low[c]
    for n in names:
        if any(c in n.lower() for c in candidates):
            return n
    return None


# --- inspection... extract the metadata from the files
def _arrays_summary(rep, wave, flux, err):
    wave = np.asarray(wave, float)
    flux = np.asarray(flux, float)
    rep["n_points"] = int(wave.size)
    rep["flux_nan_fraction"] = round(float(np.mean(~np.isfinite(flux))), 3)
    rep["wave_sorted"] = bool(np.all(np.diff(wave[np.isfinite(wave)]) > 0))
    rep["wave_guess"], unit = wave_guess(wave)
    rep["flux_guess"] = flux_guess(flux)
    rep["has_error"] = err is not None
    if unit:
        scale = {"um": 1, "nm": 1e-3, "Angstrom": 1e-4}[unit]
        lo, hi = np.nanmin(wave) * scale, np.nanmax(wave) * scale
        rep["wave_range_um"] = [round(float(lo), 4), round(float(hi), 4)]
        rep["regime_guess"] = regime_from_um(lo, hi)


def inspect_file(path):
    path = Path(path)
    rep = {"file": str(path), "notes": [], "specutils": {}}
    if not path.exists():
        rep.update(kind="missing", layout="missing",
                   recommendation="FILE NOT FOUND: check the path (has the file been written yet?)")
        return rep

    rep["filename_hints"] = filename_hints(path.name)

    # 1) Can specutils already read it?
    try:
        from specutils import Spectrum
    except ImportError:
        try:
            from specutils import Spectrum1D as Spectrum
        except ImportError:
            Spectrum = None
    if Spectrum is not None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                Spectrum.read(str(path))
            rep["specutils"] = {"auto_read": True}
        except Exception as e:  # noqa: BLE001
            rep["specutils"] = {"auto_read": False, "error": f"{type(e).__name__}: {e}"[:200]}
    else:
        rep["specutils"] = {"auto_read": None, "error": "specutils not installed"}

    suffix = path.suffix.lower()
    if suffix in (".fits", ".fit", ".fts"):
        from astropy.io import fits
        rep["kind"] = "fits"
        try:
            hdul = fits.open(path, ignore_missing_simple=True)
        except Exception as e:  # noqa: BLE001
            rep.update(layout="unreadable", recommendation=f"Cannot open FITS: {e}")
            return rep
        with hdul:
            rep["hdus"] = [{"index": i, "name": h.name, "type": type(h).__name__,
                            "shape": list(h.data.shape) if getattr(h, "data", None) is not None
                            and hasattr(h.data, "shape") else None}
                           for i, h in enumerate(hdul)]
            hdr = hdul[0].header
            rep["header_keys"] = {k: str(hdr[k]).strip() for k in HEADER_KEYS if k in hdr}
            if isinstance(hdr.get("SIMPLE"), str):
                rep["notes"].append("Non-standard SIMPLE='True': open with "
                                    "ignore_missing_simple=True; cast string header values")
            if "DATE_OBS" in hdr and "DATE-OBS" not in hdr:
                rep["notes"].append("Date stored as DATE_OBS (underscore); map to DATE-OBS")
            if "DATE" in hdr and not ({"DATE-OBS", "DATE_OBS"} & set(hdr.keys())):
                rep["notes"].append("Only DATE present -- usually file-creation/reduction date, "
                                    "NOT observation date. Do not use as DATE-OBS")
            for k in ("XUNITS", "YUNITS", "CUNIT1", "BUNIT"):
                if k in hdr:
                    rep["notes"].append(f"{k}={str(hdr[k]).strip()!r} (unit hint)")

            data = hdul[0].data
            if data is not None and data.ndim == 1:
                if any(k in hdr for k in WCS_KEYS):
                    n = data.size
                    crval = float(hdr["CRVAL1"])
                    cdelt = float(hdr.get("CDELT1", hdr.get("CD1_1")))
                    crpix = float(hdr.get("CRPIX1", 1))
                    wave = crval + (np.arange(n) + 1 - crpix) * cdelt
                    if str(hdr.get("DC-FLAG", "0")).strip() == "1":
                        wave = 10 ** wave
                    rep["layout"] = "image-1d-wcs"
                    _arrays_summary(rep, wave, data, None)
                else:
                    rep["layout"] = "image-1d-nowcs"
                    rep["notes"].append("1-D data without wavelength WCS -- wavelength unknown")
            elif data is not None and data.ndim >= 2:
                arr = np.squeeze(np.asarray(data, float))
                rep["layout"] = "image-2d-stacked"
                rep["loader_hints"] = {"hdu": 0, "rows": int(arr.shape[0])}
                rep["notes"].append(f"Stacked rows (SpeX/IDL style): {arr.shape[0]} rows x "
                                    f"{arr.shape[-1]} pix; assume row0=wave,row1=flux,row2=err -- CONFIRM")
                if arr.ndim == 2 and arr.shape[0] >= 2:
                    _arrays_summary(rep, arr[0], arr[1], arr[2] if arr.shape[0] > 2 else None)
            else:
                for i, h in enumerate(hdul[1:], start=1):
                    if isinstance(h, fits.BinTableHDU):
                        cols = h.columns.names
                        w, f, e = _pick(cols, WAVE_COLS), _pick(cols, FLUX_COLS), _pick(cols, ERR_COLS)
                        if w and f:
                            rep["layout"] = "fits-table"
                            rep["loader_hints"] = {"hdu": i, "wave": w, "flux": f, "err": e}
                            if e and "ivar" in e.lower():
                                rep["notes"].append("Error column is inverse variance: err = 1/sqrt(ivar)")
                            _arrays_summary(rep, np.ravel(h.data[w]), np.ravel(h.data[f]), e)
                            break
                rep.setdefault("layout", "unknown")
    elif suffix in (".txt", ".dat", ".csv", ".ascii", ".tbl", ".ecsv"):
        rep["kind"] = "ascii"
        delim = "," if suffix == ".csv" else None
        try:
            arr = np.genfromtxt(path, comments="#", delimiter=delim, invalid_raise=False)
            if arr.ndim == 2 and np.isnan(arr[0]).all():
                arr = arr[1:]
        except Exception as e:  # noqa: BLE001
            arr = None
            rep["notes"].append(f"genfromtxt failed: {e}")
        if arr is not None and arr.ndim == 2 and arr.shape[1] >= 2:
            rep["layout"] = f"ascii-{arr.shape[1]}col"
            rep["loader_hints"] = {"columns": int(arr.shape[1])}
            if arr.shape[1] > 3:
                rep["notes"].append(">3 columns -- ask which are wave/flux/err")
            _arrays_summary(rep, arr[:, 0], arr[:, 1], arr[:, 2] if arr.shape[1] > 2 else None)
            comments = [ln.strip() for ln in open(path, errors="replace") if ln.startswith("#")]
            if comments:
                rep["header_comments"] = comments[:10]
        else:
            rep["layout"] = "unknown"
    else:
        rep.update(kind="other", layout="unknown")

    # Recommendation
    if rep["specutils"].get("auto_read"):
        rep["recommendation"] = "ALREADY OK: specutils reads it; check header only"
    elif rep.get("layout") in (None, "unknown", "image-1d-nowcs", "unreadable"):
        rep["recommendation"] = "MANUAL: layout not understood -- inspect by hand / ask the data owner"
    else:
        rep["recommendation"] = f"CONVERT: use the '{rep['layout']}' loader in astrodb-convert-spectra"

    # What a converter will still need from a human
    rep["missing_metadata"] = missing_metadata(rep.get("header_keys", {}))
    return rep


def missing_metadata(hk):
    have = {"OBJECT": "OBJECT" in hk, "TELESCOP": "TELESCOP" in hk, "INSTRUME": "INSTRUME" in hk,
            "DATE-OBS": bool({"DATE-OBS", "DATE_OBS", "MJD_OBS", "MJD-OBS"} & set(hk)),
            "RA_TARG": "RA" in hk, "DEC_TARG": "DEC" in hk}
    return [k for k in REQUIRED_META if not have[k]]


# --- create markdown files for each source so that astronomers can understand the results and confirm the guesses
def _status_icon(rec):
    r = rec.get("recommendation", "")
    return "✅" if r.startswith("ALREADY") else "🔄" if r.startswith("CONVERT") else "⚠️"


def render_markdown(reports, title="Spectrum Inspection Report"):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [f"# {title}", "", f"_Generated {now} by astrodb-inspect-spectra. "
           "Read-only inspection; no files were modified._", "",
           "Legend: ✅ already readable · 🔄 convertible · ⚠️ needs a human", "",
           "## Summary", "",
           "| | File | Layout | Wavelength | Flux | NaN % | Regime | Next step |",
           "|---|---|---|---|---|---|---|---|"]
    for r in reports:
        wr = r.get("wave_range_um")
        out.append("| {} | `{}` | {} | {} | {} | {} | {} | {} |".format(
            _status_icon(r), Path(r["file"]).name, r.get("layout", "?"),
            f"{wr[0]}–{wr[1]} µm" if wr else r.get("wave_guess", "—"),
            (r.get("flux_guess") or "—").split(" (")[0],
            f"{100 * r['flux_nan_fraction']:.1f}" if "flux_nan_fraction" in r else "—",
            r.get("regime_guess", "—"),
            r.get("recommendation", "—").split(":")[0]))
    out.append("")

    for r in reports:
        name = Path(r["file"]).name
        out += [f"## {_status_icon(r)} {name}", "", f"**Path:** `{r['file']}`  ",
                f"**Recommendation:** {r.get('recommendation', '—')}", ""]
        if r.get("layout") == "missing":
            continue
        out += ["### Data", "", "| Property | Value |", "|---|---|"]
        rows = [("Layout", r.get("layout")), ("Points", r.get("n_points")),
                ("Wavelength guess", r.get("wave_guess")),
                ("Wavelength range", f"{r['wave_range_um'][0]}–{r['wave_range_um'][1]} µm"
                 if r.get("wave_range_um") else None),
                ("Flux guess", r.get("flux_guess")),
                ("Has uncertainty", r.get("has_error")),
                ("Flux NaN fraction", f"{100 * r['flux_nan_fraction']:.1f}%"
                 if "flux_nan_fraction" in r else None),
                ("Regime guess", r.get("regime_guess")),
                ("specutils reads it?", "yes" if r.get("specutils", {}).get("auto_read")
                 else f"no — {r.get('specutils', {}).get('error', '')}")]
        out += [f"| {k} | {v} |" for k, v in rows if v not in (None, "")]
        out.append("")

        hk = r.get("header_keys") or {}
        out += ["### Header metadata found", ""]
        if hk:
            out += ["| Keyword | Value |", "|---|---|"] + [f"| `{k}` | {v} |" for k, v in hk.items()]
        else:
            out.append("_None of the standard keywords are present._")
        out.append("")

        fh = r.get("filename_hints") or filename_hints(name)
        if fh:
            out += ["### Hints from the filename (unconfirmed)", ""]
            labels = {"designation_coords_deg": "RA/Dec from designation (deg)",
                      "obs_date": "Observation date", "reduction_date": "Reduction date (not DATE-OBS)",
                      "instrument": "Instrument"}
            out += [f"- **{labels.get(k, k)}:** {', '.join(map(str, v)) if isinstance(v, list) else v}"
                    for k, v in fh.items()]
            out.append("")

        if r.get("notes"):
            out += ["### Notes", ""] + [f"- {n}" for n in r["notes"]] + [""]

        qs = []
        if r.get("layout") == "image-2d-stacked":
            qs.append("Confirm row order: row 0 = wavelength, row 1 = flux, row 2 = uncertainty?")
        if r.get("wave_guess") or r.get("flux_guess"):
            unit_hint = any(k in hk for k in ("XUNITS", "YUNITS", "CUNIT1", "BUNIT"))
            qs.append("Confirm units" + ("" if unit_hint else
                      " (no unit keywords in header — guesses are from value ranges only)") + ".")
        for m in r.get("missing_metadata", missing_metadata(hk)):
            src = ""
            if m == "DATE-OBS" and fh.get("obs_date"):
                src = f" Filename suggests {fh['obs_date']}."
            if m in ("RA_TARG", "DEC_TARG") and fh.get("designation_coords_deg"):
                src = " Filename designation gives approximate coordinates."
            qs.append(f"Missing `{m}`: where should it come from?{src}")
        if qs:
            out += ["### Questions before converting", ""] + [f"- [ ] {q}" for q in qs] + [""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--json", help="write machine-readable report here")
    ap.add_argument("--md", help="write human-readable Markdown report here")
    ap.add_argument("--from-json", help="skip inspection; render Markdown from an existing JSON report")
    ap.add_argument("--title", default="Spectrum Inspection Report")
    args = ap.parse_args()

    if args.from_json:
        reports = json.loads(Path(args.from_json).read_text())
    else:
        if not args.files:
            ap.error("give FILES or --from-json")
        reports = [inspect_file(f) for f in args.files]

    if args.json and not args.from_json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(reports, indent=2, default=str))
        print(f"JSON report: {args.json}")
    md = render_markdown(reports, args.title)
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(md)
        print(f"Markdown report: {args.md}")
    if not args.json and not args.md:
        print(json.dumps(reports, indent=2, default=str))


if __name__ == "__main__":
    main()

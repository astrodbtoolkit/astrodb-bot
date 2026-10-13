"""
Inspect one or more spectrum files and classify their layout BEFORE writing a converter.

This is a real, runnable diagnostic tool (unlike convert_spectra.py, which is a template).
Run it on every input file in Step 2 of SKILL.md and show the user the summary.

    python scripts/inspect_spectrum.py path/to/file.fits [more files or globs ...]
    python scripts/inspect_spectrum.py "data/*.fits" --json inspect.json
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

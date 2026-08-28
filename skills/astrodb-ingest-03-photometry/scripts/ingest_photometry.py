"""
REFERENCE TEMPLATE — do NOT copy this file verbatim into astrodb-ingest-artifacts/.

Read it for structure (config block -> filter setup phase -> ingest loop -> summary), then
write a tailored script named astrodb-ingest-artifacts/ingest_{LABEL}_photometry.py using the
user's real column names, file path, BAND_SETUP, and SOURCE_NAME_MAP. Every value below is a
placeholder to be replaced with a real one — never leave placeholders in the generated script.
"""

import logging

import numpy as np
from astropy.table import Table

from astrodb_utils import AstroDBError, build_db_from_json
from astrodb_utils.photometry import ingest_photometry, ingest_photometry_filter
from astrodb_utils.sources import find_source_in_db
from astrodb_utils.utils import get_db_regime

logging.getLogger("astrodb_utils").setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s - %(message)s")

SAVE_DB = False  # set True only after a clean dry run, on explicit user confirmation

# --- Project layout (confirmed with the user) ---
SETTINGS_FILE = "database.toml"
TABLE_PATH = "path/to/file.fits"  # confirmed in Step 1

# --- Column mapping — filled from Step 3 confirmation (use ACTUAL column names) ---
SOURCE_COL = "Name"          # required — source name column
REFERENCE_COL = "Reference"  # required — must already exist in Publications
EPOCH_COL = None             # optional — column name or None
COMMENTS_COL = None          # optional — column name or None
# regime is NOT a data column — it is derived from each band's SVO filter (see resolve_regimes)

# --- Bands — one entry per magnitude column present in the table (from Steps 3-4) ---
# The per-band telescope (4th field) is written to Photometry.telescope; set it to None to omit.
# (magnitude_column, svo_id, error_column_or_None, telescope_or_None)
BANDS = [
    ("Jmag", "2MASS/2MASS.J", "e_Jmag", "2MASS"),
    ("Hmag", "2MASS/2MASS.H", "e_Hmag", "2MASS"),
    ("W1mag", "WISE/WISE.W1", "e_W1mag", "WISE"),
]

# --- Filter setup — {svo_id: (telescope, instrument, filter_name)} for every band above (Step 4) ---
# ingest_photometry_filter fetches SVO metadata and creates the Telescopes + Instruments rows too.
BAND_SETUP = {
    "2MASS/2MASS.J": ("2MASS", "2MASS", "J"),
    "2MASS/2MASS.H": ("2MASS", "2MASS", "H"),
    "WISE/WISE.W1": ("WISE", "WISE", "W1"),
}

# --- Canonical source names — {data_table_name: Sources.source} from Step 2 ---
# Leave as {} to resolve inline via find_source_in_db (below); prefer the Step 2 map when you have it.
SOURCE_NAME_MAP = {}


def is_missing(value):
    """True for masked / None / NaN / empty cells that should be skipped."""
    if value is None or value is np.ma.masked:
        return True
    try:
        return bool(np.isnan(float(value)))
    except (TypeError, ValueError):
        return str(value).strip() == ""


def canonical_source(db, raw_name):
    """Resolve a data-table name to a single Sources.source, or None if not unique."""
    if raw_name in SOURCE_NAME_MAP:
        return SOURCE_NAME_MAP[raw_name]
    matches = find_source_in_db(db, raw_name)
    return matches[0] if len(matches) == 1 else None


def categorize(error_message):
    """Bucket an AstroDBError from ingest_photometry by its message (flags has no message key)."""
    msg = str(error_message)
    if "may be a duplicate" in msg:
        return "skipped_duplicate"
    if "not found in PhotometryFilters" in msg:
        return "skipped_band_missing"
    if "No unique source match" in msg:
        return "skipped_source_missing"
    if "not found in Publications" in msg:
        return "skipped_reference_missing"
    if "not found in Telescopes" in msg:
        return "skipped_telescope_missing"
    return "skipped_other"


def setup_filters(db):
    """Phase A — ensure every band's PhotometryFilters/Telescopes/Instruments rows exist FIRST."""
    created = 0
    for svo_id, (telescope, instrument, filter_name) in BAND_SETUP.items():
        exists = (
            db.query(db.PhotometryFilters)
            .filter(db.PhotometryFilters.c.band == svo_id)
            .table()
        )
        if len(exists):
            logger.info(f"Filter already present: {svo_id}")
            continue
        try:
            ingest_photometry_filter(
                db, telescope=telescope, instrument=instrument, filter_name=filter_name
            )
            created += 1
            logger.info(f"Filter created: {svo_id}")
        except AstroDBError as e:
            # "already exists" is fine; a real SVO/lookup failure needs user attention.
            logger.warning(f"Filter {svo_id}: {e}")
    return created


def regime_from_wavelength(wave_ang):
    """Coarse regime from a filter's effective wavelength (Angstroms)."""
    if wave_ang < 3000:
        return "ultraviolet"
    if wave_ang < 10000:
        return "optical"
    if wave_ang < 30000:
        return "nir"      # near-infrared (J/H/K)
    return "mir"          # mid-infrared (WISE, etc.)


def resolve_regimes(db):
    """{svo_id: canonical RegimeList regime} derived from each filter's SVO effective wavelength.

    get_db_regime returns None when the derived regime is not in RegimeList — surface those to the
    user (add the regime, or pick an existing one) rather than ingesting a regime the FK will reject.
    """
    regimes = {}
    for svo_id in BAND_SETUP:
        row = (
            db.query(db.PhotometryFilters)
            .filter(db.PhotometryFilters.c.band == svo_id)
            .table()
        )
        if len(row) == 0:
            continue
        eff = float(row["effective_wavelength_angstroms"][0])
        regime = get_db_regime(db, regime_from_wavelength(eff), raise_error=False)
        if regime is None:
            logger.warning(
                f"Regime for {svo_id} (~{eff:.0f} A) not in RegimeList — add it or pick one with the user."
            )
        regimes[svo_id] = regime
    return regimes


def ingest_all(db, data, band_regime):
    """Phase B — ingest each (source, band) magnitude, bucketing skips by reason."""
    counts = {
        "ingested": 0,
        "skipped_missing_value": 0,
        "skipped_duplicate": 0,
        "skipped_band_missing": 0,
        "skipped_source_missing": 0,
        "skipped_reference_missing": 0,
        "skipped_telescope_missing": 0,
        "skipped_other": 0,
    }
    for row in data:
        source = canonical_source(db, str(row[SOURCE_COL]))
        if source is None:
            counts["skipped_source_missing"] += 1
            logger.warning(f"No unique source match for {row[SOURCE_COL]}")
            continue
        reference = str(row[REFERENCE_COL])
        for mag_col, svo_id, err_col, telescope in BANDS:
            if mag_col not in data.colnames or is_missing(row[mag_col]):
                counts["skipped_missing_value"] += 1
                continue
            kwargs = dict(
                source=source,
                band=svo_id,
                magnitude=float(row[mag_col]),
                reference=reference,
                raise_error=True,
            )
            if err_col and not is_missing(row[err_col]):
                kwargs["magnitude_error"] = float(row[err_col])
            if telescope:
                kwargs["telescope"] = telescope
            regime = band_regime.get(svo_id)
            if regime:
                kwargs["regime"] = regime
            if EPOCH_COL and not is_missing(row[EPOCH_COL]):
                kwargs["epoch"] = float(row[EPOCH_COL])
            if COMMENTS_COL and not is_missing(row[COMMENTS_COL]):
                kwargs["comments"] = str(row[COMMENTS_COL])
            try:
                flags = ingest_photometry(db, **kwargs)
                if flags["added"]:
                    counts["ingested"] += 1
                    logger.info(f"Ingested: {source} {svo_id} = {row[mag_col]}")
            except AstroDBError as e:
                bucket = categorize(e)
                counts[bucket] += 1
                logger.warning(f"Skipping {source} {svo_id}: {e}")
    return counts


if __name__ == "__main__":
    db = build_db_from_json(settings_file=SETTINGS_FILE)

    data = Table.read(TABLE_PATH)
    logger.info(f"Loaded {len(data)} rows from {TABLE_PATH}")

    filters_created = setup_filters(db)
    band_regime = resolve_regimes(db)
    counts = ingest_all(db, data, band_regime)

    logger.info(
        f"Done: {counts['ingested']} ingested, "
        f"{sum(v for k, v in counts.items() if k.startswith('skipped'))} skipped; "
        f"{filters_created} filters created"
    )
    for key, value in counts.items():
        logger.info(f"  {key}: {value}")

    if SAVE_DB:
        db.save_database(directory="data/")
        logger.info("Database saved to data/")
    else:
        logger.info(
            "Dry run complete — NOT saved. Set SAVE_DB = True to write the database to JSON files."
        )

# ---------------------------------------------------------------------------
# Ingest summary — fill in with the real counts from the dry run (issue #24):
#   Filters created:            <N>
#   Measurements ingested:      <X>
#   Skipped (missing value):    <...>
#   Skipped (duplicate):        <...>
#   Skipped (band missing):     <...>
#   Skipped (source missing):   <...>
#   Skipped (reference missing):<...>
#   Skipped (other):            <...>
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Asymmetric errors (magnitude_error_upper / magnitude_error_lower)
# ---------------------------------------------------------------------------
# ingest_photometry only accepts a single symmetric magnitude_error. When the
# data has asymmetric errors, DON'T drop or silently average them — ingest with
# a small custom insert modeled on ingest_photometry: validate source/band/
# reference the same way, then write the upper/lower columns directly.
#
# from astrodb_utils.publications import find_publication
#
# def ingest_asymmetric(db, *, source, band, magnitude, reference,
#                       err_upper, err_lower, telescope=None, regime=None, epoch=None):
#     assert len(find_source_in_db(db, source)) == 1, f"source not unique: {source}"
#     assert find_publication(db, reference=reference)[0], f"reference missing: {reference}"
#     assert len(db.query(db.PhotometryFilters)
#                .filter(db.PhotometryFilters.c.band == band).table()) == 1, f"band missing: {band}"
#     row = {"source": source, "band": band, "magnitude": str(magnitude),
#            "magnitude_error_upper": str(err_upper), "magnitude_error_lower": str(err_lower),
#            "telescope": telescope, "regime": regime, "epoch": epoch, "reference": reference}
#     with db.engine.connect() as conn:
#         conn.execute(db.Photometry.insert().values(row))
#         conn.commit()
# ---------------------------------------------------------------------------

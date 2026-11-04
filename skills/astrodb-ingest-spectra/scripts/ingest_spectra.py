"""
REFERENCE TEMPLATE — read this to understand the ingest_spectrum pattern.
Do NOT copy this file verbatim into a real run. Write a tailored script to
astrodb-ingest-artifacts/ingest_{REF}_spectra.py using the user's actual
column names, canonical source-name mapping (Step 2), and permalink base URL
(Step 3.5) confirmed in the conversation.

Adapted from a working SIMPLE-db ingest script — structure only, not values.
"""
import logging
from datetime import datetime

import pandas as pd
from astrodb_utils import build_db_from_json
from astrodb_utils.spectra import check_spectrum_plottable, ingest_spectrum

astrodb_utils_logger = logging.getLogger("astrodb_utils")
astrodb_utils_logger.setLevel(logging.INFO)
logger = logging.getLogger("astrodb_utils.ingest_spectra")
logger.setLevel(logging.INFO)

# --- Config (fill in with real values, never placeholders) ---
SAVE_DB = False  # dry run first
SETTINGS_FILE = "database.toml"
DATA_FILE = "path/to/data_table.csv"

# {data_table_name: canonical_source} -- built in Step 2 (Names/other_name resolution)
SOURCE_NAME_MAP = {}

# Optional: names to exclude this run, with a reason each (e.g. known bad file, unresolved source)
SKIP_NAMES = {}  # {"Some Name": "reason"}

# Permalink base URL confirmed with the user in Step 3.5 -- never hardcode a specific bucket
SPECTRUM_BASE_URL = ""
ORIGINAL_SPECTRUM_BASE_URL = ""  # optional, only if a separate raw/original file exists


def build_url(base_url, filename):
    """Join a base URL and filename, URL-encoding characters like '+'."""
    return (base_url + str(filename)).replace("+", "%2B")


def parse_obs_date(raw):
    """Parse to ISO format. Returns None if unparseable -- caller must skip the row,
    since observation_date is part of the Spectra table's primary key and cannot be null."""
    if not raw or pd.isna(raw):
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def categorize_skip(message):
    """Bucket an ingest_spectrum flags['message'] into a skip-reason category.
    Match against the message text since ingest_spectrum doesn't return a
    structured error code. Only duplicate/no-date get their own bucket --
    other failure modes (missing reference, unresolved source, bad regime,
    unknown instrument) should already have been caught earlier, during
    Step 2 (source resolution) and the Prerequisites checks (Step 3), so a
    single 'other' bucket with the logged message is enough for them."""
    msg = (message or "").lower()
    if "duplicate" in msg:
        return "skipped_duplicate"
    if "observation date" in msg or "obs_date" in msg:
        return "skipped_no_date"
    return "skipped_other"


def ingest_spectra(db, data):
    counts = {
        "ingested": 0, "skipped_not_plottable": 0, "skipped_duplicate": 0,
        "skipped_no_date": 0, "skipped_other": 0,
    }

    for _, row in data.iterrows():
        raw_name = row["NAME_COLUMN"]  # replace with real column name

        if raw_name in SKIP_NAMES:
            logger.info(f"Skipping {raw_name}: {SKIP_NAMES[raw_name]}")
            counts["skipped_other"] += 1
            continue

        canonical_source = SOURCE_NAME_MAP.get(raw_name)
        if canonical_source is None:
            logger.warning(f"Skipping {raw_name}: no resolved Sources.source match")
            counts["skipped_other"] += 1
            continue

        obs_date = parse_obs_date(row["DATE_COLUMN"])  # replace with real column name
        if obs_date is None:
            logger.warning(f"Skipping {raw_name}: missing/unparseable obs_date (required, part of PK)")
            counts["skipped_no_date"] += 1
            continue

        spectrum_url = build_url(SPECTRUM_BASE_URL, row["FILENAME_COLUMN"])
        original_url = (
            build_url(ORIGINAL_SPECTRUM_BASE_URL, row["ORIGINAL_FILENAME_COLUMN"])
            if ORIGINAL_SPECTRUM_BASE_URL else None
        )

        regime = row["REGIME_COLUMN"]
        reference = row["REFERENCE_COLUMN"]

        # check_spectrum_plottable is called separately (and wrapped) because
        # ingest_spectrum calls it internally without honoring raise_error=False --
        # a bad URL would otherwise raise uncaught even with raise_error=False below.
        try:
            check_spectrum_plottable(spectrum_url, raise_error=False, show_plot=False)
        except Exception as e:
            logger.warning(f"Skipping {raw_name}: not plottable ({e})")
            counts["skipped_not_plottable"] += 1
            continue

        # ingest_spectrum handles source/reference/regime/instrument validation,
        # obs_date parsing, and duplicate detection (all five PK columns) internally.
        # No separate find_spectra pre-check is needed here.
        flags = ingest_spectrum(
            db,
            source=canonical_source,
            spectrum=spectrum_url,
            original_spectrum=original_url,
            regime=regime,
            telescope=row["TELESCOPE_COLUMN"],
            instrument=row["INSTRUMENT_COLUMN"],
            mode=row["MODE_COLUMN"],
            obs_date=obs_date,
            reference=reference,
            raise_error=False,
        )

        if flags["added"]:
            counts["ingested"] += 1
            logger.info(f"Ingested spectrum for {raw_name}")
        else:
            category = categorize_skip(flags["message"])
            counts[category] += 1
            logger.warning(f"Skipping {raw_name}: {flags['message']}")

    return counts


if __name__ == "__main__":
    db = build_db_from_json(settings_file=SETTINGS_FILE)
    data = pd.read_csv(DATA_FILE)
    counts = ingest_spectra(db, data)

    print(f"Total rows: {len(data)}")
    for k, v in counts.items():
        print(f"{k}: {v}")

    if SAVE_DB:
        db.save_database(directory="data/")
        logger.info("Database JSON files written to disk")
    else:
        print("Dry run complete — NOT saved. Set SAVE_DB = True to write the database to JSON files.")

# Ingest summary (fill in with real counts from the run above, not placeholders):
# Total spectra attempted:
# Successfully ingested:
# Skipped (duplicate):
# Skipped (not plottable / unreachable):
# Skipped (missing obs_date):
# Skipped (other):
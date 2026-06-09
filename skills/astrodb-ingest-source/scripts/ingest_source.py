
import logging
from astropy.table import Table
from astrodb_utils import build_db_from_json
from astrodb_utils.sources import ingest_source

logging.getLogger("astrodb_utils").setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s - %(message)s")

SAVE_DB = False  # set True only after a clean dry run

# Adjust to match your project layout
SETTINGS_FILE = "database.toml"

db = build_db_from_json(
    settings_file=SETTINGS_FILE,
)

# --Load data table--
TABLE_PATH    = "path/to/file.fits"  # confirmed in Step 1
data = Table.read(TABLE_PATH)
logger.info(f"Loaded {len(data)} rows from {TABLE_PATH}")

# --- Column mapping — filled from Step 2 confirmation ---
# Use the ACTUAL column names from your file (not assumed defaults)
SOURCE_COL    = "Name"               # confirmed in Step 2 — required
REFERENCE_COL = "Reference"         # confirmed in Step 2 — required
RA_COL        = "RA"                 # confirmed in Step 2 — set to None → SIMBAD fallback
DEC_COL       = "Dec"               # confirmed in Step 2 — set to None → SIMBAD fallback

# Optional columns — set to None if not present in table
EPOCH_COL     = None                 # optional — set to column name if present
EQUINOX_COL   = None                 # optional — set to column name if present
COMMENT_COL   = None                 # optional — set to column name if present
OTHER_REF_COL = None                 # optional — set to column name if present

# --- DB schema column names — confirmed in Step 2B ---
# These are column names IN the database Sources table, not the input file.
# astrodb-template-db defaults: ra_deg, dec_deg, epoch_year
# SIMPLE-db uses:               ra,     dec,     epoch
# To check your DB: print(db.metadata.tables["Sources"].columns.keys())
RA_COL_NAME    = "ra_deg"
DEC_COL_NAME   = "dec_deg"
EPOCH_COL_NAME = "epoch_year"

# Ingest Loop
sources_added = sources_skipped = 0
for row in data:
    source_name = str(row[SOURCE_COL])
    try:
        ingest_source(
            db,
            source=source_name,
            reference=str(row[REFERENCE_COL]),
            ra=float(row[RA_COL]) if RA_COL else None,
            dec=float(row[DEC_COL]) if DEC_COL else None,
            epoch=str(row[EPOCH_COL]) if EPOCH_COL else None,
            equinox=str(row[EQUINOX_COL]) if EQUINOX_COL else None,
            other_reference=str(row[OTHER_REF_COL]) if OTHER_REF_COL else None,
            comment=str(row[COMMENT_COL]) if COMMENT_COL else None,
            ra_col_name=RA_COL_NAME,
            dec_col_name=DEC_COL_NAME,
            epoch_col_name=EPOCH_COL_NAME,
            raise_error=True,
        )
        sources_added += 1
        logger.info(f"Ingested: {source_name}")
    except Exception as e:
        sources_skipped += 1
        logger.warning(f"Skipping {source_name}: {e}")
 
logger.info(f"Done: {sources_added} ingested, {sources_skipped} skipped out of {len(data)} rows")

if SAVE_DB:
    db.save_database(directory="data/")
    logger.info("Database saved to data/")
else:
    logger.info("Dry run complete — NOT saved. Set SAVE_DB = True to write the database to JSON files.")

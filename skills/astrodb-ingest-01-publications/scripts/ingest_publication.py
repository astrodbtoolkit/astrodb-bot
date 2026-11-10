"""
Template: ingest publications into an AstroDB Publications table.

This is a PATTERN to adapt — not a script to run as-is. Replace SETTINGS_FILE and the
PUBLICATIONS list with the user's real values (Steps 1-2 of the skill). For a batch,
build PUBLICATIONS from a table column instead of hand-listing it (see the commented
example near the bottom).
"""

import logging

from astrodb_utils import build_db_from_json
from astrodb_utils.publications import (
    ingest_publication,
    find_publication,
    check_ads_token,
)

logging.getLogger("astrodb_utils").setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format="%(levelname)s - %(message)s")

SAVE_DB = False  # set True only after a clean dry run, on explicit user confirmation

# Adjust to match your project layout (Step: Prerequisites)
SETTINGS_FILE = "database.toml"

# ADS auto-populates bibcode/doi/description from a DOI or bibcode, but needs a token.
# If no token is configured, set IGNORE_ADS = True and give each entry a `reference`.
IGNORE_ADS = not check_ads_token()
if IGNORE_ADS:
    logger.warning(
        "No ADS token found — ingesting with ignore_ads=True. "
        "Each publication must include a 'reference' shortname; "
        "bibcode/description will NOT be auto-fetched."
    )

# --- Publications to ingest — filled from Step 1-2 confirmation ---
# Each entry needs at least one identifier. With an ADS token, a DOI or bibcode is enough.
# Without a token (IGNORE_ADS=True), include a 'reference' shortname (and optionally a
# 'description'). Use ACTUAL values — never leave placeholder strings in the file.
PUBLICATIONS = [
    {"doi": "10.1088/0004-637X/748/2/93"},                 # auto-populated via ADS
    # {"bibcode": "2012ApJ...748...93R"},                  # bibcode also works
    # {"reference": "Rojas12",                             # no token / bare shortname:
    #  "description": "Discovery paper for ...",           #   supply metadata by hand
    #  "doi": "10.1088/0004-637X/748/2/93"},
]

db = build_db_from_json(settings_file=SETTINGS_FILE)


def find_existing(db, doi=None, bibcode=None):
    """Return the reference of the row with this DOI or bibcode, or None.

    Search by DOI and bibcode only — never pass `reference` to find_publication.
    With a reference it falls back to a fuzzy "first 4 letters + 2-digit year"
    match, so e.g. "Shipp2020" (or "Ship20") returns "Shipp2019" and the new
    paper is wrongly skipped as already present.
    """
    for key, value in (("doi", doi), ("bibcode", bibcode)):
        if value:
            found, result = find_publication(db, **{key: value})
            if found:
                return result
            if result:  # (False, N): N rows already share this DOI/bibcode
                logger.warning(f"{result} rows already have {key} {value} — check for duplicates")
                return f"{result} existing rows"
    return None


def reference_taken(db, reference):
    """True if this exact shortname is already used (exact match, not fuzzy)."""
    return bool(reference) and (
        db.query(db.Publications).filter(db.Publications.c.reference == reference).count() > 0
    )


added = already_present = failed = 0
for pub in PUBLICATIONS:
    doi = pub.get("doi")
    bibcode = pub.get("bibcode")
    reference = pub.get("reference")
    label = reference or doi or bibcode

    # Deduplicate first — report existing rows instead of re-ingesting them.
    existing = find_existing(db, doi=doi, bibcode=bibcode)
    if existing:
        already_present += 1
        logger.info(f"Already present, skipping: {label} ({existing})")
        continue
    if reference_taken(db, reference):
        if doi or bibcode:
            # Same shortname, different paper: a collision, not a duplicate.
            failed += 1
            logger.warning(
                f"Shortname {reference} is already used by a different paper — "
                "add the DOI suffix to both (see the naming convention) and re-run."
            )
        else:
            already_present += 1
            logger.info(f"Already present (exact shortname match), skipping: {reference}")
        continue

    try:
        ingest_publication(
            db,
            doi=doi,
            bibcode=bibcode,
            reference=reference,
            description=pub.get("description"),
            ignore_ads=IGNORE_ADS,
        )
        added += 1
        logger.info(f"Ingested: {label}")
    except Exception as e:
        failed += 1
        logger.warning(f"Failed to ingest {label}: {e}")

logger.info(
    f"Done: {added} added, {already_present} already present, {failed} failed "
    f"out of {len(PUBLICATIONS)} publications"
)

if SAVE_DB:
    db.save_database()
    logger.info("Database saved.")
else:
    logger.info(
        "Dry run complete — NOT saved. Set SAVE_DB = True to write the database to JSON files."
    )

# --- Batch helper: build PUBLICATIONS from a table column instead of hand-listing ---
# Replace the PUBLICATIONS literal above with something like:
#
#     from astropy.table import Table
#     data = Table.read("path/to/file.ecsv")     # auto-detects .fits/.csv/.ecsv
#     refs = sorted({str(r).strip() for r in data["reference"] if str(r).strip()})
#     PUBLICATIONS = [{"reference": r} for r in refs]   # bare shortnames -> IGNORE_ADS=True
#
# If the column holds DOIs instead, use {"doi": d} and an ADS token to auto-populate.

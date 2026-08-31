"""
Template: backfill missing metadata for references that ALREADY exist in a
Publications table (bibcode / doi / description are blank).

This is a PATTERN to adapt — not a script to run as-is. Phase 1 (resolving each
shortname to a real DOI/bibcode/title) happens before this script: do it with the
agent + the database's own context (the stream/object each reference is attached
to), confirm the resolved table with the user, then drop the verified values into
METADATA below. Only run this script after the user has confirmed the resolved table.

Two database forms are supported:
  - standalone .sqlite  -> direct UPDATE (default below; the row already exists, so
                           re-ingesting would collide on the `reference` primary key)
  - JSON template layout -> see the ADS variant at the bottom

Idempotent: a reference whose metadata is already present is left untouched.
"""

import sqlite3
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "path/to/database.sqlite"

# reference -> (bibcode, doi, description)   <- verified in Phase 1, confirmed with user
# Use real values, never placeholders. Leave a field as None only if it genuinely
# has no DOI/bibcode (rare for journal papers).
METADATA = {
    # "Bonaca2020": ("2020ApJ...892L..37B", "10.3847/2041-8213/ab800c",
    #                "High-resolution Spectroscopy of the GD-1 Stellar Stream ..."),
}

con = sqlite3.connect(DB_PATH)
# Use rollback-journal, not WAL, so the .sqlite file stays self-contained. Otherwise the
# updates can live in a `-wal` sidecar and a plain `cp` of just the .sqlite loses them.
con.execute("PRAGMA journal_mode=DELETE")
cur = con.cursor()

existing = {r[0] for r in cur.execute("SELECT reference FROM Publications")}
filled = skipped = missing = 0
for ref, (bibcode, doi, desc) in METADATA.items():
    if ref not in existing:
        print(f"  ! {ref}: not in Publications — skipping (add it with the ingest flow first)")
        missing += 1
        continue
    bib0, doi0, desc0 = cur.execute(
        "SELECT bibcode, doi, description FROM Publications WHERE reference=?", (ref,)
    ).fetchone()
    if any(v not in (None, "") for v in (bib0, doi0, desc0)):
        print(f"  = {ref}: metadata already present — leaving as is")
        skipped += 1
        continue
    cur.execute(
        "UPDATE Publications SET bibcode=?, doi=?, description=? WHERE reference=?",
        (bibcode, doi, desc, ref),
    )
    filled += 1
    print(f"  + {ref}: {bibcode} | {doi}")

con.commit()
print(f"\nDone: {filled} filled, {skipped} already present, {missing} missing.")
nulls = cur.execute(
    "SELECT COUNT(*) FROM Publications "
    "WHERE bibcode IS NULL OR doi IS NULL OR description IS NULL"
).fetchone()[0]
print(f"Rows still missing any metadata: {nulls}")
con.close()

# --- JSON template-layout variant (when you have database.toml + data/ and an ADS token) ---
# Instead of a direct UPDATE you can let ADS fill bibcode/description from the DOI:
#
#     from astrodb_utils import build_db_from_json
#     from astrodb_utils.publications import ingest_publication, get_db_publication
#     db = build_db_from_json(settings_file="database.toml")
#     for ref, doi in REF_TO_DOI.items():
#         if get_db_publication(db, ref, raise_error=False):
#             # blank row already exists -> a fresh ingest would collide on the PK;
#             # update it directly via db.engine instead, or remove+re-ingest deliberately.
#             ...
#         else:
#             ingest_publication(db, doi=doi, reference=ref)   # ADS fills the rest
#     # db.save_database()   # only after a confirmed dry run

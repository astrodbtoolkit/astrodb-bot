# astrodb_utils.sources API Reference

Source of truth: https://github.com/astrodbtoolkit/astrodb_utils/blob/main/astrodb_utils/sources.py
Do NOT copy sources.py into this skill — always use the installed package.

---

## ingest_source signature

```python
from astrodb_utils.sources import ingest_source

ingest_source(
    db,                             # astrodbkit Database object (from build_db_from_json)
    source,                         # str — source name
    reference: str,                 # str — must exist in Publications table
    *,
    ra: float = None,               # decimal degrees; None → SIMBAD lookup
    dec: float = None,              # decimal degrees; None → SIMBAD lookup
    epoch: str = None,              # e.g. "2000.0"
    equinox: str = None,            # e.g. "J2000"
    other_reference: str = None,
    comment: str = None,
    raise_error: bool = True,       # True = stop on error; False = warn and skip
    search_db: bool = True,         # True = check for duplicates before inserting
    ra_col_name: str = "ra_deg",    # column name in the DB Sources table for RA
    dec_col_name: str = "dec_deg",  # column name in the DB Sources table for Dec
    epoch_col_name: str = "epoch_year",
    use_simbad: bool = True,        # query SIMBAD if RA/Dec missing or name unresolved
)
```

Returns None. Side effects: inserts into `Sources` and `Names`.
If source already exists: adds new name as alternate in `Names` only.

---

## ra_col_name / dec_col_name

These are column names **in the database Sources table** — not in the input data file.
Defaults (`ra_deg`, `dec_deg`) match astrodb-template-db. Only change if your DB schema differs.

--- 

## Common warnings and fixes

| Warning | Cause | Fix |
|---------|-------|-----|
| `Discovery reference X missing or not in Publications` | Reference not in Publications | Run `ingest_publication` first |
| `Coordinates needed and could not be retrieved from SIMBAD` | No RA/Dec + SIMBAD can't resolve name | Provide RA/Dec columns, or check source name spelling |
| `More than one match for X` | Name resolves to multiple DB candidates | Investigate duplicates manually |
| `No internet connection, not using Simbad` | SIMBAD unreachable | Provide RA/Dec explicitly |
| `Coordinates do not match for X` | Provided RA/Dec >60 arcsec from DB entry | Check coordinate columns and units |
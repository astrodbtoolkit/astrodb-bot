# astrodb_utils.publications API Reference

Source of truth: https://github.com/astrodbtoolkit/astrodb_utils/blob/main/astrodb_utils/publications.py
Docs: https://astrodb-utils.readthedocs.io/en/stable/pages/db_access/ingesting/ingesting_publications.html
Do NOT copy publications.py into this skill — always use the installed package.

---

## ingest_publication signature

```python
from astrodb_utils.publications import ingest_publication

ingest_publication(
    db,                          # astrodbkit Database object (from build_db_from_json)
    *,                           # everything below is keyword-only
    doi: str = None,             # DOI of the reference        — one of doi/bibcode needed
    bibcode: str = None,         # ADS bibcode of the reference — one of doi/bibcode needed
    reference: str = None,       # short identifier (e.g. "Rojas12"); auto-generated if omitted
    description: str = None,     # paper description, typically the title
    ignore_ads: bool = False,    # True = skip ADS lookup (then you must supply reference)
)
```

Returns None. Side effect: inserts a row into `Publications`.

- With a DOI **or** bibcode and `ignore_ads=False`, ADS is queried and `reference`,
  `bibcode`, `doi`, and `description` are auto-populated. Requires `ADS_TOKEN` (see below).
- With `ignore_ads=True`, nothing is fetched — supply `reference` yourself (and
  `description` if wanted). Use this when there is no ADS token, or when all you have is a
  bare reference shortname with no DOI/bibcode.

## find_publication signature

```python
from astrodb_utils.publications import find_publication

found, result = find_publication(
    db,
    *,
    reference: str = None,   # search by shortname
    doi: str = None,         # search by DOI
    bibcode: str = None,     # search by bibcode
)
```

Return contract:
| Situation        | Returns            |
|------------------|--------------------|
| Exactly one match | `True, "<reference>"` |
| No matches        | `False, 0`         |
| Multiple matches  | `False, N_matches` |

Always call this **before** `ingest_publication` so a paper already in the database is
reported as "already present" instead of being ingested again.

## Supporting functions

```python
from astrodb_utils.publications import check_ads_token, get_db_publication
check_ads_token()                          # returns whether an ADS token is configured
get_db_publication(db, reference, raise_error=True)  # case-insensitive lookup of a shortname
```

## Loading the database

```python
from astrodb_utils import build_db_from_json
db = build_db_from_json(settings_file="database.toml")   # rebuilds .sqlite from JSON files
```

`build_db_from_json` reads the astrodb-template-db layout from `database.toml` and is the
same loader the other ingest skills use. (The published example uses
`read_db_from_file(db_name="SIMPLE")` instead — that reads an existing `.sqlite` directly.
Prefer `build_db_from_json` here so saving writes the JSON source files back out.)

Saving (only after a confirmed dry run):
```python
db.save_database()
```

---

## Resolving a reference when you have no DOI

This is the common case. `ingest_publication` needs a DOI or bibcode; a bare shortname
(`Cruz03`) or "author + year" is not enough. Resolve it first:

1. **Disambiguate with context.** A shortname maps to many possible papers, so use what the
   database knows. The object/stream a reference is attached to is the strongest clue — find
   it in `Associations` / `Sources` / `Photometry` / etc.:
   ```python
   # what object(s) does this reference describe?
   cur.execute("SELECT DISTINCT association FROM Associations WHERE reference=?", ("Bonaca2020",))
   # -> 'GD-1'  => this is the GD-1 paper, not some other Bonaca 2020
   ```
2. **Search** with author + year + object/topic on **Google Scholar**, **NASA ADS**
   (`https://ui.adsabs.harvard.edu/`), or **Crossref**. Crossref turns a title into a DOI
   reliably and needs no key:
   ```
   https://api.crossref.org/works?query.bibliographic=<author year object/title>&rows=1
       &select=DOI,title,container-title,volume,page,published
   ```
   NASA ADS gives the bibcode (`2020ApJ...892L..37B`); Crossref gives the DOI + exact
   title/volume/page (from which the bibcode also follows: `YYYY` + journal + volume + page
   + first-author initial).
3. **Verify before writing.** Check author, year, and that the title matches the object the
   reference is attached to. Wrong-paper metadata is worse than a blank row. Show the user
   the resolved `reference → title → DOI → bibcode → disambiguating context` and confirm.

Only after a verified DOI/bibcode is in hand do you call `ingest_publication` (or write the
row directly for a standalone sqlite backfill).

## ADS token setup

`ingest_publication` auto-fills metadata by querying NASA ADS, which needs a token.

1. Make an ADS account: https://ui.adsabs.harvard.edu/help/api/
2. Go to https://ui.adsabs.harvard.edu/user/settings/token and copy the token.
3. Export it so the shell (and Python) can see it:
   ```bash
   export ADS_TOKEN="<your token>"
   ```
   To persist it, add that line to `~/.zshenv` (zsh) or `~/.bashrc` (bash).

No token? Run with `ignore_ads=True` and supply `reference` (and `description`) by hand.

---

## reference naming convention

The `reference` is a short, unique identifier — first four letters of the first author's
last name + two-digit year:

- Smith et al. 2020 → `Smit20`
- Short last names: use first-name initials or underscores → `WuXi21` or `Wu__21`
- Multiple papers, same first-author/year: the **second paper does not get a variant
  shortname**. Instead, cite it in the `comments` field of the data row that references it
  (e.g. `Parallaxes.comments`, `Sources.comments`), using the last 4 characters of its DOI
  as a concise identifier — e.g. `see also 800c`. **Never use `a`, `b`, `c` letter
  suffixes** (`Smit20a`) and never append a DOI suffix to the shortname (`Smit20.800c`).

When ADS is available it generates this for you. When using `ignore_ads=True`, construct it
yourself with this rule (or use the shortname already present in the user's table).

---

## Common warnings and fixes

| Warning / error | Cause | Fix |
|-----------------|-------|-----|
| `ADS_TOKEN` not set / token errors | No ADS token in environment | Set the token, or use `ignore_ads=True` with a supplied `reference` |
| Publication already exists | Reference/DOI already in `Publications` | Expected — the dedup check skips it; not an error |
| Reference already exists (on insert) | Dedup check was skipped | Call `find_publication` before ingesting |
| ADS returns no match for a DOI | DOI typo, or paper not in ADS | Verify the DOI; or ingest with `ignore_ads=True` + manual metadata |
| Cannot reach ADS / network error | No internet | Retry with a connection, or `ignore_ads=True` |
| No DOI or bibcode and no reference | Entry has no usable identifier | Supply at least a `reference` shortname, and use `ignore_ads=True` |

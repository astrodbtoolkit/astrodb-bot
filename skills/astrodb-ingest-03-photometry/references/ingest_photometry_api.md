# astrodb_utils.photometry / .instruments API Reference

Source of truth: https://github.com/astrodbtoolkit/astrodb_utils/blob/main/astrodb_utils/photometry.py
Do NOT copy photometry.py into this skill — always use the installed package.

---

## ingest_photometry signature

```python
from astrodb_utils.photometry import ingest_photometry

ingest_photometry(
    db,                             # astrodbkit Database object (from build_db_from_json)
    *,                              # everything below is keyword-only
    source: str = None,            # REQUIRED — must resolve to one Sources.source (checked via find_source_in_db)
    band: str = None,              # REQUIRED — SVO filter ID; must already exist in PhotometryFilters
    magnitude: float = None,       # REQUIRED — stored as a string to preserve significant digits
    reference: str = None,         # REQUIRED — must exist in Publications
    regime: str = None,            # optional — e.g. "optical", "infrared"; only written if provided
    magnitude_error: float = None, # optional — symmetric error; masked values become None
    telescope: str = None,         # optional — if given, must exist in Telescopes
    epoch: float = None,           # optional
    comments: str = None,          # optional
    raise_error: bool = True,      # True = raise AstroDBError on any problem; False = warn and return
)
```

Returns a `flags` dict: `{"added": bool}`. **Note there is no `message` key** — unlike
`ingest_spectrum`. To classify *why* a row was skipped, call with `raise_error=True` and read the
`AstroDBError` message (see "Bucketing skip reasons" below). Side effect: one row inserted into
`Photometry`.

What it validates, in order (each raises `AstroDBError` when `raise_error=True`):

1. `source`, `band`, `magnitude`, `reference` are all provided.
2. `source` resolves to exactly one entry via `find_source_in_db` — else *"No unique source match for
   {source} in the database"*.
3. `reference` exists in `Publications` — else *"Reference {reference} not found in Publications
   table."*
4. `band` exists in `PhotometryFilters` — else *"Band {band} not found in PhotometryFilters table."*
5. If `telescope` is given, it exists in `Telescopes` — else *"Telescope {telescope} not found in
   Telescopes table."*
6. The insert itself — a `UNIQUE constraint failed` becomes *"The measurement may be a duplicate."*

There is **no** pre-check for duplicates; uniqueness is enforced by the DB constraint on insert. The
`Photometry` uniqueness constraint is on **`(source, band, reference)`** (per the schema docs) — it
does **not** include `epoch`. So repeated measurements of the same source in the same band from the
same reference but at different epochs collide, and all but the first come back as
*"may be a duplicate."* If a data table holds genuine multi-epoch / time-series photometry for one
band+reference, flag it for the user rather than silently dropping rows.

`magnitude_error_upper` / `magnitude_error_lower` exist in the `Photometry` schema (columns of type
`double`) but are **not** parameters of this function — only a symmetric `magnitude_error` is
supported. They are still ingestible with a custom insert — see "Ingesting asymmetric errors" below.

Column string caps (from the schema): `source` 100, `comments` 100, and `band` / `telescope` /
`reference` / `regime` 30 characters. A value over its cap raises an `IntegrityError` (not a UNIQUE
one), which the skip-bucketing catches as *other* — trim the value before ingest.

### Bucketing skip reasons

Because `flags` carries no message, categorize by matching the exception text:

| Substring in AstroDBError | Bucket |
|---|---|
| `may be a duplicate` | duplicate |
| `not found in PhotometryFilters` | band-missing |
| `No unique source match` | source-missing |
| `not found in Publications` | reference-missing |
| `not found in Telescopes` | telescope-missing |
| (anything else) | other |

---

## ingest_photometry_filter signature — sets up telescope + instrument + filter

```python
from astrodb_utils.photometry import ingest_photometry_filter

ingest_photometry_filter(
    db,
    *,
    telescope=None,      # e.g. "2MASS"  — created in Telescopes if missing
    instrument=None,     # e.g. "2MASS"  — created in Instruments (mode="Imaging") if missing
    filter_name=None,    # e.g. "J"
    ucd=None,            # auto-assigned from effective wavelength if None
    wavelength_col_name="effective_wavelength_angstroms",
    width_col_name="width_angstroms",
)
```

Side effects, in order: (1) inserts the `Telescopes` row if absent; (2) inserts the `Instruments` row
with `mode="Imaging"` if absent (via `ingest_instrument`); (3) calls `fetch_svo(telescope, instrument,
filter_name)` for the metadata; (4) inserts `PhotometryFilters` keyed on the **SVO-returned
`filter_id`** (i.e. `Facility/Instrument.Band`). Raises `AstroDBError` if the filter already exists or
SVO can't be reached. This is the mechanism for "set up instrument/telescope before the photometry
values": run it for every band up front, treating an *already exists* error as success.

The `band` stored is the SVO `filter_id` for `{telescope}/{instrument}.{filter_name}` — that exact
string is what you must pass as `band=` to `ingest_photometry`.

---

## fetch_svo — SVO validation helper

```python
from astrodb_utils.photometry import fetch_svo
filter_id, wave_eff, fwhm, width_effective = fetch_svo("2MASS", "2MASS", "J")
```

Queries `http://svo2.cab.inta-csic.es/svo/theory/fps3/fps.php?ID={telescope}/{instrument}.{filter_name}`.
Returns the filter ID plus effective wavelength, FWHM, and effective width as astropy `Quantity`
objects in Angstroms. Raises `AstroDBError` with no internet, a bad HTTP status, or an unknown filter
— use it to validate a band before committing to an SVO ID. `assign_ucd(wave_eff)` maps an effective
wavelength to a UCD string (e.g. `em.IR.J`); `ingest_photometry_filter` uses it automatically.

---

## ingest_instrument signature (for reference)

```python
from astrodb_utils.instruments import ingest_instrument
ingest_instrument(db, *, telescope=None, instrument=None, mode=None, raise_error=True)
```

Idempotent: inserts the `Telescopes` row and the `Instruments` (instrument+mode+telescope) row if
missing; does nothing if both already exist. Returns `None`. `ingest_photometry_filter` calls it for
you with `mode="Imaging"`, so you rarely call it directly — reach for it only when you need a
non-imaging mode (e.g. spectroscopy) or want to register an instrument without adding a filter.

---

## SVO filter IDs (band names)

`PhotometryFilters.band` **must** be an SVO Filter Profile Service ID of the form
`Facility/Instrument.Band` — never a bare band letter. Common mappings:

| Bare band | SVO filter ID | (telescope, instrument, filter_name) |
|---|---|---|
| J (2MASS) | `2MASS/2MASS.J` | `("2MASS", "2MASS", "J")` |
| H (2MASS) | `2MASS/2MASS.H` | `("2MASS", "2MASS", "H")` |
| K / Ks (2MASS) | `2MASS/2MASS.Ks` | `("2MASS", "2MASS", "Ks")` |
| W1 / W2 / W3 / W4 | `WISE/WISE.W1` … | `("WISE", "WISE", "W1")` … |
| u/g/r/i/z (SDSS) | `SDSS/SDSS.g` … | `("SDSS", "SDSS", "g")` … |
| G (Gaia DR3) | `Gaia/Gaia3.G` | `("Gaia", "Gaia3", "G")` |
| BP (Gaia DR3) | `Gaia/Gaia3.Gbp` | `("Gaia", "Gaia3", "Gbp")` |
| RP (Gaia DR3) | `Gaia/Gaia3.Grp` | `("Gaia", "Gaia3", "Grp")` |
| B / V (Johnson) | `Generic/Johnson.V` | `("Generic", "Johnson", "V")` |
| R / I (Cousins) | `Generic/Cousins.R` | `("Generic", "Cousins", "R")` |

For any band not listed, search the SVO FPS to find the exact ID:
https://svo2.cab.inta-csic.es/theory/fps3/ . If the telescope or instrument is ambiguous, **flag the
band and ask the user** to confirm rather than guessing.

---

## Common warnings and fixes

| Warning | Cause | Fix |
|---------|-------|-----|
| `Band X not found in PhotometryFilters table.` | Filter not set up yet | Run `ingest_photometry_filter` for that band first (Step 4) |
| `No unique source match for X in the database` | Source not in `Sources`/`Names`, or ambiguous | Ingest the source first (`astrodb-ingest-sources`) or fix the name |
| `Reference X not found in Publications table.` | Reference missing | Run `astrodb-ingest-publications` first |
| `Telescope X not found in Telescopes table.` | `telescope=` passed but no row | Let `ingest_photometry_filter` create it, or omit `telescope` |
| `The measurement may be a duplicate.` | UNIQUE constraint on insert | Expected on re-runs; report as "already present", not an error |
| `Error fetching filter data from SVO` | No internet, or unknown filter ID | Check connectivity; confirm the SVO ID exists in the FPS |
| Asymmetric error columns present | `magnitude_error_upper/lower` aren't `ingest_photometry` params | Write a custom insert that populates those columns — see "Ingesting asymmetric errors" |
| Repeated `may be a duplicate` on multi-epoch data | Key is `(source, band, reference)` — `epoch` is not in it | Flag time-series data; only one row per source+band+reference fits this key |
| `IntegrityError` value too long | A string exceeds its column cap (`source`/`comments` 100; `band`/`telescope`/`reference`/`regime` 30) | Trim/shorten the value before ingest |
| `Regime not found in database` | Derived regime isn't in `RegimeList` | Add it to `RegimeList` or pick an existing one with the user (see "Regime") |

---

## Regime — derived from the SVO filter (not a user column)

`Photometry.regime` links to the controlled `RegimeList` table. You don't need the user to supply it:
the band's SVO filter already gives the effective wavelength (stored in
`PhotometryFilters.effective_wavelength_angstroms` after `ingest_photometry_filter`), which determines
the regime. Bin the wavelength, then canonicalize against `RegimeList` with `get_db_regime`:

```python
from astrodb_utils.utils import get_db_regime

def regime_from_wavelength(wave_ang):   # Angstroms
    if wave_ang < 3000:   return "ultraviolet"
    if wave_ang < 10000:  return "optical"
    if wave_ang < 30000:  return "nir"    # J/H/K
    return "mir"                          # WISE, etc.

regime = get_db_regime(db, regime_from_wavelength(eff_wavelength), raise_error=False)
```

`get_db_regime(db, regime, raise_error=True)` matches `RegimeList` case- and hyphen-insensitively and
returns the canonical value, or `None` when it isn't in the table (its warning lists the available
regimes). If it returns `None`, **ask the user** — add the regime to `RegimeList` or pick an existing
one. `ingest_photometry` does not validate `regime` itself, so a value absent from `RegimeList` fails
the foreign key on insert (bucketed *other*) — resolve it first.

---

## Ingesting asymmetric errors

`ingest_photometry` takes only a symmetric `magnitude_error`, but the `Photometry` table has
`magnitude_error_upper` and `magnitude_error_lower` columns. When the data has asymmetric errors,
don't drop or silently average them — write a small custom insert modeled on `ingest_photometry`:
validate `source` / `reference` / `band` the same way, then insert with the upper/lower columns set.

```python
from astrodb_utils.sources import find_source_in_db
from astrodb_utils.publications import find_publication

def ingest_asymmetric(db, *, source, band, magnitude, reference,
                      err_upper, err_lower, telescope=None, regime=None, epoch=None):
    assert len(find_source_in_db(db, source)) == 1, f"source not unique: {source}"
    assert find_publication(db, reference=reference)[0], f"reference missing: {reference}"
    assert len(db.query(db.PhotometryFilters)
               .filter(db.PhotometryFilters.c.band == band).table()) == 1, f"band missing: {band}"
    row = {
        "source": source, "band": band, "magnitude": str(magnitude),
        "magnitude_error_upper": str(err_upper), "magnitude_error_lower": str(err_lower),
        "telescope": telescope, "regime": regime, "epoch": epoch, "reference": reference,
    }
    with db.engine.connect() as conn:
        conn.execute(db.Photometry.insert().values(row))
        conn.commit()
```

Confirm the upper/lower column mapping with the user first, and store magnitudes/errors as strings to
preserve significant digits (matching `ingest_photometry`).

# astrodb_utils.spectra API Reference

Source of truth: https://github.com/astrodbtoolkit/astrodb_utils/blob/main/astrodb_utils/spectra.py
Do NOT copy spectra.py into this skill — always use the installed package.

---

## check_spectrum_plottable signature

```python
from astrodb_utils.spectra import check_spectrum_plottable

check_spectrum_plottable(
    spectrum_path,             # str — URL or local path
    raise_error: bool = True,  # True = raise on failure; False = return False and warn
    show_plot: bool = False,   # True = display a plot (skip in scripted ingestion)
    format: str = None,        # e.g. "tabular-fits"; None = specutils auto-detect
)
```

Returns `True`/`False` (when `raise_error=False`) or raises on failure. The reference template
script (`scripts/ingest_spectra.py`) uses `raise_error=True` wrapped in a `try/except` inside
the ingest loop — functionally equivalent to `raise_error=False`, but keeps the failure-handling
logic in one visible place alongside the other per-row checks. Either pattern is fine; match
whichever the template already uses so scripts stay consistent with each other.

---

## find_spectra signature

```python
from astrodb_utils.spectra import find_spectra

find_spectra(
    db,
    source: str,                # canonical Sources.source value
    *,
    reference: str = None,
    obs_date: str = None,
    telescope: str = None,
    instrument: str = None,
    mode: str = None,
    regime: str = None,
)
```

Returns matching rows from `Spectra`. Call before `ingest_spectrum` to check for existing
duplicates — if a match is found, skip and log the reason rather than re-ingesting.

---

## ingest_spectrum signature

```python
from astrodb_utils.spectra import ingest_spectrum

ingest_spectrum(
    db,
    *,
    source: str = None,              # must already exist in Sources (use canonical name)
    spectrum: str = None,             # URL or local path — the file to ingest
    regime: str = None,               # must exist in RegimeList
    telescope: str = None,            # must exist in Telescopes
    instrument: str = None,           # must exist in Instruments
    mode: str = None,                 # paired with telescope+instrument in Instruments
    obs_date: str = None,             # ISO format preferred
    reference: str = None,            # must exist in Publications
    original_spectrum: str = None,    # raw/unprocessed version, if different from `spectrum`
    comments: str = None,
    other_references: str = None,
    local_spectrum: str = None,       # local file path, when different from `spectrum`
    raise_error: bool = True,         # False = warn and skip instead of raising
    format: str = None,               # specutils format string; None = auto-detect
)
```

Returns None. Side effect: inserts a row into `Spectra`.

**`spectrum` vs `local_spectrum`**: `spectrum` is the primary reference stored in the DB
(should be a stable, resolvable URL/permalink per the issue's requirement). `local_spectrum`
is only used when the user also has a local copy to record — it's optional and doesn't
replace the need for a real permalink.

---

## Common warnings and fixes

| Warning | Cause | Fix |
|---------|-------|-----|
| `Source X not found in Sources table` | Source not ingested yet, or name mismatch | Run `astrodb-ingest-sources` first, or resolve via `Names.other_name` (see SKILL.md Step 2) |
| `Reference X missing or not in Publications` | Reference not ingested | Run `ingest_publication` first |
| `Instrument/telescope/mode combination not found` | Missing from `Instruments` | Run `ingest_instrument` first |
| `Regime X not found in RegimeList` | Typo or unlisted regime | Check `RegimeList` table for valid values; fix casing |
| `Spectrum could not be read / not plottable` | Bad URL, wrong format, corrupt file | Run `check_spectrum_plottable` with `show_plot=True` interactively to debug; check `format=` param |
| `Duplicate spectrum found` (via `find_spectra`) | Same source+reference+regime+obs_date already ingested | Skip, or confirm with the user this is an intentional re-ingest |
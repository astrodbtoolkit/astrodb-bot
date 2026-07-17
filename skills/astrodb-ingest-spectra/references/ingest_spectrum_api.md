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

Returns `True`/`False` (when `raise_error=False`) or raises on failure. **Always call this
yourself, wrapped, before `ingest_spectrum`** — `ingest_spectrum` calls it internally but does
not pass through its own `raise_error` setting, so a bad URL will raise uncaught even when you
called `ingest_spectrum(..., raise_error=False)`.

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
    raise_error: bool = True,         # False = return a flags dict instead of raising
    format: str = None,               # specutils format string; None = auto-detect
)
```

Returns a `flags` dict: `{"added": bool, "content": dict, "message": str}`. `added` is `True`
if the row was inserted; when `False`, `message` explains why. When `raise_error=True` (the
default), the same failures raise `AstroDBError` instead.

**`ingest_spectrum` already validates and checks for duplicates internally** — it resolves
the source, confirms the reference exists in `Publications`, validates the regime and the
telescope/instrument/mode combo, parses `obs_date`, and runs its own duplicate check against
all five `Spectra` primary-key columns (`source`, `regime`, `mode`, `obs_date`, `reference`)
before inserting. **Don't call `find_spectra` yourself as a separate pre-check for duplicates**
— call `ingest_spectrum(..., raise_error=False)` directly and read `flags["message"]` to see
whether it skipped because of a duplicate, a missing reference, an unresolved source, etc.

**`spectrum` vs `local_spectrum`**: `spectrum` is the primary reference stored in the DB
(`access_url` column — should be a stable, resolvable URL/permalink per the issue's requirement).
`local_spectrum` is only used when the user also has a local copy to record — it's optional and
doesn't replace the need for a real permalink.

---

## find_spectra signature (for reference — not called directly in this skill's normal flow)

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

Returns matching rows from `Spectra`. `ingest_spectrum` calls this internally to check for
duplicates before inserting — you generally don't need to call it yourself in an ingest script.
It's still useful interactively (e.g. to inspect what's already in the database for a source
before deciding how to handle an edge case), just not as a required pre-check step.

---

## Common warnings and fixes

| Warning | Cause | Fix |
|---------|-------|-----|
| `Source X not found in Sources table` / no unique match | Source not ingested yet, or name mismatch | Run `astrodb-ingest-sources` first, or resolve via `Names.other_name` (see SKILL.md Step 2) |
| `Reference not found in database` | Reference not ingested | Run `ingest_publication` first |
| Instrument/telescope/mode combination not found | Missing from `Instruments` | Run `ingest_instrument` first |
| `Regime not found in database` | Typo or unlisted regime | Check `RegimeList` table for valid values; fix casing |
| `Observation date is not valid` | Missing or unparseable `obs_date` | Skip the row — `observation_date` is part of the PK and can't be null or guessed |
| Spectrum could not be read / not plottable | Bad URL, wrong format, corrupt file | Your own `check_spectrum_plottable` pre-check (see above) should catch this before `ingest_spectrum` is even called |
| `Skipping suspected duplicate measurement` | Same source+regime+mode+obs_date+reference already in `Spectra` | Reported via `flags["message"]` automatically — no separate check needed |
| Integrity Error (e.g. value too long for column) | A field exceeds its schema length cap | Reported via `flags["message"]` when `raise_error=False`; trim/fix the value |
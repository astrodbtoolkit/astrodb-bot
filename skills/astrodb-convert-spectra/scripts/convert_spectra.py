"""
REFERENCE TEMPLATE -- read this to understand the conversion pattern.

Do NOT copy this file verbatim into a real run. Write a tailored script to
astrodb-convert-artifacts/convert_{REF}_spectra.py that:
  * keeps ONLY the loaders for layouts actually found by scripts/inspect_spectrum.py (Step 2),
  * uses the units the user confirmed in Step 3 (never guessed),
  * uses the metadata table / values the user confirmed in Step 4.

The CONFIG block below is filled with the eval fixture values (evals/data/) so this
template is runnable as a self-test:  python scripts/convert_spectra.py
"""
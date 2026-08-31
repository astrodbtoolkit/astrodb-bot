# Photometry Filter IDs

Whenever a column is mapped to `Photometry.magnitude`, the corresponding `PhotometryFilters.band`
value **must** be an SVO Filter Profile Service filter ID, not a bare band letter.

SVO filter IDs follow the format `Facility/Instrument.Band`, for example:
- `2MASS/2MASS.J`, `2MASS/2MASS.H`, `2MASS/2MASS.Ks`
- `WISE/WISE.W1`, `WISE/WISE.W2`, `WISE/WISE.W3`, `WISE/WISE.W4`
- `SDSS/SDSS.u`, `SDSS/SDSS.g`, `SDSS/SDSS.r`, `SDSS/SDSS.i`, `SDSS/SDSS.z`
- `Gaia/Gaia3.G`, `Gaia/Gaia3.Gbp`, `Gaia/Gaia3.Grp`
- `HST/ACS_WFC.F814W`, etc.

To resolve an ambiguous band name, fetch the filter list from:
https://svo2.cab.inta-csic.es/theory/fps3/index.php?mode=browse

Or search directly:
https://svo2.cab.inta-csic.es/theory/fps3/index.php?mode=search

Always prefer the most specific, instrument-resolved ID. If the source catalog does not specify
the instrument or telescope, flag the band in the PhotometryFilters checklist with a note that
the exact SVO ID needs to be confirmed by the user.

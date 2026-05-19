# Column Information: drpall-v3_1_1.fits

**File:** `drpall-v3_1_1.fits`
**Format:** fits
**Reader:** astropy
**Rows:** 11273
**Columns:** 99


| Column | Description | Units | Type |
|--------|-------------|-------|------|
| plate | Plate number | — | int64 |
| ifudsgn | IFU design ID | — | str |
| plateifu | Plate-IFU identifier (PLATE-IFUDSGN) | — | str |
| mangaid | MaNGA ID (CatalogID-LineNumber) | — | str |
| versdrp2 | DRP version 2 | — | str |
| versdrp3 | DRP version 3 | — | str |
| verscore | Core version | — | str |
| versutil | Utility version | — | str |
| versprim | Primary version | — | str |
| platetyp | Plate type | — | str |
| srvymode | Survey mode | — | str |
| objra | Object right ascension | deg | float64 |
| objdec | Object declination | deg | float64 |
| ifuglon | IFU Galactic longitude | deg | float64 |
| ifuglat | IFU Galactic latitude | deg | float64 |
| ifura | IFU right ascension | deg | float64 |
| ifudec | IFU declination | deg | float64 |
| ebvgal | Galactic E(B-V) reddening | mag | float64 |
| nexp | Number of exposures | — | int64 |
| exptime | Total exposure time | s | float64 |
| drp3qual | DRP3 quality flag | — | int64 |
| bluesn2 | Blue channel S/N squared | — | float64 |
| redsn2 | Red channel S/N squared | — | float64 |
| harname | Hardware name | — | str |
| frlplug | Fiber plug | — | int64 |
| cartid | Cart ID | — | str |
| designid | Design ID | — | int64 |
| cenra | Central right ascension | deg | float64 |
| cendec | Central declination | deg | float64 |
| airmsmin | Minimum airmass | — | float64 |
| airmsmed | Median airmass | — | float64 |
| airmsmax | Maximum airmass | — | float64 |
| seemin | Minimum seeing | arcsec | float64 |
| seemed | Median seeing | arcsec | float64 |
| seemax | Maximum seeing | arcsec | float64 |
| transmin | Minimum transparency | — | float64 |
| transmed | Median transparency | — | float64 |
| transmax | Maximum transparency | — | float64 |
| mjdmin | Minimum MJD | — | int64 |
| mjdmed | Median MJD | — | int64 |
| mjdmax | Maximum MJD | — | int64 |
| gfwhm | g-band FWHM | arcsec | float64 |
| rfwhm | r-band FWHM | arcsec | float64 |
| ifwhm | i-band FWHM | arcsec | float64 |
| zfwhm | z-band FWHM | arcsec | float64 |
| mngtarg1 | MaNGA target bitmask 1 (main sample) | — | int64 |
| mngtarg2 | MaNGA target bitmask 2 (non-galaxy) | — | int64 |
| mngtarg3 | MaNGA target bitmask 3 (ancillary) | — | int64 |
| catidnum | Catalog ID number | — | int64 |
| plttarg | Plate target | — | str |
| manga_tileid | MaNGA tile ID | — | int64 |
| nsa_iauname | NSA IAU name | — | str |
| ifudesignsize | IFU design size | — | int64 |
| ifutargetsize | IFU target size | — | int64 |
| ifudesignwrongsize | IFU design wrong size flag | — | int64 |
| z | Redshift | dimensionless_unscaled | float64 |
| zmin | Redshift minimum | dimensionless_unscaled | float64 |
| zmax | Redshift maximum | dimensionless_unscaled | float64 |
| szmin | Stellar redshift minimum | dimensionless_unscaled | float64 |
| szmax | Stellar redshift maximum | dimensionless_unscaled | float64 |
| ezmin | Emission redshift minimum | dimensionless_unscaled | float64 |
| ezmax | Emission redshift maximum | dimensionless_unscaled | float64 |
| probs | Probability | — | float64 |
| pweight | Primary weight | — | float64 |
| psweight | Primary-secondary weight | — | float64 |
| psrweight | Primary-secondary ratio weight | — | float64 |
| sweight | Secondary weight | — | float64 |
| srweight | Secondary ratio weight | — | float64 |
| eweight | Enhanced weight | — | float64 |
| esweight | Enhanced secondary weight | — | float64 |
| esrweight | Enhanced secondary ratio weight | — | float64 |
| nsa_field | NSA field | — | int64 |
| nsa_run | NSA run | — | int64 |
| nsa_camcol | NSA camcol | — | int64 |
| nsa_version | NSA version | — | str |
| nsa_nsaid | NSA ID | — | int64 |
| nsa_nsaid_v1b | NSA ID v1b | — | int64 |
| nsa_z | NSA redshift | dimensionless_unscaled | float64 |
| nsa_zdist | NSA redshift distance | Mpc | float64 |
| nsa_sersic_absmag | NSA Sérsic absolute magnitude | mag | float64 |
| nsa_elpetro_absmag | NSA elliptical Petrosian absolute magnitude | mag | float64 |
| nsa_elpetro_amivar | NSA elliptical Petrosian magnitude inverse variance | mag^-2 | float64 |
| nsa_sersic_mass | NSA Sérsic stellar mass | solMass | float64 |
| nsa_elpetro_mass | NSA elliptical Petrosian stellar mass | solMass | float64 |
| nsa_elpetro_ba | NSA elliptical Petrosian axis ratio b/a | dimensionless_unscaled | float64 |
| nsa_elpetro_phi | NSA elliptical Petrosian position angle | deg | float64 |
| nsa_extinction | NSA extinction | mag | float64 |
| nsa_elpetro_th50_r | NSA elliptical Petrosian 50% light radius (r-band) | arcsec | float64 |
| nsa_petro_th50 | NSA Petrosian 50% light radius | arcsec | float64 |
| nsa_petro_flux | NSA Petrosian flux | — | float64 |
| nsa_petro_flux_ivar | NSA Petrosian flux inverse variance | — | float64 |
| nsa_elpetro_flux | NSA elliptical Petrosian flux | — | float64 |
| nsa_elpetro_flux_ivar | NSA elliptical Petrosian flux inverse variance | — | float64 |
| nsa_sersic_ba | NSA Sérsic axis ratio b/a | dimensionless_unscaled | float64 |
| nsa_sersic_n | NSA Sérsic index | dimensionless_unscaled | float64 |
| nsa_sersic_phi | NSA Sérsic position angle | deg | float64 |
| nsa_sersic_th50 | NSA Sérsic 50% light radius | arcsec | float64 |
| nsa_sersic_flux | NSA Sérsic flux | — | float64 |
| nsa_sersic_flux_ivar | NSA Sérsic flux inverse variance | — | float64 |
## Notes

- FITS BINTABLE has no TCOMMn/TUNITn header keywords; descriptions and units inferred from SDSS/MaNGA drpall conventions.
- RA/Dec columns (objra, objdec, ifura, ifudec, cenra, cendec) in decimal degrees.
- Redshift columns (z, nsa_z, zmin, zmax, etc.) dimensionless.
- NSA mass columns in solar masses; magnitude columns in mag.
- See [SDSS drpall tutorial](https://www.sdss4.org/dr16/manga/manga-tutorials/drpall/) for usage.

# Schema Match: drpall-v3_1_1.fits → AstroDB

**Source:** `drpall-v3_1_1.fits` · 2025-03-17

| Column | Description | Units | Type | AstroDB Table | AstroDB Field | Confidence | Notes |
|--------|-------------|-------|------|---------------|---------------|------------|-------|
| plate | Plate number | — | int64 | — | — | Unmatched | Survey metadata; use for filtering or store in comments |
| ifudsgn | IFU design ID | — | str | — | — | Unmatched | Survey metadata |
| plateifu | Plate-IFU identifier (PLATE-IFUDSGN) | — | str | Names | other_name | High | Alternate identifier |
| mangaid | MaNGA ID (CatalogID-LineNumber) | — | str | Sources | source | High | Primary identifier |
| versdrp2 | DRP version 2 | — | str | — | — | Unmatched | Version metadata |
| versdrp3 | DRP version 3 | — | str | — | — | Unmatched | Version metadata |
| verscore | Core version | — | str | — | — | Unmatched | Version metadata |
| versutil | Utility version | — | str | — | — | Unmatched | Version metadata |
| versprim | Primary version | — | str | — | — | Unmatched | Version metadata |
| platetyp | Plate type | — | str | — | — | Unmatched | Survey metadata |
| srvymode | Survey mode | — | str | — | — | Unmatched | Survey metadata |
| objra | Object right ascension | deg | float64 | Sources | ra_deg | High | RA in decimal degrees |
| objdec | Object declination | deg | float64 | Sources | dec_deg | High | Dec in decimal degrees |
| ifuglon | IFU Galactic longitude | deg | float64 | — | — | Unmatched | No AstroDB Galactic coord field |
| ifuglat | IFU Galactic latitude | deg | float64 | — | — | Unmatched | No AstroDB Galactic coord field |
| ifura | IFU right ascension | deg | float64 | Positions | ra_deg | Medium | IFU center position; needs Positions row |
| ifudec | IFU declination | deg | float64 | Positions | dec_deg | Medium | IFU center position |
| ebvgal | Galactic E(B-V) reddening | mag | float64 | ModeledParameters | value | Medium | parameter=ebv_galactic, unit=mag |
| nexp | Number of exposures | — | int64 | — | — | Unmatched | Observation metadata |
| exptime | Total exposure time | s | float64 | — | — | Unmatched | Observation metadata |
| drp3qual | DRP3 quality flag | — | int64 | — | — | Unmatched | Quality code; use for row filtering or skip |
| bluesn2 | Blue channel S/N squared | — | float64 | — | — | Unmatched | Observation metadata |
| redsn2 | Red channel S/N squared | — | float64 | — | — | Unmatched | Observation metadata |
| harname | Hardware name | — | str | — | — | Unmatched | Instrument metadata |
| frlplug | Fiber plug | — | int64 | — | — | Unmatched | Instrument metadata |
| cartid | Cart ID | — | str | — | — | Unmatched | Instrument metadata |
| designid | Design ID | — | int64 | — | — | Unmatched | Survey metadata |
| cenra | Central right ascension | deg | float64 | — | — | Unmatched | Redundant with objra/ifura; or use for Positions |
| cendec | Central declination | deg | float64 | — | — | Unmatched | Redundant with objdec/ifudec |
| airmsmin | Minimum airmass | — | float64 | — | — | Unmatched | Observation metadata |
| airmsmed | Median airmass | — | float64 | — | — | Unmatched | Observation metadata |
| airmsmax | Maximum airmass | — | float64 | — | — | Unmatched | Observation metadata |
| seemin | Minimum seeing | arcsec | float64 | — | — | Unmatched | Observation metadata |
| seemed | Median seeing | arcsec | float64 | — | — | Unmatched | Observation metadata |
| seemax | Maximum seeing | arcsec | float64 | — | — | Unmatched | Observation metadata |
| transmin | Minimum transparency | — | float64 | — | — | Unmatched | Observation metadata |
| transmed | Median transparency | — | float64 | — | — | Unmatched | Observation metadata |
| transmax | Maximum transparency | — | float64 | — | — | Unmatched | Observation metadata |
| mjdmin | Minimum MJD | — | int64 | — | — | Unmatched | Observation metadata |
| mjdmed | Median MJD | — | int64 | — | — | Unmatched | Observation metadata |
| mjdmax | Maximum MJD | — | int64 | — | — | Unmatched | Observation metadata |
| gfwhm | g-band FWHM | arcsec | float64 | — | — | Unmatched | Observation metadata |
| rfwhm | r-band FWHM | arcsec | float64 | — | — | Unmatched | Observation metadata |
| ifwhm | i-band FWHM | arcsec | float64 | — | — | Unmatched | Observation metadata |
| zfwhm | z-band FWHM | arcsec | float64 | — | — | Unmatched | Observation metadata |
| mngtarg1 | MaNGA target bitmask 1 (main sample) | — | int64 | — | — | Unmatched | Target selection; use for filtering |
| mngtarg2 | MaNGA target bitmask 2 (non-galaxy) | — | int64 | — | — | Unmatched | Target selection |
| mngtarg3 | MaNGA target bitmask 3 (ancillary) | — | int64 | — | — | Unmatched | Target selection |
| catidnum | Catalog ID number | — | int64 | — | — | Unmatched | Survey metadata |
| plttarg | Plate target | — | str | — | — | Unmatched | Survey metadata |
| manga_tileid | MaNGA tile ID | — | int64 | — | — | Unmatched | Survey metadata |
| nsa_iauname | NSA IAU name | — | str | Names | other_name | High | IAU designation |
| ifudesignsize | IFU design size | — | int64 | — | — | Unmatched | Instrument metadata |
| ifutargetsize | IFU target size | — | int64 | — | — | Unmatched | Instrument metadata |
| ifudesignwrongsize | IFU design wrong size flag | — | int64 | — | — | Unmatched | Quality flag |
| z | Redshift | dimensionless_unscaled | float64 | RadialVelocities | rv_kms | High | Convert: z × 299792.458 km/s |
| zmin | Redshift minimum | dimensionless_unscaled | float64 | — | — | Unmatched | Redshift range; ModeledParameters if needed |
| zmax | Redshift maximum | dimensionless_unscaled | float64 | — | — | Unmatched | Redshift range |
| szmin | Stellar redshift minimum | dimensionless_unscaled | float64 | — | — | Unmatched | Redshift range |
| szmax | Stellar redshift maximum | dimensionless_unscaled | float64 | — | — | Unmatched | Redshift range |
| ezmin | Emission redshift minimum | dimensionless_unscaled | float64 | — | — | Unmatched | Redshift range |
| ezmax | Emission redshift maximum | dimensionless_unscaled | float64 | — | — | Unmatched | Redshift range |
| probs | Probability | — | float64 | — | — | Unmatched | Survey weight |
| pweight | Primary weight | — | float64 | — | — | Unmatched | Survey weight |
| psweight | Primary-secondary weight | — | float64 | — | — | Unmatched | Survey weight |
| psrweight | Primary-secondary ratio weight | — | float64 | — | — | Unmatched | Survey weight |
| sweight | Secondary weight | — | float64 | — | — | Unmatched | Survey weight |
| srweight | Secondary ratio weight | — | float64 | — | — | Unmatched | Survey weight |
| eweight | Enhanced weight | — | float64 | — | — | Unmatched | Survey weight |
| esweight | Enhanced secondary weight | — | float64 | — | — | Unmatched | Survey weight |
| esrweight | Enhanced secondary ratio weight | — | float64 | — | — | Unmatched | Survey weight |
| nsa_field | NSA field | — | int64 | — | — | Unmatched | NSA catalog metadata |
| nsa_run | NSA run | — | int64 | — | — | Unmatched | NSA catalog metadata |
| nsa_camcol | NSA camcol | — | int64 | — | — | Unmatched | NSA catalog metadata |
| nsa_version | NSA version | — | str | — | — | Unmatched | NSA catalog metadata |
| nsa_nsaid | NSA ID | — | int64 | — | — | Unmatched | Could be Names.other_name if desired |
| nsa_nsaid_v1b | NSA ID v1b | — | int64 | — | — | Unmatched | NSA catalog metadata |
| nsa_z | NSA redshift | dimensionless_unscaled | float64 | RadialVelocities | rv_kms | Medium | Alternative to z; convert same way |
| nsa_zdist | NSA redshift distance | Mpc | float64 | ModeledParameters | value | Medium | parameter=redshift_distance, unit=Mpc |
| nsa_sersic_absmag | NSA Sérsic absolute magnitude | mag | float64 | — | — | Unmatched | Absolute mag; Photometry stores apparent only. Use ModeledParameters or skip |
| nsa_elpetro_absmag | NSA elliptical Petrosian absolute magnitude | mag | float64 | — | — | Unmatched | Absolute mag; same as above |
| nsa_elpetro_amivar | NSA elliptical Petrosian magnitude inverse variance | mag^-2 | float64 | — | — | Unmatched | Inverse variance, not direct photometry |
| nsa_sersic_mass | NSA Sérsic stellar mass | solMass | float64 | ModeledParameters | value | High | parameter=stellar_mass_sersic, unit=M☉ |
| nsa_elpetro_mass | NSA elliptical Petrosian stellar mass | solMass | float64 | ModeledParameters | value | High | parameter=stellar_mass_elpetro, unit=M☉ |
| nsa_elpetro_ba | NSA elliptical Petrosian axis ratio b/a | dimensionless_unscaled | float64 | Morphology | ellipticity | Medium | ellipticity = 1 − b/a |
| nsa_elpetro_phi | NSA elliptical Petrosian position angle | deg | float64 | Morphology | position_angle_deg | High | PA in degrees |
| nsa_extinction | NSA extinction | mag | float64 | ModeledParameters | value | Medium | parameter=extinction, unit=mag |
| nsa_elpetro_th50_r | NSA elliptical Petrosian 50% light radius (r-band) | arcsec | float64 | Morphology | half_light_radius_arcmin | High | Convert arcsec → arcmin (÷60) |
| nsa_petro_th50 | NSA Petrosian 50% light radius | arcsec | float64 | Morphology | half_light_radius_arcmin | Medium | Same conversion; may duplicate th50_r |
| nsa_petro_flux | NSA Petrosian flux | — | float64 | — | — | Unmatched | Petrosian flux; not apparent mag. ModeledParameters or skip |
| nsa_petro_flux_ivar | NSA Petrosian flux inverse variance | — | float64 | — | — | Unmatched | Flux uncertainty |
| nsa_elpetro_flux | NSA elliptical Petrosian flux | — | float64 | — | — | Unmatched | Petrosian flux |
| nsa_elpetro_flux_ivar | NSA elliptical Petrosian flux inverse variance | — | float64 | — | — | Unmatched | Flux uncertainty |
| nsa_sersic_ba | NSA Sérsic axis ratio b/a | dimensionless_unscaled | float64 | Morphology | ellipticity | Medium | ellipticity = 1 − b/a; may duplicate elpetro_ba |
| nsa_sersic_n | NSA Sérsic index | dimensionless_unscaled | float64 | ModeledParameters | value | High | parameter=sersic_index, unit=dimensionless |
| nsa_sersic_phi | NSA Sérsic position angle | deg | float64 | Morphology | position_angle_deg | Medium | May duplicate elpetro_phi |
| nsa_sersic_th50 | NSA Sérsic 50% light radius | arcsec | float64 | Morphology | half_light_radius_arcmin | High | Convert arcsec → arcmin (÷60) |
| nsa_sersic_flux | NSA Sérsic flux | — | float64 | — | — | Unmatched | Sérsic flux |
| nsa_sersic_flux_ivar | NSA Sérsic flux inverse variance | — | float64 | — | — | Unmatched | Flux uncertainty |

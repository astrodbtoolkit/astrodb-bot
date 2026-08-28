# AstroDB Template Schema

The schema follows the [Felis](https://felis.lsst.io) format.
Full source: https://github.com/astrodbtoolkit/astrodb-template-db/blob/main/schema.yaml
Documentation: https://astrodb-utils.readthedocs.io/en/stable/pages/template_schema/template_schema.html

## Lookup Tables

| Table | Fields |
|---|---|
| Publications | reference, bibcode, doi, description |
| Telescopes | telescope, description, reference |
| Instruments | instrument, mode, telescope, description, reference |
| PhotometryFilters | band, ucd, effective_wavelength_angstroms, width_angstroms |
| Versions | version, start_date, end_date, description |
| RegimeList | regime, description |
| AssociationList | association, association_type, comments, reference |
| ParameterList | parameter, description |
| CompanionList | companion, description |
| SourceTypeList | source_type, comments |

## Main Tables

| Table | Fields |
|---|---|
| Sources | source, ra_deg, dec_deg, epoch_year, equinox, reference, other_references, comments |
| Names | source, other_name |
| Positions | source, ra_deg, dec_deg, epoch_year, reference |

## Data Tables

| Table | Fields |
|---|---|
| Photometry | source, band, magnitude, magnitude_error, magnitude_error_upper, magnitude_error_lower, telescope, epoch, comments, reference, regime |
| Parallaxes | source, parallax_mas, parallax_error, parallax_error_upper, parallax_error_lower, adopted, comments, reference |
| RadialVelocities | source, rv_kms, rv_error, rv_error_upper, rv_error_lower, adopted, comments, reference |
| ProperMotions | source, pm_ra, pm_ra_error, pm_ra_error_upper, pm_ra_error_lower, pm_dec, pm_dec_error, pm_dec_error_upper, pm_dec_error_lower, adopted, comments, reference |
| RotationalParameters | source, period_hr, period_error, period_error_upper, period_error_lower, v_sin_i_kms, v_sin_i_error, v_sin_i_error_upper, v_sin_i_error_lower, inclination, inclination_error, inclination_error_upper, inclination_error_lower, adopted, comments, reference |
| Morphology | source, position_angle_deg, position_angle_error, position_angle_error_upper, position_angle_error_lower, ellipticity, ellipticity_error, ellipticity_error_upper, ellipticity_error_lower, half_light_radius_arcmin, half_light_radius_error, half_light_radius_error_upper, half_light_radius_error_lower, adopted, comments, reference |
| Spectra | source, access_url, original_spectrum, local_spectrum, regime, telescope, instrument, mode, observation_date, comments, reference, other_references |
| CompanionRelationships | source, companion, relationship, projected_separation_arcsec, projected_separation_error, projected_separation_error_upper, projected_separation_error_lower, comments, reference, other_companion_names |
| CompanionParameters | source, companion, parameter, value, error, error_upper, error_lower, unit, comments, reference |
| Associations | source, association, membership_probability, comments, adopted, reference |
| SourceTypes | source, source_type, comments, adopted, reference |
| ModeledParameters | source, model, parameter, value, error, error_upper, error_lower, unit, comments, reference |

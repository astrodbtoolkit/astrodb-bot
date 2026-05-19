## Schema Mapping Validation Report
Source: `drpall-v3_1_1.fits` → `sdss/manga-schema.yaml`
Date: 2025-03-17

### Nullable Violations (0 issues)
No nullable violations found.

### Type Mismatches (0 issues)
No type mismatches found.

### Clean Mappings (22 columns OK)
- plateifu → Names.other_name
- mangaid → Sources.source
- objra → Sources.ra_deg
- objdec → Sources.dec_deg
- ifura → Positions.ra_deg
- ifudec → Positions.dec_deg
- ebvgal → ModeledParameters.value
- z → RadialVelocities.rv_kms
- nsa_z → RadialVelocities.rv_kms
- nsa_zdist → ModeledParameters.value
- nsa_sersic_mass → ModeledParameters.value
- nsa_elpetro_mass → ModeledParameters.value
- nsa_elpetro_ba → Morphology.ellipticity
- nsa_elpetro_phi → Morphology.position_angle_deg
- nsa_extinction → ModeledParameters.value
- nsa_elpetro_th50_r → Morphology.half_light_radius_arcmin
- nsa_petro_th50 → Morphology.half_light_radius_arcmin
- nsa_sersic_ba → Morphology.ellipticity
- nsa_sersic_n → ModeledParameters.value
- nsa_sersic_phi → Morphology.position_angle_deg
- nsa_sersic_th50 → Morphology.half_light_radius_arcmin
- nsa_iauname → Names.other_name

### Summary
- 0 nullable violations found (columns with nulls in non-nullable fields)
- 0 type mismatches found
- 22 columns passed validation cleanly

**All 22 mapped columns passed validation.**

The data is compatible with the schema for direct ingestion. Remember:
- **RadialVelocities.rv_kms**: Convert redshift `z` (or `nsa_z`) to km/s: `z × 299792.458`
- **Morphology.half_light_radius_arcmin**: Convert arcsec → arcmin (÷60) for `nsa_elpetro_th50_r`, `nsa_petro_th50`, `nsa_sersic_th50`
- **Morphology.ellipticity**: Convert b/a → ellipticity: `1 − b/a` for `nsa_elpetro_ba`, `nsa_sersic_ba`
- **ModeledParameters**: Each parameter needs its own row with `parameter`, `model`, `unit`, and `reference` filled from the mapping notes.

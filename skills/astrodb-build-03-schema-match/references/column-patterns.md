# Column Name Matching Patterns

## Guiding principle: `Sources` is deliberately minimal — never a catch-all

The `Sources` table holds **only** these fields: `source`, `ra_deg`, `dec_deg`, `epoch_year`,
`equinox`, `reference`, `other_references`, `comments`. That is the entire table. It is a thin
identity-and-position record, **not** a landing spot for leftover columns. Before you map anything
to `Sources`, confirm it is genuinely one of those eight fields.

Concretely, this means:
- **Alternate names, shortnames, and survey/catalog designations do not go in `Sources`** — they go
  in `Names.other_name` (see Identifiers below). Only the single canonical identifier becomes
  `Sources.source`.
- **Measured quantities never go in `Sources`** — proper motions → `ProperMotions`, radial
  velocities → `RadialVelocities`, parallaxes → `Parallaxes`, photometry → `Photometry`, etc. If a
  value has its own table, it belongs there, not in `Sources`.
- **Miscellaneous / bookkeeping columns do not get dumped into `Sources.comments`.** Genuinely
  leftover columns fall through to **Unmatched** and are routed to a proposed **`Misc`** table or
  ignored — see "Columns that typically end up Unmatched" below. Do not use `Sources.comments` as a
  default drawer for URLs, flags, or survey metadata.

When in doubt, a column does **not** belong in `Sources`.

## Layer 1: Column name patterns (strongest signal)

**Identifiers:**
- Exactly **one** column becomes the canonical `Sources.source` primary identifier. Candidates:
  `source`, `name`, `id`, `designation`, `target`, `obj`, `object`.
- **Every other name-like column → `Names.other_name` (High confidence), not `Sources`.** This
  includes survey/catalog shortnames and secondary designations such as `shortname`,
  `gucds_shortname`, `alt_name`, `alternate_name`, `2MASS`, `2MASS_name`, `WISEA`, `SDSS_name`,
  `Gaia_designation`, `common_name`, `other_id`, `catalog_id`, and the like. A column being a name
  is a strong, High-confidence signal for `Names.other_name` — do not park these in `Sources`.
- If the table has multiple name-like columns and it's not obvious which is the canonical primary
  identifier (e.g., `Number`, `Name`, and `Designation` all present), **ask the user** which
  column should become `Sources.source`. List the candidates with a brief description of each and
  wait for their choice before finalizing the mapping. Map the rest to `Names.other_name`.

**Coordinates:**
- `ra`, `ra_deg`, `RA`, `Right_Ascension`, `RAJ2000` → `Sources.ra_deg`
- `dec`, `dec_deg`, `Dec`, `Declination`, `DEJ2000` → `Sources.dec_deg`
- `epoch`, `epoch_year` (standalone, not with a measurement) → `Sources.epoch_year`

**Parallax:**
- `parallax`, `plx`, `parallax_mas`, `pi` → `Parallaxes.parallax_mas`
- `parallax_error`, `e_plx`, `plx_err`, `sigma_plx`, `eplx`, `e_Plx` → `Parallaxes.parallax_error`

**Proper motion:**
- `pm_ra`, `pmra`, `mu_ra`, `mu_alpha`, `pmRA` → `ProperMotions.pm_ra`
- `pm_dec`, `pmdec`, `mu_dec`, `mu_delta`, `pmDE` → `ProperMotions.pm_dec`
- Corresponding `_error`, `_err`, `e_` prefix variants → the matching `_error` field

**Radial velocity:**
- `rv`, `RV`, `radial_velocity`, `vrad`, `HRV`, `cz` → `RadialVelocities.rv_kms`
- Corresponding error variants → `RadialVelocities.rv_error`

**Photometry — single-band columns:**
Column names that *are* a band name (case-insensitive), or end/start with a band name:
- Standard band names: `u`, `g`, `r`, `i`, `z`, `y`, `J`, `H`, `K`, `Ks`, `W1`, `W2`, `W3`, `W4`, `G`, `BP`, `RP`, `NUV`, `FUV`, `B`, `V`, `R`, `I`, `L`, `M`, `N`, `Q`
- e.g. `Jmag`, `J_mag`, `Hmag`, `W1mag`, `G_mag`, `gmag`, `rmag` → `Photometry.magnitude`
- Corresponding errors (`eJmag`, `J_err`, `e_Jmag`, `Jmag_err`, `eW1`, etc.) → `Photometry.magnitude_error`
- If there are asymmetric upper/lower error columns, map them to `magnitude_error_upper` / `magnitude_error_lower`

**Photometry band → SVO filter ID:**
The `band` value stored in `PhotometryFilters` must be an SVO Filter Profile Service ID
(`Facility/Instrument.Band`). Map common band names as follows:

| Bare band name | SVO filter ID |
|---|---|
| J (2MASS) | `2MASS/2MASS.J` |
| H (2MASS) | `2MASS/2MASS.H` |
| K / Ks (2MASS) | `2MASS/2MASS.Ks` |
| W1 | `WISE/WISE.W1` |
| W2 | `WISE/WISE.W2` |
| W3 | `WISE/WISE.W3` |
| W4 | `WISE/WISE.W4` |
| u (SDSS) | `SDSS/SDSS.u` |
| g (SDSS) | `SDSS/SDSS.g` |
| r (SDSS) | `SDSS/SDSS.r` |
| i (SDSS) | `SDSS/SDSS.i` |
| z (SDSS) | `SDSS/SDSS.z` |
| G (Gaia DR3) | `Gaia/Gaia3.G` |
| BP (Gaia DR3) | `Gaia/Gaia3.Gbp` |
| RP (Gaia DR3) | `Gaia/Gaia3.Grp` |
| B (Johnson) | `Generic/Johnson.B` |
| V (Johnson) | `Generic/Johnson.V` |
| R (Cousins) | `Generic/Cousins.R` |
| I (Cousins) | `Generic/Cousins.I` |

For any band not in this table, search https://svo2.cab.inta-csic.es/theory/fps3/ to find the
correct ID. If the telescope or instrument is ambiguous, flag the band in the output and ask the
user to confirm the SVO ID.

**Rotational parameters:**
- `period`, `rot_period`, `Prot`, `P_rot`, `rotation_period` → `RotationalParameters.period_hr` (note: units matter — convert to hours if in days)
- `vsini`, `v_sin_i`, `vrot`, `vsini_kms` → `RotationalParameters.v_sin_i_kms`
- `inclination`, `incl`, `i_rot` → `RotationalParameters.inclination`

**Morphology:**
- `pa`, `position_angle`, `PA_deg` → `Morphology.position_angle_deg`
- `ellipticity`, `ellip`, `e=1-b/a`, `epsilon` → `Morphology.ellipticity`
- `half_light_radius`, `r_eff`, `r_h`, `Re` → `Morphology.half_light_radius_arcmin` (check units)

**Spectra:**
- `access_url`, `spectrum_url`, `url`, `fits_url` → `Spectra.access_url`
- `telescope`, `obs_telescope` → `Spectra.telescope` (or `Telescopes.telescope`)
- `instrument` → `Spectra.instrument`
- `obs_date`, `date_obs`, `observation_date` → `Spectra.observation_date`

**Classification:**
- `spectral_type`, `spt`, `SpT`, `sp_type`, `sp_type_adopted` → `SourceTypes.source_type`
- `association`, `moving_group`, `young_association`, `cluster` → `Associations.association`

Use the data to also populate the SourceTypeList and AssociationList tables with needed values.

**References:**
- `reference`, `ref`, `bibcode`, `citation` → `Publications.reference`

## Layer 2: Units (use when name is ambiguous)

| Units | Likely field |
|---|---|
| `mas` | `Parallaxes.parallax_mas` |
| `mas/yr` | `ProperMotions.pm_ra` or `pm_dec` |
| `km/s` | `RadialVelocities.rv_kms` or `RotationalParameters.v_sin_i_kms` |
| `mag` | `Photometry.magnitude` |
| `deg` + RA/Dec context | `Sources.ra_deg` / `Sources.dec_deg` |
| `hr` or `d` + periodic context | `RotationalParameters.period_hr` |
| `arcsec` + separation context | `CompanionRelationships.projected_separation_arcsec` |
| `arcmin` + size context | `Morphology.half_light_radius_arcmin` |

## Layer 3: Description text (use as tiebreaker or when name+units both unclear)

Scan description for key words:
- "magnitude", "flux", "photometry" → `Photometry`
- "parallax", "distance" → `Parallaxes`
- "radial velocity", "line-of-sight velocity" → `RadialVelocities`
- "proper motion", "sky-plane motion" → `ProperMotions`
- "spectral type", "classification" → `SourceTypes`
- "rotation", "spin", "period" → `RotationalParameters`
- "separation", "companion", "binary" → `CompanionRelationships` or `CompanionParameters`
- "association", "membership", "moving group" → `Associations`

## Uncertainty columns

When you identify that a column is an uncertainty on a value you've already mapped:
- Single symmetric error → `<field>_error`
- Upper bound / `+` suffix / `_upper` / `_plus` → `<field>_error_upper`
- Lower bound / `-` suffix / `_lower` / `_minus` → `<field>_error_lower`

## The `adopted` flag is boolean-only — not a mapping target

Several data tables (`Parallaxes`, `RadialVelocities`, `ProperMotions`, `RotationalParameters`,
`Morphology`, `Associations`, `SourceTypes`) have an `adopted` field. It is a **boolean** that marks,
among several measurements of the same quantity for a source, which one is the preferred/adopted
value. It is set at ingestion time, not carried in from a data column.

- **Never map a continuous, string, or measurement column onto `adopted`.** A column of parallax
  values maps to `parallax_mas`, never to `adopted`; a spectral-type string maps to `source_type`,
  never to `adopted`.
- Only map an input column to `adopted` if that column is itself a genuine boolean/flag (0/1,
  True/False, "adopted"/"") indicating the preferred value — which is rare in source tables.

## Catch-all tables for unmapped physical parameters

If a column clearly represents a physical quantity but doesn't fit any specific table field:
- Fitted or modeled parameters (effective temperature `Teff`, luminosity `L`, mass `M`, radius `R`, surface gravity `logg`, metallicity `[Fe/H]`, age) → `ModeledParameters` (using the generic `value` + `unit` fields; put the parameter name in `parameter`)
- Companion-derived measurements → `CompanionParameters`

## The `Misc` table (proposed) — for genuine non-physical leftovers

For columns that are neither identity/position, nor a measured quantity with a home table, nor a
physical parameter (which goes to `ModeledParameters`) — e.g. survey bookkeeping, generic URLs,
quality flags, internal notes — **do not dump them into `Sources.comments`.** Instead, route them to
a dedicated **`Misc`** table.

`Misc` is **not** part of the current template schema, so it is always a **proposed new table**
(confidence `Proposed (new table)`), flowing through the "Add new table" path in SKILL.md and the
**Proposed Schema Additions** section of the HTML output. Its suggested minimal shape is a generic
key/value store:

| Field | Purpose |
|---|---|
| `source` | FK to `Sources.source` (which object the value belongs to) |
| `parameter` | the original column name / what the value is |
| `value` | the value itself (stored as text) |
| `comments` | optional note |
| `reference` | provenance, when known |

Do not work out Felis-level details (nullability, primary keys) here — `astrodb-build-schema-generate`
finalizes those from the proposal.

**Fallback ordering (so `Misc` doesn't cannibalize real homes).** Try these in order before
proposing `Misc`:
1. Identifiers / alternate names → `Names.other_name`
2. Physical / modeled parameters → `ModeledParameters` (or `CompanionParameters` for companion data)
3. Row numbers, internal indices, and other truly disposable columns → **Ignore**
4. Only genuine non-physical leftovers (URLs, survey flags, bookkeeping) → **`Misc`** (proposed)

## Columns that typically end up Unmatched

The following column types commonly fall through all three matching layers. When you reach the
**Resolving Unmatched Columns** step in SKILL.md, use the explanation and suggested options
below as the reason/suggestions for these columns in the combined prompt to the user — don't
ask about them separately. **None of these should default to `Sources.comments`** — `Sources` is
not a catch-all (see the guiding principle at the top of this file).

**Absolute magnitude columns** (`H`, `absolute_magnitude`, `abs_mag`, `M_V`, `M_B`, etc. when
clearly absolute and not apparent magnitude):
AstroDB's `Photometry.magnitude` stores *apparent* magnitudes only. Suggest adding a new field
in `ModeledParameters` (parameter="absolute_magnitude_<band>", unit="mag"), or ignoring it.

**Generic URL / link columns** (`url`, `link`, `webpage`, `nasa_link`, `href`, etc. that are not
clearly spectrum access URLs):
No direct AstroDB field. Suggest mapping to `Spectra.access_url` if the link points to a spectrum,
routing it to the proposed **`Misc`** table (default) if it's generic metadata, or ignoring it.

**Quality codes and observation flags** (`flag`, `flags`, `quality`, `qual`, `qflag`,
`quality_code`, `f_flag`, numeric quality scores, etc.):
No AstroDB field. Suggest using these for pre-ingestion row filtering (e.g. keep only
quality=1 rows) and ignoring them for the schema mapping, or — if the user wants to keep them —
routing them to the proposed **`Misc`** table.

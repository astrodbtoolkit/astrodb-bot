# Directions

Notes, decisions, and known issues for this database.

## Database

- **Name**: `StreamDB`
- **Description**: A catalog of stellar stream members with metallicities, orbital distances,
  and membership probabilities — for studying the accretion history of the Milky Way halo.

## License

- **License**: BSD 3-Clause (keep the template's)
- **Copyright holder(s)**: Jane Astronomer, 2026 — added alongside the template authors

## Data Overview

- Each row represents a single star
- `all_stream.fits` contains all membership data

## Column Handling

- `flag_internal` — internal bookkeeping, do not ingest
- `Feh` and `AFe`: ingest into `ModeledParameters` table

## Known Issues / Open Questions

- Distances in `dist_kpc` are heliocentric, not galactocentric
- `p_membership`: how to handle stars with only one membership is TBD

## Schema Notes

- Stream membership probabilities go in a custom `StreamMembership` table

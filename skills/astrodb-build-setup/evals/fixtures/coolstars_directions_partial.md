# Directions

Notes and decisions for this database.

## Database

- **Description**: A catalog of nearby M dwarfs with rotation periods and activity indices,
  assembled to study the rotation–activity relation across the fully convective boundary.

## Data Overview

- Each row is one star; one row per epoch where rotation was measured
- `prot_days` is the adopted rotation period; `prot_err` may be null for literature values

## Column Handling

- `notes_internal` — scratch column, do not ingest
- `Prot` and `Ro`: ingest into `RotationalParameters`

## Known Issues / Open Questions

- Some activity indices are upper limits; flag column is `is_limit`

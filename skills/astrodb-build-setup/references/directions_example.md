# Directions

Notes, decisions, and known issues for this database. Subsequent skills read this file
automatically — keep it up to date as new decisions are made.

## Database

Answers the questions `astrodb-build-setup` would otherwise have to ask. Fill in what you
know; anything you leave out, the skill will ask about instead.

- **Name**: `StreamDB` — becomes `db_name` in `database.toml` and names the SQLite file
- **Description**: A catalog of stellar stream members with metallicities, orbital
  distances, and membership probabilities — for studying the accretion history of the
  Milky Way halo. Used as the README and CLAUDE.md description.

## License

- **License**: BSD 3-Clause (keep the template's)
- **Copyright holder(s)**: Jane Astronomer, 2026 — added alongside the template authors

## Data Overview
- Each row represents a single star
- `all_stream.fits` contains all membership data

## Column Handling
- `Feh` and `AFe`: ingest into `ModeledParameters` table
- `d_orb`, `x`, `y`, `z`: put in `ModeledParameters` with this paper as the reference;
  55,397 distances — every star has `d_orb`
- Ingest bad parallaxes: yes; also keep distances alongside `d_orb` in `ModeledParameters`
- Ignore `d_orb`, `x`, `y`, `z` from the main source table — they go in `ModeledParameters`

## Source Matching
- Use our own Gaia match if `gaia_id` is present in the data
- Add epoch to `ra_index`; ingest epoch for our index and get `gaia_index`

## Membership / References
- Ingest each star twice if it has multiple memberships (once per reference)
- Start with unique members first, in a separate table
- Stream name goes in the `name` field; stream reference goes in the `Publications` table

## Schema Notes
- Schema is not fixed — attributes can be added later
- Define `alpha_fe` and `fe` using this data table for the initial schema
- If proper motion values change: add different proper motion values; a dedicated update
  skill is planned for this

## Known Issues / Open Questions
- `p_membership`: how to handle stars with only one membership is TBD
- Separate unique-members table: start there before ingesting all memberships

# AstroDB Bot

Agent Skills for interactive AstroDB ingestion workflows. Expects an input data table and will prepare it to be converted into a new database using the [AstroDB Template schema](https://github.com/astrodbtoolkit/astrodb-template-db) and conventions. It utilizes the [Felis system](https://felis.lsst.io/index.html) for describing database schemas. Also uses `astrodbkit` and `astrodb_utils` packages for setting up and interacting with the database.

To install this in another agent, you can copy the `skills/` directory to whatever is appropriate for your agent (eg, `.claude/skills/`, `.cursor/skills/`, `.agents/skills/`, etc).

## Skills

- [`astrodb-setup`](skills/astrodb-setup/SKILL.md) — Setup the local directory, making sure the user clones the astrodb template and names it properly.
- [`astrodb-parse-data-table`](skills/astrodb-parse-data-table/SKILL.md) — summarizes table columns, descriptions, units, and types.
- [`astrodb-match-schema`](skills/astrodb-match-schema/SKILL.md) — maps parsed columns to [AstroDB Template](https://github.com/astrodbtoolkit/astrodb-template-db) tables and fields
- [`astrodb-validate-schema-mapping`](skills/astrodb-validate-schema-mapping/SKILL.md) — identifies problems with nulls and inconsistent data types
- [`astrodb-generate-schema`](skills/astrodb-generate-schema/SKILL.md) — creates a Felis-format schema.yaml file using outputs of previous skills
- [`astrodb-create-db`](skills/astrodb-create-db/SKILL.md) — Create an empty SQLite AstroDB database from a Felis-validated schema.yaml, following the astrodb-template-db file structure.
- [`astrodb-website`](skills/astrodb-website/SKILL.md) — Sets up a FastAPI web interface ([astrodb-web](https://github.com/astrodbtoolkit/astrodb-web)) to browse and visualize an AstroDB SQLite database.
- [`astrodb-ingest-publication`](skills/astrodb-ingest-publication/SKILL.md) — ingests publications into the Publications table from a DOI/bibcode or a table of references, and backfills missing bibcode/DOI/description for existing references.


## Requirements

- an AI skill runner that reads `.agents/skills/` (or the appropriate directory for your agent)
- `uv` or `pip` to install Python packages
- Python 3.11+
  - `astropy`
  - `pandas` for fallback table parsing
  - `lsst-felis`
  - `astrodbkit`
  - `astrodb_utils`
  - `pytest`

## License

BSD 3-Clause. See [LICENSE](LICENSE).

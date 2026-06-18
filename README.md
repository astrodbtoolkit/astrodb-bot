# AstroDB Bot

Agent Skills for interactive AstroDB ingestion workflows. Expects an input data table and will prepare it to be converted into a new database using the [AstroDB Template schema](https://github.com/astrodbtoolkit/astrodb-template-db) and conventions. It utilizes the [Felis system](https://felis.lsst.io/index.html) for describing database schemas. Also uses `astrodbkit` and `astrodb_utils` packages for setting up and interacting with the database.

To install this in another agent, you can copy the `skills/` directory to whatever is appropriate for your agent (eg, `.claude/skills/`, `.cursor/skills/`, `.agents/skills/`, etc).

## Skills

### Build

- [`astrodb-build-setup`](skills/astrodb-build-setup/SKILL.md) — Set up the local directory, cloning the astrodb template and naming it properly.
- [`astrodb-build-parse-table`](skills/astrodb-build-parse-table/SKILL.md) — Summarize table columns, descriptions, units, and types.
- [`astrodb-build-schema-match`](skills/astrodb-build-schema-match/SKILL.md) — Map parsed columns to [AstroDB Template](https://github.com/astrodbtoolkit/astrodb-template-db) tables and fields.
- [`astrodb-build-schema-validate`](skills/astrodb-build-schema-validate/SKILL.md) — Identify problems with nulls and inconsistent data types.
- [`astrodb-build-schema-generate`](skills/astrodb-build-schema-generate/SKILL.md) — Create a Felis-format schema.yaml file using outputs of previous skills.
- [`astrodb-build-create-db`](skills/astrodb-build-create-db/SKILL.md) — Create an empty SQLite AstroDB database from a Felis-validated schema.yaml.

### Ingest

- [`astrodb-ingest-publications`](skills/astrodb-ingest-publications/SKILL.md) — Ingest publications into the Publications table from a DOI/bibcode or a table of references; backfills missing metadata for existing references.
- [`astrodb-ingest-sources`](skills/astrodb-ingest-sources/SKILL.md) — Ingest astronomical objects into the Sources table from a data file.

### Website

- [`astrodb-website`](skills/astrodb-website/SKILL.md) — Set up a FastAPI web interface ([astrodb-web](https://github.com/astrodbtoolkit/astrodb-web)) to browse and visualize an AstroDB SQLite database.


## Requirements

- an AI skill runner that reads `.agents/skills/` (or the appropriate directory for your agent)
- `uv` to install Python packages
- Python 3.13+
  - `astropy`
  - `pandas` for fallback table parsing
  - `lsst-felis`
  - `astrodbkit`
  - `astrodb_utils`
  - `pytest`

## Releases

Versioned releases are available on the [Releases page](../../releases). Use a tagged release when installing skills into a project so you can pin to a known-good version.

## License

BSD 3-Clause. See [LICENSE](LICENSE).

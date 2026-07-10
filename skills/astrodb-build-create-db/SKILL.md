---
name: astrodb-build-create-db
description: Create an empty SQLite AstroDB database from a Felis-validated schema.yaml, following the astrodb-template-db file structure. Use this skill whenever the user wants to create a database, initialize a SQLite database, build an AstroDB, or has just finished generating a Felis schema and wants to turn it into a working database. Always trigger after astrodb-build-schema-generate completes, or when the user says "create database", "make database", "initialize database", "create sqlite", "make sqlite", "build the database", "create astrodb", "initialize astrodb", or "set up the database". Do NOT skip this skill just because a schema.yaml already exists — this skill is exactly what handles that case.
compatibility: python, astrodbkit, felis
---

# Create AstroDB Database

Take a Felis-validated `schema.yaml` and create an empty SQLite database following the
[astrodb-template-db](https://github.com/astrodbtoolkit/astrodb-template-db) file structure,
using `astrodbkit`.

## Step 0: Read context documents

1. Read `references/astrodb-directions.md` for the workflow.md convention.
2. Check whether `workflow.md` exists in the current working directory. If it does, read it
   to carry forward context from prior skills.

## Prerequisites

This skill requires a schema.yaml that has **passed** `felis validate`. The astrodb-build-schema-generate
skill always runs this validation as its final step, so if the user just completed that workflow
the schema is already validated. If there is any doubt, validate before proceeding.

## Step 1: Locate the schema.yaml

Check (in order):
1. A path the user explicitly stated in the conversation
2. `astrodb-build-artifacts/<schema-name>-schema.yaml` — the default output of astrodb-build-schema-generate
3. `schema.yaml` in the current working directory

If you cannot find the file, ask the user for the path before continuing.

## Step 2: Confirm felis validation

Run `felis validate` on the schema to confirm it is valid. If the project has a `.venv/`:

```bash
.venv/bin/felis validate <schema-path>
# or
felis validate <schema-path>
```

**If validation fails:** show the error to the user and stop — do not create the database from
a broken schema. Offer to go back to astrodb-build-schema-generate to fix the issue.

**If validation passes:** proceed.

## Step 3: Read the schema name

The database name comes from the top-level `name:` field in the schema YAML. For example:

```yaml
name: MyDataset
"@id": "#MyDataset"
```

This yields `MyDataset.sqlite` as the database file name.

Use Python or shell to extract it:
```bash
python -c "import yaml; d=yaml.safe_load(open('<schema-path>')); print(d['name'])"
```

## Step 4: Determine the project root

The project root is the directory where the new database will live — typically the current working
directory (where the user's project is). Confirm this is correct; if the user wants it elsewhere,
use that path instead.

The final layout will follow astrodb-template-db:
```
<project-root>/
├── schema.yaml              ← copy of the validated schema
├── <db-name>.sqlite         ← the new empty database
├── database.toml            ← config file
├── data/
│   ├── reference/           ← lookup table JSON files (initially empty)
│   └── source/              ← source JSON files (initially empty)
└── tests/                   ← generated test suite (Step 8)
    ├── conftest.py
    ├── test_felis.py
    ├── test_contents.py
    ├── test_database.py
    └── test_contents_*.py
```

## Step 5: Create directory structure and config

Create the directories:
```bash
mkdir -p <project-root>/data/reference
mkdir -p <project-root>/data/source
```

Copy the schema.yaml to the project root (if it is not already there):
```bash
cp <schema-path> <project-root>/schema.yaml
```

Create `database.toml` if it does not already exist:

```toml
db_name = "<db-name>"
data_path = "data/"
felis_path = "schema.yaml"
lookup_tables = []
```

Do not overwrite an existing `database.toml`.

## Step 6: Create the empty SQLite database

Use the bundled script `scripts/create_db.py`. Run it with `uv run` so the project's virtualenv
is used:

```bash
uv run python <skill-dir>/scripts/create_db.py \
  --schema <project-root>/schema.yaml \
  --db-path <project-root>/<db-name>.sqlite
```

The script calls `astrodbkit.astrodb.create_database()` and prints success or an error traceback.

If `uv` is not available, try:
```bash
python <skill-dir>/scripts/create_db.py --schema ... --db-path ...
```

**If the script fails**, read the traceback carefully:
- `felis.datamodel` errors → schema is not valid Felis; offer to re-run astrodb-build-schema-generate
- `sqlite3` errors → check that the db path is writable
- `ImportError` for astrodbkit → astrodbkit is not installed; run `uv add astrodbkit`

## Step 7: Verify and report

After the script succeeds, confirm the database file exists and is non-empty:
```bash
ls -lh <project-root>/<db-name>.sqlite
```

## Step 8: Generate the test suite

Use the bundled script `scripts/generate_tests.py` to create a `tests/` directory
adapted for this database's schema. Run it from the project root so the generated
conftest.py correctly references the database file:

```bash
cd <project-root>
uv run python <skill-dir>/scripts/generate_tests.py \
  --schema schema.yaml \
  --output-dir tests/
```

The script reads the schema and produces:
- `tests/__init__.py`
- `tests/conftest.py` — builds the DB via `build_db_from_json()`, named correctly
- `tests/test_felis.py` — validates schema.yaml against the Felis spec
- `tests/test_contents.py` — checks all expected tables are present
- `tests/test_database.py` — basic ORM add/delete smoke test
- `tests/test_contents_sources.py` — Sources count (0 for empty DB)
- `tests/test_contents_kinematics.py` — kinematic table counts (if tables exist)
- `tests/test_contents_parameters.py` — parameter table counts (if tables exist)
- `tests/test_contents_<NewTable>.py` — one file per table not in the astrodb-template-db

After generation, run the tests to confirm they all pass on the fresh empty database:

```bash
cd <project-root>
uv run pytest tests/ -v
```

**If tests fail**, the most common causes:
- `conftest.py` can't find the db file → check that `database.toml` has the correct
  `db_name` and that the `.sqlite` file exists in the project root
- `test_table_presence` fails with wrong count → the schema has tables that
  `generate_tests.py` didn't account for; re-run the script (it re-reads the schema)
- Import errors for `astrodb_utils` or `felis` → run `uv add astrodb_utils felis` first

## Step 9: Final report

Tell the user:
- The database file path
- The schema.yaml location
- The database.toml location
- The data/ directory structure
- The tests/ directory and how to run them
- What to do next (e.g., add JSON data files and re-run the tests to update counts)

Example success message:
```
Database created: MyDataset.sqlite (32 KB)
Schema:           schema.yaml
Config:           database.toml
Data directory:   data/reference/  data/source/
Tests:            tests/  (run with: uv run pytest tests/ -v)

Next steps:
  1. Add JSON data files to data/source/ and run your ingestion scripts.
  2. Update the count assertions in tests/test_contents_*.py to match your data.
```

## Completion Checklist

Before telling the user the database is created, confirm every item below. Anything unmet must be done
first.

- [ ] You located the schema.yaml and confirmed `felis validate` passes on it — if it doesn't, you stopped rather than building from a broken schema.
- [ ] The database name was read from the schema's top-level `name:` field.
- [ ] `data/reference/` and `data/source/` exist, the validated schema.yaml is at the project root, and `database.toml` exists (created only if absent — an existing one was not overwritten).
- [ ] The empty SQLite database was created with `scripts/create_db.py`, and you verified the `.sqlite` file exists and is non-empty.
- [ ] The test suite was generated with `scripts/generate_tests.py`, and `uv run pytest tests/ -v` was actually run and all tests pass.
- [ ] You gave the final report: database path, schema location, config location, data directories, the tests directory with how to run them, and next steps.

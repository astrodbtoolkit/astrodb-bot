#!/usr/bin/env python
"""Generate pytest test files for a new AstroDB database based on its schema.yaml.

Adapted from the astrodb-template-db test suite. Generates test files that:
- Check all expected tables exist
- Verify basic ORM operations work
- Assert empty counts (0) for all data tables (correct for a fresh database)
- Cover any new tables not in the astrodb-template-db

Usage:
    python generate_tests.py --schema path/to/schema.yaml --output-dir path/to/tests/
"""

import argparse
import sys
from pathlib import Path

import yaml

# Tables present in the astrodb-template-db. Any table in the user's schema
# that is NOT in this set is considered "new" and gets its own test file.
TEMPLATE_TABLES = {
    "Sources", "Publications", "Names", "Telescopes", "Instruments", "Versions",
    "ProperMotions", "Parallaxes", "RadialVelocities", "Photometry", "RegimeList",
    "PhotometryFilters", "CompanionRelationships", "CompanionParameters", "CompanionList",
    "SourceTypeList", "SourceTypes", "AssociationList", "Associations",
    "ModeledParameters", "RotationalParameters", "ParameterList", "Spectra",
}


def load_schema(schema_path):
    with open(schema_path) as f:
        return yaml.safe_load(f)


def get_tables(schema):
    """Return list of dicts with name and columns for each table."""
    return schema.get("tables", [])


def get_table_names(schema):
    return [t["name"] for t in get_tables(schema)]


def get_non_nullable_columns(table):
    """Return list of (name, datatype) for non-nullable columns in a table."""
    return [
        (c["name"], c.get("datatype", "string"))
        for c in table.get("columns", [])
        if not c.get("nullable", True)
    ]


def get_all_columns(table):
    return [(c["name"], c.get("datatype", "string")) for c in table.get("columns", [])]


def dtype_to_test_value(col_name, dtype, index=0):
    """Return a sensible test value for a column given its Felis datatype."""
    float_types = {"float", "double"}
    int_types = {"int", "long", "short", "byte"}
    bool_types = {"boolean"}
    if dtype in float_types:
        return 0.0
    elif dtype in int_types:
        return 0
    elif dtype in bool_types:
        return False
    else:
        return f"TestValue{index}"


# ── Individual file writers ────────────────────────────────────────────────────

def write_init(output_dir):
    (output_dir / "__init__.py").write_text("")


def write_conftest(output_dir, db_name):
    content = f'''import os
import pytest
import logging

import astrodb_utils
from astrodb_utils import build_db_from_json

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def db():
    logger.info(f"Using version {{astrodb_utils.__version__}} of astrodb_utils")

    db = build_db_from_json()

    assert os.path.exists(
        "{db_name}.sqlite"
    ), "Database file \'{db_name}.sqlite\' was not created."

    logger.info(
        "Loaded {db_name} database using build_db_from_json function in conftest.py"
    )

    return db
'''
    (output_dir / "conftest.py").write_text(content)


def write_test_felis(output_dir):
    content = '''"""Validate the schema.yaml against the Felis specification."""
import tomllib
import yaml
from pydantic import ValidationError

from felis.datamodel import Schema


def test_schema():
    with open("database.toml", "rb") as f:
        settings = tomllib.load(f)
    schema_path = settings["felis_path"]
    data = yaml.safe_load(open(schema_path, "r"))

    try:
        schema = Schema.model_validate(data)  # noqa: F841
    except ValidationError as e:
        print(e)
        raise
'''
    (output_dir / "test_felis.py").write_text(content)


def write_test_contents(output_dir, table_names):
    """test_contents.py: table presence and basic sanity checks."""
    table_count = len(table_names)
    table_assertions = "\n".join(
        f'    assert "{t}" in db.metadata.tables.keys(), "{t} table missing"'
        for t in sorted(table_names)
    )

    photometry_test = ""
    if "Photometry" in table_names:
        photometry_test = '''

def test_magnitudes(db):
    """Check that all photometry magnitudes are plausible."""
    from sqlalchemy import or_
    t = (
        db.query(db.Photometry.c.magnitude)
        .filter(
            or_(
                db.Photometry.c.magnitude.is_(None),
                db.Photometry.c.magnitude > 100,
                db.Photometry.c.magnitude < -1,
            )
        )
        .astropy()
    )
    assert len(t) == 0, f"{len(t)} Photometry rows failed magnitude checks"
'''

    content = f'''"""
Tests for overall database structure and cross-table sanity checks.
Update n_tables if you add or remove tables from the schema.
"""


def test_table_presence(db):
    """Confirm all expected tables are present."""
    assert len(db.metadata.tables.keys()) == {table_count}, (
        f"Expected {table_count} tables, found {{len(db.metadata.tables.keys())}}: "
        f"{{sorted(db.metadata.tables.keys())}}"
    )
{table_assertions}
{photometry_test}'''
    (output_dir / "test_contents.py").write_text(content)


def write_test_database(output_dir, schema, table_names):
    """test_database.py: basic ORM add/delete test for Sources and Names."""
    table_set = set(table_names)
    if "Sources" not in table_set or "Names" not in table_set:
        return  # Skip — no Sources or Names table to test

    # Find non-nullable columns for Sources so we build a valid row
    sources_table = next(t for t in get_tables(schema) if t["name"] == "Sources")
    non_nullable = get_non_nullable_columns(sources_table)

    # Build keyword args for the test Source row
    kwargs_parts = []
    for i, (col_name, dtype) in enumerate(non_nullable):
        val = dtype_to_test_value(col_name, dtype, i)
        if isinstance(val, str):
            kwargs_parts.append(f'{col_name}="Test ORM Source"')
        elif isinstance(val, float):
            kwargs_parts.append(f"{col_name}=0.0")
        elif isinstance(val, bool):
            kwargs_parts.append(f"{col_name}=False")
        else:
            kwargs_parts.append(f"{col_name}=0")

    # Names table: assume it has source + other_name (standard template layout)
    names_table = next((t for t in get_tables(schema) if t["name"] == "Names"), None)
    names_nonnull = get_non_nullable_columns(names_table) if names_table else []

    name_kwargs = 'source="Test ORM Source", other_name="Test Alias"'
    if names_nonnull:
        name_kwargs_parts = []
        for i, (col_name, dtype) in enumerate(names_nonnull):
            if col_name == "source":
                name_kwargs_parts.append('source="Test ORM Source"')
            elif col_name == "other_name":
                name_kwargs_parts.append('other_name="Test Alias"')
            else:
                val = dtype_to_test_value(col_name, dtype, i)
                if isinstance(val, str):
                    name_kwargs_parts.append(f'{col_name}="TestNameVal"')
                else:
                    name_kwargs_parts.append(f"{col_name}={val!r}")
        name_kwargs = ", ".join(name_kwargs_parts)

    source_kwargs = ", ".join(kwargs_parts) if kwargs_parts else 'source="Test ORM Source"'

    content = f'''"""
Tests that the database ORM works as expected.
These tests add and remove rows to verify basic database operations —
they should not need modification as data is added to the database.
"""
from sqlalchemy.ext.automap import automap_base


def test_orm_use(db):
    """Verify adding and removing a source via the ORM works correctly."""
    Base = automap_base(metadata=db.metadata)
    Base.prepare()

    Sources = Base.classes.Sources
    Names = Base.classes.Names

    s = Sources({source_kwargs})
    n = Names({name_kwargs})

    with db.session as session:
        session.add(s)
        session.add(n)
        session.commit()

    assert db.query(db.Sources).filter(db.Sources.c.source == "Test ORM Source").count() == 1
    assert db.query(db.Names).filter(db.Names.c.other_name == "Test Alias").count() == 1

    with db.session as session:
        session.delete(n)
        session.delete(s)
        session.commit()

    assert db.query(db.Sources).filter(db.Sources.c.source == "Test ORM Source").count() == 0
'''
    (output_dir / "test_database.py").write_text(content)


def write_test_sources(output_dir, schema, table_names):
    if "Sources" not in table_names:
        return

    # Only include the coordinate test if ra_deg and dec_deg exist in Sources
    sources_table = next((t for t in get_tables(schema) if t["name"] == "Sources"), None)
    source_col_names = {c["name"] for c in sources_table.get("columns", [])} if sources_table else set()
    has_coords = "ra_deg" in source_col_names and "dec_deg" in source_col_names

    coord_test = ""
    if has_coords:
        coord_test = '''

def test_coordinates(db):
    """Verify all sources have valid RA/Dec coordinates."""
    t = (
        db.query(db.Sources.c.source, db.Sources.c.ra_deg, db.Sources.c.dec_deg)
        .filter(
            or_(
                db.Sources.c.ra_deg.is_(None),
                db.Sources.c.ra_deg < 0,
                db.Sources.c.ra_deg > 360,
                db.Sources.c.dec_deg.is_(None),
                db.Sources.c.dec_deg < -90,
                db.Sources.c.dec_deg > 90,
            )
        )
        .astropy()
    )
    assert len(t) == 0, f"{len(t)} Sources failed coordinate checks: {t}"
'''

    imports = "from sqlalchemy import or_\n\n\n" if has_coords else "\n"
    content = f'''"""
Tests for the Sources table.
As data is added, update n_sources to reflect the actual expected count.
"""
{imports}def test_sources(db):
    n_sources = db.query(db.Sources).count()
    assert n_sources == 0, f"Found {{n_sources}} sources, expected 0 (empty database)"
{coord_test}'''
    (output_dir / "test_contents_sources.py").write_text(content)


def write_test_kinematics(output_dir, table_names):
    kinematic = {"ProperMotions", "Parallaxes", "RadialVelocities"}
    present = kinematic & set(table_names)
    if not present:
        return

    blocks = []

    if "RadialVelocities" in present:
        blocks.append('''def test_radial_velocities(db):
    t = db.query(db.RadialVelocities.c.rv_kms).astropy()
    n_radial_velocities = 0
    assert (
        len(t) == n_radial_velocities
    ), f"Found {len(t)} entries in RadialVelocities, expected {n_radial_velocities}"
''')

    if "ProperMotions" in present:
        blocks.append('''def test_proper_motions(db):
    t = db.query(db.ProperMotions.c.pm_ra).astropy()
    n_proper_motions = 0
    assert (
        len(t) == n_proper_motions
    ), f"Found {len(t)} entries in ProperMotions, expected {n_proper_motions}"
''')

    if "Parallaxes" in present:
        blocks.append('''def test_parallaxes(db):
    t = db.query(db.Parallaxes.c.parallax_mas).astropy()
    n_parallaxes = 0
    assert (
        len(t) == n_parallaxes
    ), f"Found {len(t)} entries in Parallaxes, expected {n_parallaxes}"
''')

    content = (
        '"""\n'
        "Test kinematic and astrometry tables.\n"
        "As data is added, update the expected counts.\n"
        '"""\n\n\n'
        + "\n".join(blocks)
    )
    (output_dir / "test_contents_kinematics.py").write_text(content)


def write_test_parameters(output_dir, table_names):
    param_tables = {"CompanionParameters", "ModeledParameters", "RotationalParameters"}
    present = param_tables & set(table_names)
    if not present:
        return

    blocks = []

    if "CompanionParameters" in present:
        blocks.append('''def test_companion_parameters(db):
    t = db.query(db.CompanionParameters.c.source).astropy()
    n_companion_parameters = 0
    assert (
        len(t) == n_companion_parameters
    ), f"Found {len(t)} entries in CompanionParameters, expected {n_companion_parameters}"
''')

    if "ModeledParameters" in present:
        blocks.append('''def test_modeled_parameters(db):
    t = db.query(db.ModeledParameters.c.parameter).astropy()
    n_parameters = 0
    assert (
        len(t) == n_parameters
    ), f"Found {len(t)} entries in ModeledParameters, expected {n_parameters}"
''')

    if "RotationalParameters" in present:
        blocks.append('''def test_rotational_parameters(db):
    t = db.query(db.RotationalParameters.c.source).astropy()
    n_rotational_parameters = 0
    assert (
        len(t) == n_rotational_parameters
    ), f"Found {len(t)} entries in RotationalParameters, expected {n_rotational_parameters}"
''')

    content = (
        '"""\n'
        "Tests for parameter tables.\n"
        "As data is added, update the expected counts.\n"
        '"""\n\n\n'
        + "\n".join(blocks)
    )
    (output_dir / "test_contents_parameters.py").write_text(content)


def write_new_table_tests(output_dir, new_tables, schema):
    """Generate a test file for each table not in the template."""
    for table_name in new_tables:
        # Find a good query column: prefer first non-nullable column
        table = next((t for t in get_tables(schema) if t["name"] == table_name), None)
        non_nullable = get_non_nullable_columns(table) if table else []
        query_col = non_nullable[0][0] if non_nullable else "id"

        safe_name = table_name.lower()
        content = f'''"""
Tests for the {table_name} table.
This table was not part of the astrodb-template-db schema.
As data is added, update n_entries to reflect the expected count.
"""


def test_{safe_name}_table_exists(db):
    """Confirm {table_name} was created in the database."""
    assert "{table_name}" in db.metadata.tables.keys(), (
        "{table_name} table not found — check that schema.yaml includes it"
    )


def test_{safe_name}_count(db):
    """Fresh database should have 0 entries in {table_name}."""
    n_entries = db.query(db.{table_name}).count()
    assert n_entries == 0, (
        f"Found {{n_entries}} entries in {table_name}, expected 0 (empty database)"
    )
'''
        (output_dir / f"test_contents_{safe_name}.py").write_text(content)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate pytest test files for a new AstroDB database"
    )
    parser.add_argument("--schema", required=True, help="Path to schema.yaml")
    parser.add_argument("--output-dir", required=True, help="Directory to write test files into")
    args = parser.parse_args()

    schema_path = Path(args.schema)
    output_dir = Path(args.output_dir)

    if not schema_path.exists():
        print(f"ERROR: schema not found: {schema_path}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    schema = load_schema(schema_path)
    db_name = schema["name"]
    table_names = get_table_names(schema)
    new_tables = [t for t in table_names if t not in TEMPLATE_TABLES]

    print(f"Database name : {db_name}")
    print(f"Tables ({len(table_names)}) : {', '.join(table_names)}")
    if new_tables:
        print(f"New tables    : {', '.join(new_tables)}")
    print()

    write_init(output_dir)
    write_conftest(output_dir, db_name)
    write_test_felis(output_dir)
    write_test_contents(output_dir, table_names)
    write_test_database(output_dir, schema, table_names)
    write_test_sources(output_dir, schema, table_names)
    write_test_kinematics(output_dir, table_names)
    write_test_parameters(output_dir, table_names)
    write_new_table_tests(output_dir, new_tables, schema)

    generated = sorted(output_dir.glob("*.py"))
    print(f"Generated {len(generated)} files in {output_dir}/")
    for f in generated:
        print(f"  {f.name}")
    print()
    print(f"Run tests with:  uv run pytest {output_dir}/ -v")


if __name__ == "__main__":
    main()

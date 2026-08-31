#!/usr/bin/env python
"""Create an empty AstroDB SQLite database from a Felis schema.yaml.

Usage:
    python create_db.py --schema path/to/schema.yaml --db-path path/to/output.sqlite
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Create an empty AstroDB SQLite database from a Felis schema.yaml"
    )
    parser.add_argument("--schema", required=True, help="Path to the Felis schema.yaml")
    parser.add_argument("--db-path", required=True, help="Output path for the SQLite database file")
    args = parser.parse_args()

    schema_path = Path(args.schema).resolve()
    db_path = Path(args.db_path).resolve()

    if not schema_path.exists():
        print(f"ERROR: Schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure the parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection_string = f"sqlite:///{db_path}"

    print(f"Schema:     {schema_path}")
    print(f"Database:   {db_path}")
    print(f"Connection: {connection_string}")
    print()

    try:
        from astrodbkit.astrodb import create_database
    except ImportError as e:
        print(f"ERROR: Could not import astrodbkit: {e}", file=sys.stderr)
        print("Install it with: uv add astrodbkit", file=sys.stderr)
        sys.exit(1)

    try:
        session, base, engine = create_database(
            connection_string,
            felis_schema=str(schema_path),
        )
        session.close()
    except Exception as e:
        print(f"ERROR: Database creation failed: {e}", file=sys.stderr)
        raise

    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        print(f"Success! Created {db_path.name} ({size_kb:.1f} KB)")
    else:
        print("ERROR: create_database returned without error but the file was not created.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

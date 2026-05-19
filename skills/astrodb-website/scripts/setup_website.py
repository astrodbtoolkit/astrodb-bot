#!/usr/bin/env python
"""Setup script for Astro-Web skill.

Generates a .env file for Astro-Web based on a provided database path.
"""

import argparse
import sys
from pathlib import Path

import tomllib


def main():
    parser = argparse.ArgumentParser(description="Setup Astro-Web .env file")
    parser.add_argument("--db-path", required=True, help="Path to the SQLite database")
    parser.add_argument("--website-dir", required=True, help="Directory where Astro-Web is cloned")
    parser.add_argument("--toml-path", help="Path to database.toml (optional)")
    parser.add_argument("--ra-col", default="ra", help="Name of the RA column (default: ra)")
    parser.add_argument("--dec-col", default="dec", help="Name of the Dec column (default: dec)")
    parser.add_argument("--primary-table", default="Sources", help="Name of the primary sources table (default: Sources)")
    args = parser.parse_args()

    db_path = Path(args.db_path).resolve()
    if not db_path.exists():
        print(f"ERROR: Database file not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    astro_web_dir = Path(args.website_dir).resolve()
    if not astro_web_dir.exists():
        print(f"ERROR: Website directory not found at {astro_web_dir}", file=sys.stderr)
        sys.exit(1)

    # Look for database.toml
    toml_path = None
    if args.toml_path:
        toml_path = Path(args.toml_path).resolve()
    else:
        # Check project root (2 levels up from skills/astrodb-website/)
        root_toml = Path(__file__).parent.parent.parent.parent / "database.toml"
        if root_toml.exists():
            toml_path = root_toml
        else:
            # Check same dir as DB
            db_dir_toml = db_path.parent / "database.toml"
            if db_dir_toml.exists():
                toml_path = db_dir_toml

    lookup_tables = []
    if toml_path and toml_path.exists():
        print(f"Reading configuration from {toml_path}")
        if tomllib:
            try:
                with open(toml_path, "rb") as f:
                    config = tomllib.load(f)
                    lookup_tables = config.get("lookup_tables", [])
            except Exception as e:
                print(f"WARNING: Could not parse {toml_path}: {e}")
        else:
            print("WARNING: tomllib not available, skipping database.toml parsing")

    # Prepare .env content
    # Use absolute path for database URL to avoid relative path confusion
    db_url = f"sqlite:///{db_path}"

    env_content = [
        f'ASTRO_WEB_DATABASE_URL="{db_url}"',
        'ASTRO_WEB_SCHEMA=""',
    ]

    if lookup_tables:
        env_content.append(f'ASTRO_WEB_LOOKUP_TABLES="{",".join(lookup_tables)}"')
    else:
        # Default lookup tables from Astro-Web .env.example
        env_content.append(
            'ASTRO_WEB_LOOKUP_TABLES="Publications,Telescopes,Instruments,PhotometryFilters,Versions,RegimeList,SourceTypeList,ParameterList,AssociationList,CompanionList,Modes,Filters,Citations,References,Parameters,Regimes"'
        )

    # Add other defaults
    env_content.extend(
        [
            f'ASTRO_WEB_PRIMARY_TABLE="{args.primary_table}"',
            'ASTRO_WEB_SOURCE_COLUMN="source"',
            'ASTRO_WEB_FOREIGN_KEY="source"',
            'ASTRO_WEB_PRIMARY_DATATYPE="str"',
            f'ASTRO_WEB_RA_COLUMN="{args.ra_col}"',
            f'ASTRO_WEB_DEC_COLUMN="{args.dec_col}"',
            'ASTRO_WEB_SPECTRA_URL_COLUMN="access_url"',
            'ASTRO_WEB_SOURCE_URL_BASE="/source/"',
        ]
    )

    env_path = astro_web_dir / ".env"
    with open(env_path, "w") as f:
        f.write("\n".join(env_content) + "\n")

    print(f"Successfully generated {env_path}")
    print("\nNext steps:")
    print(f"  cd {astro_web_dir.relative_to(Path.cwd())}")
    print("  uv sync")
    print("  uv run serve  # Recommended")
    print("  # OR: uv run uvicorn astro_web.main:app --reload --port 8000")


if __name__ == "__main__":
    main()

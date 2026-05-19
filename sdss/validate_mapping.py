#!/usr/bin/env python3
"""Validate schema mapping: check nulls and types for drpall → manga-schema."""

import json
import os
import yaml
import numpy as np
from astropy.table import Table

# Paths
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "drpall-v3_1_1.fits")
SCHEMA_FILE = os.path.join(BASE, "manga-schema.yaml")
OUTPUT_JSON = os.path.join(BASE, "validation-result.json")

# Mappings from drpall-v3_1_1-schema-match.md (Column -> DB Table, DB Field)
MAPPINGS = [
    ("plateifu", "Names", "other_name"),
    ("mangaid", "Sources", "source"),
    ("objra", "Sources", "ra_deg"),
    ("objdec", "Sources", "dec_deg"),
    ("ifura", "Positions", "ra_deg"),
    ("ifudec", "Positions", "dec_deg"),
    ("ebvgal", "ModeledParameters", "value"),
    ("z", "RadialVelocities", "rv_kms"),
    ("nsa_z", "RadialVelocities", "rv_kms"),
    ("nsa_zdist", "ModeledParameters", "value"),
    ("nsa_sersic_mass", "ModeledParameters", "value"),
    ("nsa_elpetro_mass", "ModeledParameters", "value"),
    ("nsa_elpetro_ba", "Morphology", "ellipticity"),
    ("nsa_elpetro_phi", "Morphology", "position_angle_deg"),
    ("nsa_extinction", "ModeledParameters", "value"),
    ("nsa_elpetro_th50_r", "Morphology", "half_light_radius_arcmin"),
    ("nsa_petro_th50", "Morphology", "half_light_radius_arcmin"),
    ("nsa_sersic_ba", "Morphology", "ellipticity"),
    ("nsa_sersic_n", "ModeledParameters", "value"),
    ("nsa_sersic_phi", "Morphology", "position_angle_deg"),
    ("nsa_sersic_th50", "Morphology", "half_light_radius_arcmin"),
    ("nsa_iauname", "Names", "other_name"),
]


def load_schema(path):
    """Build schema_fields[table][field] -> {datatype, nullable, length}."""
    with open(path) as f:
        schema = yaml.safe_load(f)
    fields = {}
    for tbl in schema.get("tables", []):
        tname = tbl["name"]
        fields[tname] = {}
        for col in tbl.get("columns", []):
            cname = col["name"]
            fields[tname][cname] = {
                "datatype": col.get("datatype", "string"),
                "nullable": col.get("nullable", True),
                "length": col.get("length"),
            }
    return fields


def count_nulls(col):
    """Count null/missing values in a column (handles FITS masked arrays)."""
    if hasattr(col, "mask"):
        return int(np.sum(col.mask))
    arr = np.asarray(col)
    if np.issubdtype(arr.dtype, np.floating):
        return int(np.sum(np.isnan(arr)))
    if np.issubdtype(arr.dtype, np.integer):
        # No standard "null" for int; check for sentinel if needed
        return 0
    # string/object
    null_count = 0
    for v in arr.flat:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            null_count += 1
    return null_count


def is_type_compatible(data_dtype, schema_datatype):
    """Check if data dtype is compatible with schema datatype."""
    schema_type = schema_datatype.lower()
    if schema_type in ("string",):
        return any(
            np.issubdtype(data_dtype, t) for t in (np.str_, np.object_, np.bytes_)
        )
    if schema_type in ("double", "float"):
        return np.issubdtype(data_dtype, np.floating) or np.issubdtype(
            data_dtype, np.integer
        )
    if schema_type in ("int", "long"):
        return np.issubdtype(data_dtype, np.integer)
    if schema_type == "boolean":
        return np.issubdtype(data_dtype, np.bool_)
    if schema_type == "timestamp":
        return "datetime" in str(data_dtype) or any(
            np.issubdtype(data_dtype, t) for t in (np.str_, np.object_)
        )
    return True


def main():
    schema_fields = load_schema(SCHEMA_FILE)
    t = Table.read(DATA_FILE)
    nrows = len(t)

    results = []
    for data_col, db_table, db_field in MAPPINGS:
        if data_col not in t.colnames:
            results.append(
                {
                    "data_column": data_col,
                    "db_table": db_table,
                    "db_field": db_field,
                    "error": "Column not in data file",
                    "null_count": None,
                    "data_dtype": None,
                    "schema_nullable": None,
                    "schema_datatype": None,
                }
            )
            continue

        col = t[data_col]
        null_count = count_nulls(col)
        data_dtype = np.asarray(col).dtype

        schema_info = schema_fields.get(db_table, {}).get(db_field)
        if not schema_info:
            results.append(
                {
                    "data_column": data_col,
                    "db_table": db_table,
                    "db_field": db_field,
                    "error": "Schema field not found",
                    "null_count": null_count,
                    "data_dtype": str(data_dtype),
                    "schema_nullable": None,
                    "schema_datatype": None,
                }
            )
            continue

        schema_nullable = schema_info["nullable"]
        schema_datatype = schema_info["datatype"]
        compatible = is_type_compatible(data_dtype, schema_datatype)

        nullable_violation = not schema_nullable and null_count > 0
        type_mismatch = not compatible

        results.append(
            {
                "data_column": data_col,
                "db_table": db_table,
                "db_field": db_field,
                "null_count": int(null_count),
                "nrows": nrows,
                "data_dtype": str(data_dtype),
                "schema_nullable": schema_nullable,
                "schema_datatype": schema_datatype,
                "nullable_violation": nullable_violation,
                "type_mismatch": type_mismatch,
                "compatible": compatible,
            }
        )

    with open(OUTPUT_JSON, "w") as f:
        json.dump({"nrows": nrows, "results": results}, f, indent=2)

    print(f"Wrote {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

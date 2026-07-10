---
name: astrodb-build-parse-table
description: Parse a data table file and extract column information (name, description, units, type). Supports FITS, CSV, ECSV, HDF5, VOTable, Parquet, Excel, and more. Generates a markdown table summarizing the columns.
compatibility: python, astropy, pandas
metadata:
    authors: ["Claude"]

---

# Parse Data Table

## Instructions
Parse the data table file `$ARGUMENTS` and extract column information.

### Step 0: Check for a directions document

Before doing anything else, check whether `artifacts/directions.md` exists in the current working
directory. If it does, read it now — it captures dataset-specific decisions (columns to skip, how
to handle edge cases, schema choices) that should guide your interpretation throughout this skill.
If it doesn't exist, proceed without it.

**All outputs from this skill must be written inside a folder named `astrodb-build-artifacts/` in the current working directory.** Create this folder before writing any files.

### Step 1: Create the artifact folder

Run this before anything else:

```bash
mkdir -p astrodb-build-artifacts
```

If this fails, stop and tell the user you cannot create the output directory.

### Step 1: Make sure Python is installed and the necessary libraries are available

Work through these options in order — stop at the first one that succeeds:

**Option 1: astropy is already available**
```bash
python3 -c "import sys; assert sys.version_info >= (3, 11), f'Python 3.11+ required, got {sys.version}'; import astropy; print('ok')"
```
If this prints `ok`, proceed directly to Step 2. If it raises an `AssertionError`, Python is too old — fall through to Option 2 or 3, which will use a newer Python automatically.

**Option 2: use `uv` (fast, no project directory needed)**
```bash
uv run --python 3.11 --with astropy --with pandas python3 script.py
```
If `uv` is installed, this handles everything — no separate install step required. The `--python 3.11` flag ensures Python 3.11+ is used. Use this form to run all scripts in Steps 2–3.

**Option 3: `uv` is not installed — use `pip`**

First verify the Python version:
```bash
python3 -c "import sys; assert sys.version_info >= (3, 11), f'Need Python 3.11+, got {sys.version}'"
```
If that passes:
```bash
pip install astropy pandas
python3 script.py
```
If that fails, tell the user Python 3.11 or greater is required and ask them to install it or activate an appropriate environment.

**Option 4: nothing works**

If none of the above work, tell the user you're unable to install the required libraries and ask them to run in an environment that has either `uv` or `pip` available.

### Step 2: Read the file

Use `astropy.table.Table.read()` first, which handles most formats automatically. Fall back to `pandas` if needed:

```python
import json, os
from astropy.table import Table

reader = None
pandas_method = None

# Detect format from file extension — more reliable than inspecting table metadata.
ext = os.path.splitext("$ARGUMENTS")[1].lower()
fmt_map = {
    '.fits': 'fits', '.fit': 'fits',
    '.csv': 'csv', '.ecsv': 'ecsv',
    '.hdf5': 'hdf5', '.h5': 'hdf5',
    '.vot': 'votable', '.xml': 'votable',
    '.parquet': 'parquet',
    '.xlsx': 'excel', '.xls': 'excel',
}
fmt = fmt_map.get(ext)

try:
    t = Table.read("$ARGUMENTS")
    reader = "astropy"
    n_rows = len(t)
    for col in t.columns:
        print(col, t[col].dtype)  # descriptions/units extracted in Step 3
except Exception:
    import pandas as pd
    df = pd.read_csv("$ARGUMENTS")  # adjust reader as needed
    reader = "pandas"
    pandas_method = "read_csv"  # update if a different reader was used
    n_rows = len(df)
    for col in df.columns:
        print(col, df[col].dtype)

# Write sidecar so downstream skills (e.g. astrodb-build-schema-match, astrodb-build-schema-validate)
# can reuse the same reader without re-discovering the format.
# Output file paths are added to the sidecar in Step 5.
with open("astrodb-build-artifacts/astrodb-parse-result.json", "w") as f:
    json.dump({
        "file_path": "$ARGUMENTS",
        "reader": reader,
        "format": fmt,
        "pandas_method": pandas_method,
        "n_rows": n_rows,
    }, f)
```

See `references/file-formats.md` for the full list of supported formats.

### Step 3: Extract column information

For each column, extract:
- **Column name**
- **Description** (from metadata/comments; use "—" if not available)
- **Units** (use "—" if not specified)
- **Data type** (e.g. `float64`, `int32`, `str`)

**Important:** `t[col].description` is only reliably populated for ECSV files. For all other formats (FITS, CSV, HDF5, VOTable, etc.), ignore what Step 2 printed for descriptions and extract them using the format-specific methods in `references/format-specific-metadata.md`.

#### Converting dtypes to human-readable strings

The dtype printed by Step 2 may be a raw numpy code. Convert before displaying:

| Raw dtype | Display as |
|-----------|------------|
| `>f4`, `float32` | `float32` |
| `>f8`, `float64` | `float64` |
| `>i2`, `int16` | `int16` |
| `>i4`, `int32` | `int32` |
| `<U9` (any length) | `str` |
| `\|S10` (any length) | `str` |
| `bool` | `bool` |

For string columns, you may optionally note the length (e.g. `str (16-char)`) if it is meaningful.

#### Inferring missing descriptions

When a column has no description in the file metadata, try to infer one from context:

- Columns ending in `+` or `_plus` → upper uncertainty on the base column (e.g. `dmod+` → "Upper uncertainty on dmod")
- Columns ending in `-` or `_minus` → lower uncertainty (e.g. `dmod-` → "Lower uncertainty on dmod")
- Columns with `err`, `e_`, or `sig` prefixes/suffixes → errors or standard deviations; use the base column's description to construct the inferred description

If you can't infer a description confidently, leave it as "—".

#### Inferring missing units

When a column has no units in the file metadata, consult `references/units-inference.md` for the lookup table and uncertainty-column inheritance logic.

### Step 4: Ask the user to fill in any remaining gaps

After exhausting file metadata and inference, if there are still columns with missing descriptions or units, ask the user to fill them in — but only if the number is manageable (fewer than 10). Present each missing column one at a time and wait for the user's response before moving to the next.

For example:
> Column `vrot_s` has no description. Do you know what this column represents?

> Column `e=1-b/a` has no units. What units should this column have, or is it dimensionless?

If there are 10 or more columns still missing descriptions or units, output the table as-is with "—" placeholders and note at the end how many are missing, so the user can address them separately.

### Step 5: Output the results

Write both output files directly inside `astrodb-build-artifacts/` — no subdirectory. Name them
after the input file's base name with a `-parsed-data-table` suffix. **Do not overwrite existing
files** — if the file already exists, append `-1`, `-2`, etc. to the base name until a free name
is found. For example, if the input is `data/catalog.fits`, write:
- `astrodb-build-artifacts/catalog-parsed-data-table.md`
- `astrodb-build-artifacts/catalog-parsed-data-table.html`

Each file should begin with a metadata block:

```
# Column Information: <filename>

**File:** `<filename>`
**Format:** <format>
**Reader:** <astropy | pandas>
**Rows:** <n_rows>
**Columns:** <n_cols>
```

Then the markdown table:

| Column | Description | Units | Type |
|--------|-------------|-------|------|

Followed by notes as a bulleted list (e.g. missing metadata, inferred values, source file anomalies).

Do not display this table in the chat — instead, write it to a markdown file using the `Write` tool, and provide a link to that file in the chat.

Also render this result as an HTML file using the `Write` tool, with the same metadata block, table, and notes.

Display links to both the markdown table and the HTML file in the chat, and suggest opening the HTML file with a browser for best visualization.

After writing the output files, update the sidecar to record their paths:

```python
import json

with open("astrodb-build-artifacts/astrodb-parse-result.json") as f:
    sidecar = json.load(f)

sidecar["output_md"] = "astrodb-build-artifacts/<basename>-parsed-data-table.md"
sidecar["output_html"] = "astrodb-build-artifacts/<basename>-parsed-data-table.html"

with open("astrodb-build-artifacts/astrodb-parse-result.json", "w") as f:
    json.dump(sidecar, f)
```

### Step 6: Iterate as needed

Ask the user to inspect the results table and check if everything looks good, or if they want to make any edits to the descriptions, units, or types. If they want to make edits, allow them to specify which column(s) and what changes to make, then update the markdown and HTML files accordingly.
---
name: astrodb-build-parse-table
description: Parse a data table file and extract column information (name, description, units, type). Supports FITS, CSV, ECSV, HDF5, VOTable, MRT, Parquet, Excel, and more. Generates a markdown table summarizing the columns.
compatibility: python, astropy, pandas
metadata:
    authors: ["Claude"]

---

# Parse Data Table

## Instructions
Parse the data table file `$ARGUMENTS` and extract column information.

### Step 0: Read context documents and set up

1. Read `references/astrodb-directions.md` — it defines the `workflow.md`, artifact-folder, and
   completion-checklist conventions this skill follows.
2. Check whether `workflow.md` exists in the current working directory. If it does, read it to carry
   forward context from prior skills.
3. Create the artifact folder:

   ```bash
   mkdir -p astrodb-build-artifacts
   ```

   If this fails, stop and tell the user you cannot create the output directory.
4. Initialize this skill's checklist file per the completion-checklist convention: copy the items from
   `## Completion Checklist` (bottom of this file) into
   `astrodb-build-artifacts/astrodb-build-parse-table-checklist.md`.
5. Look for a **directions document** — the user's own notes on this dataset (columns to skip, how to
   handle edge cases, schema decisions already made). Work through these in order and stop at the first
   hit:
   - **The user provided a path** (e.g. in their opening message). Read it, then copy it to
     `astrodb-build-artifacts/directions.md` so later skills — and later runs of this one — pick it up
     without the user having to re-supply the path every time.
   - **`astrodb-build-artifacts/directions.md` already exists** from a prior run. Read it as-is; it's
     already in its canonical home, so there's nothing to copy.
   - **Neither.** Proceed without one. It's optional, so don't stop to ask for it.

   When you do find one, let its guidance override the default heuristics in this skill. The user wrote
   it precisely because they know something about this data that the general rules don't capture — a
   column that looks like photometry but isn't, a unit that's mislabeled upstream. Silently applying the
   defaults over an explicit instruction is the failure this lookup exists to prevent.

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
    # Before falling back to pandas, check whether this is a CDS/AAS machine-readable
    # table (common for .txt/.dat files distributed alongside journal articles).
    # Table.read() can't auto-identify this format and raises above, but pandas.read_csv()
    # won't error either — it'll silently parse the header text into one garbage column.
    # See references/format-specific-metadata.md for details.
    with open("$ARGUMENTS") as f:
        head = f.read(4000)
    if "Byte-by-byte Description of file" in head:
        t = Table.read("$ARGUMENTS", format="ascii.mrt")
        reader = "astropy"
        fmt = "mrt"
        n_rows = len(t)
        for col in t.columns:
            print(col, t[col].dtype)
    else:
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

**Important:** `t[col].description` is only reliably populated for ECSV and CDS/MRT files. For all other formats (FITS, plain CSV, HDF5, VOTable, etc.), ignore what Step 2 printed for descriptions and extract them using the format-specific methods in `references/format-specific-metadata.md`.

#### Checking for sentinel fill values

Legacy fixed-width astronomy formats (MRT tables especially, but also older FITS/CSV exports) sometimes mark missing data with a literal placeholder — `999`, `-999`, `-99.9` — instead of a true null. These aren't caught by the reader, so a quick scan matters: if a numeric column's max or min value is a suspiciously round number that recurs far more often than its neighbors, treat it as a fill value rather than a real measurement, and note it in the output (see Step 5) rather than silently reporting it as data.

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

Create a new output directory inside `astrodb-build-artifacts/`, named after the input file's base name with a `-parsed-data-table` suffix. **Do not overwrite an existing directory** — if the directory already exists, append `-1`, `-2`, etc. until a free name is found. For example, if the input is `data/catalog.fits`, create `astrodb-build-artifacts/catalog-parsed-data-table/` and save:
- `astrodb-build-artifacts/catalog-parsed-data-table/catalog-parsed-data-table.md`
- `astrodb-build-artifacts/catalog-parsed-data-table/catalog-parsed-data-table.html`

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

sidecar["output_md"] = "<path to .md file>"
sidecar["output_html"] = "<path to .html file>"

with open("astrodb-build-artifacts/astrodb-parse-result.json", "w") as f:
    json.dump(sidecar, f)
```

### Step 6: Iterate as needed

Ask the user to inspect the results table and check if everything looks good, or if they want to make any edits to the descriptions, units, or types. If they want to make edits, allow them to specify which column(s) and what changes to make, then update the markdown and HTML files accordingly.

## Final Step: Update `workflow.md`

Follow the convention in `references/astrodb-directions.md`. Append one new entry to
`workflow.md` in the current working directory (create it with the standard header if it
doesn't exist yet). Record: which file was parsed, which reader was used and why, any
column descriptions or units that were inferred, what the user confirmed during gap-filling,
and any columns still missing metadata.

## Completion Checklist

Track this checklist as a file per the **completion-checklist convention** in
`references/astrodb-directions.md`: you copied it to
`astrodb-build-artifacts/astrodb-build-parse-table-checklist.md` when you started and ticked items with
evidence as you went. Before telling the user the table is parsed, read that file back — any unchecked
box means you are not done (finish it, or record the user's explicit waiver) — then reproduce the
evidence-annotated checklist here. Don't claim a value you didn't actually extract.

- [ ] Descriptions were extracted using the format-specific methods in `references/format-specific-metadata.md` — not taken from what Step 2 printed (which is only reliable for ECSV and CDS/MRT).
- [ ] For a `.txt`/`.dat` input, you checked for the `Byte-by-byte Description of file` MRT signature before treating it as plain CSV.
- [ ] Numeric columns were spot-checked for sentinel fill values (e.g. `999`, `-999`); any found are noted in the output rather than reported as real data.
- [ ] Missing descriptions/units were inferred where possible; for any still missing, you asked the user (when fewer than 10) or noted at the end how many remain.
- [ ] dtypes are shown as human-readable strings (e.g. `float64`, `str`), not raw numpy codes like `>f8`.
- [ ] Output went to a fresh `astrodb-build-artifacts/<base>-parsed-data-table/` directory (an existing one was not overwritten), and both the `.md` and `.html` files were written, each beginning with the metadata block.
- [ ] The file was successfully read (astropy first, pandas fallback) in a verified Python 3.11+ environment, and the sidecar `astrodb-build-artifacts/astrodb-parse-result.json` records the reader, format, and row count — then was updated with the output file paths.
- [ ] You showed links to both files in the chat (the table was not dumped inline) and invited the user to review or edit.

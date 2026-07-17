# Supported File Formats

`astropy.table.Table.read()` handles most of these automatically. Fall back to `pandas` if needed.

| Extension(s) | Format |
|---|---|
| `.fits`, `.fit`, `.fz` | FITS |
| `.csv`, `.tsv` | CSV / TSV |
| `.dat`, `.txt`, `.ascii` | ASCII / fixed-width, **or** a CDS/MRT machine-readable table — check before assuming plain CSV, see below |
| `.ecsv` | ECSV (Enhanced CSV with metadata) |
| `.hdf5`, `.h5` | HDF5 |
| `.xml`, `.vot` | VOTable |
| `.xlsx`, `.xls` | Excel |
| `.parquet` | Parquet |
| `.json` | JSON |

For plain CSV/TSV, column descriptions usually aren't embedded in the file — leave description as "—".

**`.txt`/`.dat` files need a closer look before you pick a reader.** Journals (ApJ, AJ, A&A, MNRAS) commonly distribute supplementary data as "machine-readable tables" (MRT), a fixed-width text format with a `Byte-by-byte Description of file:` header that already contains every column's name, unit, and description. `Table.read()` cannot auto-identify this format from content or extension — it raises `IORegistryError` — so a naive fallback to `pandas.read_csv()` silently produces one garbage column from the header text instead of failing loudly. Always check for the MRT signature *before* falling back to pandas. See `references/format-specific-metadata.md` for detection and the exact reader call.

# Format-Specific Metadata

## FITS

FITS BINTABLEs store column descriptions in `TCOMMn` header keywords, and units in `TUNITn`. Read them directly:

```python
from astropy.io import fits

with fits.open("file.fits") as hdul:
    hdr = hdul[1].header  # BINTABLE is usually extension 1
    n_cols = hdr['TFIELDS']
    for i in range(1, n_cols + 1):
        name = hdr.get(f'TTYPE{i}', '')
        desc = hdr.get(f'TCOMM{i}', None)
        unit = hdr.get(f'TUNIT{i}', None)
```

Also check for embedded VOTable XML metadata — some FITS files store richer descriptions there. If the PRIMARY HDU header has `VOTMETA = T`, extract it:

```python
with fits.open("file.fits") as hdul:
    if hdul[0].header.get('VOTMETA'):
        xml_str = hdul[0].data.tobytes().decode('utf-8', errors='replace')
        # parse <FIELD name="..."><DESCRIPTION>...</DESCRIPTION></FIELD> elements
```

## ECSV

Descriptions and units are in the YAML header at the top of the file. `astropy` usually populates `t[col].description` and `t[col].unit` automatically for these.

## CSV / TSV / Plain text

Descriptions are not embedded in these formats — leave as "—".

## CDS / AAS Machine-Readable Tables (MRT)

Before treating a `.txt` or `.dat` file as plain CSV, check the first ~50 lines for a line containing `Byte-by-byte Description of file:`. That marks a CDS/MRT table — the format ApJ, AJ, A&A, and MNRAS use for machine-readable data behind published papers. Its header spells out every column's byte range, format code, unit, and label/explanation, so this format actually carries *richer* metadata than most — don't leave descriptions as "—" here.

```python
with open(path) as f:
    head = f.read(4000)
is_mrt = "Byte-by-byte Description of file" in head
```

`Table.read()` cannot auto-identify this format (it raises `IORegistryError`), so it must be requested explicitly:

```python
from astropy.table import Table
t = Table.read(path, format="ascii.mrt")
```

This populates `t[col].unit` and `t[col].description` directly from the header — no inference needed. Two things to watch for:

- **Unrecognized units**: astropy may warn that a unit like `g/cm^2` "did not parse as cds unit". This is harmless — the unit string is still captured correctly, just as an `UnrecognizedUnit` rather than a composed astropy unit. Use it as-is.
- **Sentinel fill values**: MRT tables are supposed to mark missing data with blank fields (which astropy masks automatically), but some authors instead write a literal placeholder like `999`, `-999`, or `-99.9` into numeric columns. Astropy has no way to know these aren't real measurements — they won't be masked. Spot-check numeric columns for a suspiciously repeated value at the max/min and call it out in the output notes (e.g. "VLSR_G uses 999 as a fill value for missing data — not masked by the reader") rather than reporting it as real data.

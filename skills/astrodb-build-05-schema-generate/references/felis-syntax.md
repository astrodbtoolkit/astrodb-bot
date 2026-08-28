# Felis YAML Syntax Reference

## Top-level schema structure

```yaml
name: MySchema
"@id": "#MySchema"
description: "Brief description of what this schema covers"
version: "1.0"
tables:
  - ...  # table definitions
```

## Table structure

```yaml
- name: TableName
  "@id": "#TableName"
  description: "What this table contains"
  primaryKey:
    - "#TableName.primary_col"         # single-column PK
    # - "#TableName.col1"              # multi-column PK: list all
    # - "#TableName.col2"
  columns:
    - ...  # column definitions
  indexes:
    - name: PK_TableName
      "@id": "#PK_TableName"
      description: Primary key for TableName
      columns:
        - "#TableName.primary_col"
  constraints:
    - ...  # optional FK constraints
```

## Column structure

```yaml
- name: column_name
  "@id": "#TableName.column_name"
  datatype: double           # see datatype table below
  description: "What this column contains"
  nullable: false            # omit if nullable (defaults to true)
  length: 30                 # required for string datatype only
  fits:tunit: deg            # physical units (use FITS unit strings)
  ivoa:ucd: "pos.eq.ra;meta.main"  # IVOA UCD if known
```

## Felis datatypes

| Felis datatype | Use for |
|---|---|
| `string` | Text; always requires `length` |
| `double` | 64-bit float (most astronomical values) |
| `float` | 32-bit float |
| `long` | 64-bit integer |
| `int` | 32-bit integer |
| `short` | 16-bit integer |
| `byte` | 8-bit integer |
| `boolean` | True/False |
| `timestamp` | Date/time (ISO 8601) |
| `binary` | Raw bytes |

## Foreign key constraint structure

```yaml
constraints:
  - name: TableName_col_OtherTable_col
    "@type": "ForeignKey"
    "@id": "#FK_TableName_col_OtherTable_col"
    description: "Link TableName.col to OtherTable"
    columns:
      - "#TableName.col"
    referencedColumns:
      - "#OtherTable.col"
```

## Common standard AstroDB foreign keys

These FK patterns appear in nearly every data table:

```yaml
# Link 'source' to Sources table
- name: TableName_source_Sources_source
  "@type": "ForeignKey"
  "@id": "#FK_TableName_source_Sources_source"
  description: Link source to Sources table
  columns:
    - "#TableName.source"
  referencedColumns:
    - "#Sources.source"

# Link 'reference' to Publications table
- name: TableName_reference_Publications_reference
  "@type": "ForeignKey"
  "@id": "#FK_TableName_reference_Publications_reference"
  description: Link reference to Publications table
  columns:
    - "#TableName.reference"
  referencedColumns:
    - "#Publications.reference"

# Link 'telescope' to Telescopes table
- name: TableName_telescope_Telescopes_telescope
  "@type": "ForeignKey"
  "@id": "#FK_TableName_telescope_Telescopes_telescope"
  description: Link telescope to Telescopes table
  columns:
    - "#TableName.telescope"
  referencedColumns:
    - "#Telescopes.telescope"
```

## Common IVOA UCDs for astronomical fields

| Field type | UCD |
|---|---|
| RA (primary) | `pos.eq.ra;meta.main` |
| Dec (primary) | `pos.eq.dec;meta.main` |
| RA (other) | `pos.eq.ra` |
| Dec (other) | `pos.eq.dec` |
| Parallax | `pos.parallax.trig` |
| Proper motion RA | `pos.pm;pos.eq.ra` |
| Proper motion Dec | `pos.pm;pos.eq.dec` |
| Radial velocity | `spect.dopplerVeloc.opt` |
| Magnitude | `phot.mag` |
| Spectral type | `src.spType` |
| Object name | `meta.id;meta.main` |
| Reference | `meta.ref` |
| Uncertainty (generic) | `stat.error` |

## Common FITS unit strings

| Unit | FITS string |
|---|---|
| Degrees | `deg` |
| Hours | `h` |
| Mas/yr | `mas/yr` |
| Mas | `mas` |
| Km/s | `km/s` |
| Magnitude (AB) | `mag` |
| Solar masses | `Msun` |
| Angstroms | `Angstrom` |
| Parsecs | `pc` |
| Years | `yr` |

## Minimal complete example

```yaml
name: Parallaxes2024
"@id": "#Parallaxes2024"
description: "Trigonometric parallaxes from the 2024 survey"
version: "1.0"
tables:
  - name: Sources
    "@id": "#Sources"
    description: Unique astronomical sources
    primaryKey:
      - "#Sources.source"
    columns:
      - name: source
        "@id": "#Sources.source"
        datatype: string
        length: 100
        description: Source identifier
        ivoa:ucd: meta.id;meta.main
        nullable: false
      - name: ra
        "@id": "#Sources.ra"
        datatype: double
        description: Right ascension (J2000)
        fits:tunit: deg
        ivoa:ucd: pos.eq.ra;meta.main
      - name: dec
        "@id": "#Sources.dec"
        datatype: double
        description: Declination (J2000)
        fits:tunit: deg
        ivoa:ucd: pos.eq.dec;meta.main
    indexes:
      - name: PK_Sources
        "@id": "#PK_Sources"
        description: Primary key for Sources
        columns:
          - "#Sources.source"

  - name: Parallaxes
    "@id": "#Parallaxes"
    description: Trigonometric parallax measurements
    primaryKey:
      - "#Parallaxes.source"
      - "#Parallaxes.reference"
    columns:
      - name: source
        "@id": "#Parallaxes.source"
        datatype: string
        length: 100
        description: Source identifier; links to Sources table
        nullable: false
      - name: parallax
        "@id": "#Parallaxes.parallax"
        datatype: double
        description: Trigonometric parallax
        fits:tunit: mas
        ivoa:ucd: pos.parallax.trig
      - name: parallax_error
        "@id": "#Parallaxes.parallax_error"
        datatype: double
        description: Parallax uncertainty (1-sigma)
        fits:tunit: mas
        ivoa:ucd: stat.error;pos.parallax.trig
      - name: reference
        "@id": "#Parallaxes.reference"
        datatype: string
        length: 30
        description: Publication reference; links to Publications table
        nullable: false
    indexes:
      - name: PK_Parallaxes
        "@id": "#PK_Parallaxes"
        description: Primary key for Parallaxes
        columns:
          - "#Parallaxes.source"
          - "#Parallaxes.reference"
    constraints:
      - name: Parallaxes_source_Sources_source
        "@type": "ForeignKey"
        "@id": "#FK_Parallaxes_source_Sources_source"
        description: Link source to Sources table
        columns:
          - "#Parallaxes.source"
        referencedColumns:
          - "#Sources.source"
      - name: Parallaxes_reference_Publications_reference
        "@type": "ForeignKey"
        "@id": "#FK_Parallaxes_reference_Publications_reference"
        description: Link reference to Publications table
        columns:
          - "#Parallaxes.reference"
        referencedColumns:
          - "#Publications.reference"
```

## Tips

- The `@id` for a schema element must be unique across the entire file — use `#TableName.colName`
  format consistently.
- Felis uses `nullable: true` as the default (i.e., omitting `nullable` means it's nullable).
  Only write `nullable: false` when you mean it.
- String `length` values should be generous — it's easier to make them longer later than shorter.
  Typical choices: 30 (short IDs), 50 (names), 100 (descriptions), 256 (long text), 1000 (notes).
- For uncertainty columns, append `_error`, `_error_upper`, or `_error_lower` to the parent
  column name and use the UCD `stat.error;<parent_ucd>`.

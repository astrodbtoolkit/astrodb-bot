# Units Inference

When a column has no units in the file metadata, infer them from the column name and description using the table below. Use `astropy.units` string conventions.

| Clue in name or description | Unit |
|-----------------------------|------|
| velocity, `km/s`, `(km/s)` | `km / s` |
| magnitude, `mag`, surface brightness | `mag` or `mag / arcsec2` |
| half-light radius, `arcmin` | `arcmin` |
| `arcsec` | `arcsec` |
| proper motion, `mas/yr` | `mas / yr` |
| metallicity, `dex`, `[Fe/H]` | `dex` |
| solar masses, `M_sun`, `M☉` | `solMass` (or `1e+06 solMass` if scaled) |
| distance modulus | `mag` |
| reddening, `E(B-V)` | `mag` |
| position angle | `deg` |
| right ascension, declination (if decimal degrees) | `deg` |
| flag, index, coded integer values | `—` |
| dimensionless quantities (e.g. ellipticity, ratios) | `dimensionless_unscaled` |

If you can't infer units confidently, fall back to inheriting from the base column: for uncertainty columns (ending in `+` or `-`), look up the already-resolved unit of the base column. Track resolved units as you process each column so they're available when processing the corresponding uncertainty columns.

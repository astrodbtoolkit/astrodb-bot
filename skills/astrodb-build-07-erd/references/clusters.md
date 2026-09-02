# Table clusters for split diagrams

`--split` and `--cluster` group tables into three sets. The names and membership match the
**Lookup / Main / Data** grouping used in
`astrodb-build-03-schema-match/references/schema.md` and in the banner comments of the
template's own `schema.yaml`, so a reader who has seen one recognizes the other.

## The astrodb-template-db taxonomy

**Lookup tables** — controlled vocabularies and reference lists. Loaded first, referenced by
everything else, and they reference nothing themselves.

> Publications, Telescopes, Instruments, PhotometryFilters, Versions, RegimeList, AssociationList,
> ParameterList, CompanionList, SourceTypeList

**Main tables** — the objects the database is about, and the tables that identify them.

> Sources, Names, Positions

**Data tables** — measurements and derived properties, each hanging off `Sources`.

> Photometry, Parallaxes, RadialVelocities, ProperMotions, ModeledParameters, RotationalParameters,
> Morphology, Spectra, CompanionParameters, CompanionRelationships, Associations, SourceTypes

These are hardcoded in `scripts/felis_to_mermaid.py` as `KNOWN_CLUSTERS`. A user schema that keeps
the template's table names inherits the grouping for free.

## Fallback for custom schemas

Any table whose name is not in the list above is placed structurally, using only the foreign key
graph:

1. **Lookup** — a table with out-degree 0 (it references nothing) that is referenced by two or more
   other tables.
2. **Main** — the hub: whatever remaining table the most other tables point at.
3. **Data** — anything that references the hub.
4. **Main** — everything left over.

This is a heuristic, not a fact about the user's data.

## Always confirm the grouping

Run:

```bash
uv run python <skill-dir>/scripts/felis_to_mermaid.py --schema schema.yaml --print-clusters
```

and show the result to the user before generating split diagrams. Per the **"skills must ask, not
assume"** rule in `references/astrodb-instructions.md`, a heuristic grouping is exactly the kind of
silent default that needs an explicit answer. If they want a different split, use `--tables` to
build the diagrams by hand and record the chosen grouping in `build-workflow.md`.

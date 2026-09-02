# What a good AstroDB ERD looks like

House style for diagrams this skill produces. The goal is a diagram someone reads in the repo, not
a poster.

## The shape of the deliverable

**One overview plus per-cluster detail**, not a single diagram of everything.

- **Overview** — every table, `--detail keys` (PK/FK/UK columns only), every relationship. This is
  the map: which tables exist and how they connect. It is what the README links to.
- **Cluster diagrams** — one per group (`lookup`, `main`, `data`; see `clusters.md`), at
  `--detail full`, each showing the tables outside the cluster it touches as keys-only context
  boxes so the edges have somewhere to land.

The template schema has 25 tables and 171 columns. Rendering all 171 attribute rows in one image is
unreadable in *any* tool — this is not a Mermaid limitation, and switching renderers does not fix
it. **Splitting the diagram is the single biggest quality lever available**, which is why
`--split` exists and why `--detail keys` is the default.

## Conventions

- **Table order follows the schema file**, which is already grouped Lookup -> Main -> Data. Do not
  re-sort alphabetically; the semantic grouping is information.
- **Column order within a table**: primary key columns first in `primaryKey` order, then foreign
  keys, then schema order. Deterministic ordering keeps diffs readable across regenerations.
- **Edge labels are the foreign key column name(s)** — `"source"`, `"reference"`,
  `"instrument, mode, telescope"`. Not a prose description of the relationship.
- **Solid lines mean identifying relationships** (the foreign key is part of the child's primary
  key). In AstroDB that distinction is real and worth preserving: `Names` cannot exist without its
  `Sources` row, while `Sources.reference` merely points at a publication.
- **Comments are off by default.** They triple the character count and most of what they add is
  already in `docs/schema/*.md`. Turn them on for a cluster diagram if the user wants a
  self-contained reference.

## What not to do

- **Do not commit a PNG.** It cannot be diffed, it goes stale silently, it bloats the repo, and it
  breaks the moment someone moves the file — which is exactly how the template repo ended up with a
  README pointing at a deleted image.
- **Do not put the whole diagram inline in the README.** Link to `docs/figures/schema_erd.md`
  instead; GitHub renders it when the reader clicks through. An inline block means every schema
  change dirties the README.
- **Do not hand-edit generated output.** The markers say so for a reason — the next regeneration
  overwrites it. Fix `schema.yaml` and re-run.
- **Do not require a build step to read the diagram.** If someone has to install something to see
  the schema, the diagram has failed at its job.

## Relationship to the rest of the docs

An ERD answers "how do these tables connect?". It does not replace `docs/schema/*.md`, which answers
"what exactly is in this column, in what unit, with which UCD?". Both should exist; keep the ERD
focused on structure and leave the per-column detail to the markdown tables.

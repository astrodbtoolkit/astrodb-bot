# Mermaid erDiagram syntax, and the limits that bite

Reference for `scripts/felis_to_mermaid.py` and for hand-editing its output.

## Where GitHub renders it

GitHub renders a fenced ` ```mermaid ` block natively in **README and other markdown files, issues,
pull requests, and discussions**, in public and private repos alike. The fence must be lowercase
`mermaid`.

It does **not** render everywhere:

- **GitHub wikis** — documented as supported but long reported as broken
  ([github/docs#15727](https://github.com/github/docs/issues/15727)). Verify before relying on it.
- **Sphinx / ReadTheDocs** — needs `sphinxcontrib-mermaid`. GitHub's native rendering does not carry
  over, so `astrodb_utils`-style Sphinx docs need either that extension or a pre-rendered SVG.
- **PyPI project pages, npm, most static site generators, PDF exports** — the block degrades to a
  plain code fence.

## Relationship lines

```
<parent> <left><line><right> <child> : "<label>"
```

| Marker | Meaning |
|---|---|
| `\|o` / `o\|` | Zero or one |
| `\|\|` | Exactly one |
| `}o` / `o{` | Zero or more |
| `}\|` / `\|{` | One or more |

Line style: `--` solid (identifying — the child cannot be identified without the parent), `..`
dashed (non-identifying).

### How this skill maps Felis to those markers

For a foreign key on child columns `C` referencing parent table `P`:

```
left marker (how many parents, seen from the child):
    every column in C has nullable: false   ->  ||   exactly one
    any column in C is nullable             ->  |o   zero or one

right marker (how many children, seen from the parent):
    C is exactly the child's whole primaryKey  ->  ||   exactly one (1:1)
    C is one column with a unique constraint   ->  |o   zero or one
    otherwise                                  ->  o{   zero or more

line style:
    C overlaps the child's primaryKey  ->  --  solid
    otherwise                          ->  ..  dashed

label: the child column name(s), comma-joined. A composite foreign key is ONE edge.
```

**Felis omits `nullable` when it is true**, so read it as `col.get("nullable", True) is not False` —
the same idiom `astrodb-template-db/scripts/build_schema_docs.py` uses. Treating a missing key as
"required" inverts every optional relationship in the diagram.

Worked examples from the template schema:

```
Sources ||--o{ Names : "source"              Names.source is non-null and part of Names' PK
Publications ||..o{ Sources : "reference"    non-null, but not in Sources' PK -> dashed
PhotometryFilters |o--o{ Photometry : "band" band is nullable -> |o; it is in the PK -> solid
Instruments ||--o{ Spectra : "instrument, mode, telescope"   composite FK, one edge
```

## Attributes

```
Photometry {
    string source PK, FK "Unique identifier for a source"
    double magnitude
}
```

- Type and name are single tokens. A type with punctuation must be sanitized (`some-odd~type` ->
  `some_odd_type`); the emitter does this.
- Key markers are `PK`, `FK`, `UK`, in that order. A column can carry several, but they **must be
  comma-separated** — `string source PK, FK`. Space-separating them is a parse error, and it is not
  one you will notice by eye: the emitter gets this right, so do not "tidy" it away when hand-editing.
- The trailing comment is double-quoted. **A `"` inside it terminates the comment and a newline
  breaks the parser** — collapse whitespace, strip quotes, and truncate. The emitter caps comments
  at 60 characters.
- An entity with no attributes still needs its `{ }` block; an empty one is legal.

## The size limit — the one that fails silently

Mermaid's `maxTextSize` defaults to **50,000 characters, and it is not configurable on GitHub.**
Past it, GitHub replaces the whole diagram with "Maximum text size in diagram exceeded" — no error,
no partial render, just a missing diagram that looks like your fault.

Measured on the 25-table astrodb-template-db schema:

| Mode | Characters |
|---|---|
| `--detail keys` (default) | ~4,400 |
| `--detail required` | ~4,700 |
| `--detail full` | ~7,700 |
| `--detail full --comments` | ~15,000 |

So the template is comfortable at any setting, but a schema a few times larger with descriptions on
every column is not. `felis_to_mermaid.py` therefore enforces a **45,000-character budget** (10%
headroom) and **exits 1** rather than writing a file that would silently fail. Raise it with
`--max-chars` only if you know the diagram is not going on GitHub.

## What you cannot control

- **No layout control on GitHub.** Only the dagre engine is available; the much better ELK layout
  needs a host that registers `@mermaid-js/layout-elk`, and GitHub does not. Diagrams grow wide, and
  `direction` is ignored for ER diagrams.
- **No dual-perspective labels.** Mermaid supports one label per relationship, not one per end.
- **Styling is partly overridden** by GitHub's theme adaptation, so branding colors will not survive.
- **Subgraphs** (useful for grouping entities) need Mermaid v11.17+; GitHub's bundled version may
  lag. Put `info` in a mermaid block on GitHub to see the version it runs.

Because layout cannot be steered, the way to improve a large diagram is to **draw less of it at
once** — see `diagram-style.md`.

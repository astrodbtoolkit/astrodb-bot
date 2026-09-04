# ERD backends: what exists, and what this skill uses

This skill's default backend is **built in and needs nothing installed**. Everything else on this
page is optional. **Graphviz is never required.** If a user asks "why not X?", the answer for X is
below — quote it rather than re-deriving it.

## The tiers

| | built-in Mermaid | d2 | mermaid-cli (`mmdc`) | graphviz (`dot`) | eralchemy 1.7 | paracelsus | mermaidx |
|---|---|---|---|---|---|---|---|
| New dependencies | **none** | Go binary | Node | system package | pip (+ system graphviz for raster) | pip | pip |
| GitHub renders it inline | **yes** | no | n/a (image) | no | yes, with `-m mermaid_er` | yes | n/a (image) |
| Diffs in git | **yes** | yes | no | no | yes | yes | no |
| Layout control | none | **best** | none | good | some | none | none |
| Any cloner can regenerate it | **yes** | no | no | no | no | yes | yes |
| This skill's stance | **default** | use if on PATH | use if on PATH | use if on PATH, never recommend | documented | documented | documented |

### Tier 0 — built-in Mermaid (the default)

`scripts/felis_to_mermaid.py` walks `schema.yaml` with `yaml.safe_load` and emits an `erDiagram`.
Its only dependency is pyyaml, which every AstroDB project already has.

Chosen as the default because zero new dependencies is not a tiebreaker here — it is the
requirement. Skill scripts run in the *user's* virtualenv, where we control nothing. A backend that
can be absent turns "make me a diagram" into "first install this", which is exactly the outcome
[PR #84](https://github.com/astrodbtoolkit/astrodb-bot/pull/84) was rejected for.

It also keeps Felis-specific information that a SQLAlchemy `MetaData` round-trip throws away
(`description`, `fits:tunit`, `ivoa:ucd`), and it is the only option with a character-budget guard
against Mermaid's silent size limit.

### Tier 1 — renderers, used only if already on `PATH`

Offer these when detected; **never ask the user to install one.** Preference order `d2 > mmdc > dot`.

- **d2** — single Go binary. Purpose-built `sql_table` shape, abbreviates constraints to PK/FK/UNQ,
  and with the ELK or TALA layout engine **connections point at the exact column row** rather than
  the table box. With 42 foreign keys that is a real readability win, and it is the best-looking
  output of anything here. GitHub does not render `.d2`, so you commit an SVG.
- **mermaid-cli (`mmdc`)** — renders our `.mmd` to SVG/PNG. Needs Node. Also the cheapest real
  parse gate: `mmdc -i out.mmd -o /tmp/out.svg` fails loudly on a syntax error.
- **graphviz (`dot`)** — best-in-class layered layout, and `rankdir=LR` / `ranksep` / `splines=ortho`
  give genuine control. **Listed, never recommended.** It is a system package, its output is a
  binary blob in git, GitHub will not render it inline, and requiring it is the thing this skill
  exists to avoid. Use it only when the user already has it and asks for it.

### Tier 2 — documented, not offered as an install

- **eralchemy 1.7** (`uv add "eralchemy[graphviz]"`) — Apache-2.0, actively maintained, consumes a
  SQLAlchemy `MetaData` or a database URL and emits PNG/PDF/SVG/`.md`/`.er` **and Mermaid**
  (`-m mermaid_er`). A perfectly good tool; it is Tier 2 only because it can be absent.
  **`eralchemy2` is deprecated** — it was merged back into upstream `eralchemy` at v1.5.0, and the
  current release is v1.7.0. If a user has `eralchemy2` installed, say so and point them at
  `eralchemy`. `astrodb-template-db/scripts/make_schema_erd.py` still imports the dead fork.
- **paracelsus** — pip-only, MIT. SQLAlchemy `MetaData` to Mermaid or DOT, with `inject` (rewrite a
  marked block inside a markdown file) and `--check` (fail CI when the committed diagram is stale).
  Those two ideas are good enough that this skill copies them; the dependency itself is not needed,
  and its model-module-import design would need a shim to accept a Felis-built `MetaData`.
- **mermaidx** — renders Mermaid to SVG/PNG/PDF with no browser, no Node, and no system package
  (embedded QuickJS plus resvg, prebuilt wheels). Genuinely unique capability. It is a young project
  with a small user base, so this skill lists it without endorsing it — mention it if the user wants
  a committed image and has none of `d2`/`mmdc`/`dot`, and let them judge the trade-off.
- **sqlalchemy-schemadisplay** — pydot plus system graphviz, but it hands back a `pydot.Dot` object,
  so you can set `rankdir` and `restrict_tables` yourself. Useful if someone wants a tuned poster.

## Surveyed and not chosen

| Tool | Why not |
|---|---|
| **PlantUML** | Needs Java; GitHub does not render it inline, and the usual workaround posts your schema to a third-party rendering proxy; crow's-foot markers degrade at angles; it shells out to graphviz anyway. Worst of both worlds here. |
| **tbls** | Go binary. Genuinely good — emits GFM markdown with inlined Mermaid ER, and its "viewpoints" produce per-subsystem diagrams. Rejected only because it reads a live database, not a Felis YAML, and it is another binary. |
| **SchemaSpy** | Java plus graphviz plus a JDBC driver. Produces an excellent interactive HTML site and even detects undeclared foreign keys, but the output is a website, not a diffable artifact. |
| **SchemaCrawler** | Java. Exports Mermaid, PlantUML, DBML and more, with good CI/linting support. Ruled out by the Java dependency. |
| **Atlas** | Go binary. `atlas schema inspect -u "sqlite://db.sqlite" --format '{{ mermaid . }}'` is a real one-liner against a built database, but it needs the `.sqlite` to exist and `--web` uploads the schema to their cloud. |
| **DBML / dbdiagram.io** | Node CLI; SQLite is not among the officially supported inputs; rendering is essentially web-only. |
| **BurntSushi/erd** | Dormant since 2024-09. Its `.er` format lives on inside eralchemy. |
| **Liam ERD** | Hosted interactive viewer, handles 100+ tables well, but it is a website rather than a committable artifact. |
| **Felis itself** | Has no diagram export at all — `felis` only does `validate`, `create`, `dump`, `diff`, and the TAP_SCHEMA commands. |

## Note for the astronomy context

LSST's `sdm_schemas`, SDSS SkyServer, and the Gaia archive all publish searchable table/column
browsers and no entity relationship diagram. An AstroDB database that ships one is already better
documented than the field's norm — worth telling the user.

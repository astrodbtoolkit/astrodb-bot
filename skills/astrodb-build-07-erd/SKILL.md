---
name: astrodb-build-07-erd
description: Generate an entity relationship diagram (ERD) from an AstroDB Felis schema.yaml, choosing a diagram backend that matches what the user already has installed. Use this skill whenever the user wants an ERD, entity relationship diagram, schema diagram, database diagram, table relationship map, or asks to "draw the schema", "visualize the schema", "make a diagram of my database", "show how the tables link", "regenerate the ERD", "update the schema diagram", or "add a diagram to the docs". Also trigger after astrodb-build-06-create-db completes, and whenever schema.yaml has changed and the committed diagram is now stale. Works on any Felis schema.yaml — it does not require that the database has been created, and it never requires graphviz or any other system package.
compatibility: python, pyyaml; optional: d2, mermaid-cli, graphviz
metadata:
  authors: ["Claude"]
---

# Generate an Entity Relationship Diagram

Turn a Felis `schema.yaml` into an entity relationship diagram, using whatever diagram tooling the
user already has. The default backend ships with this skill and needs nothing installed, so this
skill always produces a diagram — backend detection decides whether the output can be *upgraded*,
never whether it can be produced at all.

**Never make the user install a system package to get a diagram.** Graphviz in particular is
detected and listed, but never recommended: needing it is the problem this skill exists to solve.

## Step 0: Read context documents

Read `references/astrodb-instructions.md` (shared conventions) and
`references/astrodb-build-instructions.md` (build-specific conventions) — together they cover the
artifact folder, decision log, directions document, and completion-checklist conventions this skill
follows.

Then record this skill's checklist per the **completion-checklist convention**: add a
`## astrodb-build-07-erd` section holding the items from `## Completion Checklist` (bottom of this
file) to `astrodb-build-artifacts/checklists.md`, and tick them with evidence as you go.

```bash
mkdir -p astrodb-build-artifacts
```

## Prerequisites

A Felis `schema.yaml`. That is all. The database does not need to exist — the diagram is built from
the schema, not from a `.sqlite` file — so this skill works equally well straight after
`astrodb-build-05-schema-generate`, after `astrodb-build-06-create-db`, or years later on an
established database repo.

## Step 1: Locate the schema.yaml

Check (in order), stopping at the first hit:

1. A path the user explicitly stated in the conversation
2. `schema.yaml` in the current working directory
3. `astrodb-build-artifacts/<schema-name>-schema.yaml` — the output of `astrodb-build-05-schema-generate`

If you cannot find one, ask the user for the path before continuing.

Read the schema's top-level `name:` field — it names the output files
(`<schema-name>-erd.mmd`, and so on).

## Step 2: Detect the available backends

Run the bundled probe. It uses `importlib.util.find_spec` and `shutil.which`, so it never imports
anything, never installs anything, and cannot fail because a system binary is missing:

```bash
uv run python <skill-dir>/scripts/detect_erd_backends.py
```

Save its output to `astrodb-build-artifacts/erd-backends.md` so the choice stays auditable:

```bash
uv run python <skill-dir>/scripts/detect_erd_backends.py > astrodb-build-artifacts/erd-backends.md
```

The built-in Mermaid backend needs only pyyaml, so the recommendation is essentially always
`builtin-mermaid`. What the probe actually decides is whether a *rendered image* is also possible
(`d2`, `mmdc`, or `dot` already on `PATH`).

## Step 3: Choose the backend

**First check whether the choice is already made.** Read the directions document and
`astrodb-build-artifacts/build-workflow.md`; if a previous run recorded a backend, reuse it and say
so rather than asking again.

Otherwise present the probe result and ask **once**:

> I checked what's on this machine for drawing diagrams:
>
> - **Mermaid (built in)** — available now, no installs. It produces a text diagram that GitHub
>   renders inline in markdown files, issues, and pull requests, and that diffs cleanly in git.
> - *(list any renderer actually found on PATH, and what it adds — a committed SVG)*
> - *(if nothing else was found)* Nothing else found — that's fine, nothing else is required.
>
> I'd suggest **Mermaid, committed as text**: it needs no dependencies, so anyone who clones your
> repo can regenerate it, and GitHub draws it for you.
>
> 1. Mermaid text only (recommended)
> 2. Mermaid text **plus** a rendered image using `<the backend found on PATH>`
> 3. Tell me more about the trade-offs

For option 3, walk them through `references/backends.md` — it has a verdict on every tool they are
likely to name, including why PlantUML, tbls, SchemaSpy, and the rest were not chosen.

Rules for this step:

- **Never install anything.** If the user wants a backend that is not present, print the exact
  command and let them run it. Do not run `uv add`, `pip install`, `brew`, or `apt` yourself.
- **Never recommend graphviz first.** Offer it only when `dot` is already on `PATH`, and say plainly
  that it is not needed.
- **If `eralchemy2` is detected**, tell the user it is deprecated — it was merged into upstream
  `eralchemy` at v1.5.0 and the current release is v1.7.0.
- Record the choice in `build-workflow.md` so a later run does not re-ask.

## Step 4: Decide the scope, and confirm the clustering

Count the tables:

```bash
uv run python <skill-dir>/scripts/felis_to_mermaid.py --schema <schema-path> --stats > /dev/null
```

**Up to about 10 tables:** one diagram is fine. Use `--detail full` and skip to Step 5.

**More than that:** propose an overview plus per-cluster diagrams. A single diagram of every column
in a 25-table schema is unreadable in any tool — see `references/diagram-style.md`. Show the
proposed grouping first:

```bash
uv run python <skill-dir>/scripts/felis_to_mermaid.py --schema <schema-path> --print-clusters
```

and ask the user to confirm it:

> I'd split the diagram into an overview (all tables, key columns only) plus three detailed views:
>
> - **Lookup tables:** <list>
> - **Main tables:** <list>
> - **Data tables:** <list>
>
> Does that grouping match how you think about this database?

Table names from the astrodb-template-db schema use the documented Lookup/Main/Data taxonomy; any
other name is placed by a structural heuristic, which is a guess and needs confirming. See
`references/clusters.md`. If they want a different split, build the diagrams with `--tables` and
record the grouping in `build-workflow.md`.

## Step 5: Generate the diagrams

Write to the artifact directory first. Step 7 puts the diagram in the repo itself; keeping a copy
here means the decision log, the backend report, and the diagram it produced all sit together.

Single diagram:

```bash
uv run python <skill-dir>/scripts/felis_to_mermaid.py \
  --schema <schema-path> \
  --detail full --format md --title "<schema-name> schema" \
  --out astrodb-build-artifacts/<schema-name>-erd.md --stats
```

Overview plus clusters:

```bash
uv run python <skill-dir>/scripts/felis_to_mermaid.py \
  --schema <schema-path> --split astrodb-build-artifacts/<schema-name>-erd \
  --detail full --format md --stats
```

This writes flat files in `astrodb-build-artifacts/` — no subdirectory:
`<schema-name>-erd-overview.md`, `<schema-name>-erd-lookup.md`, `<schema-name>-erd-main.md`,
`<schema-name>-erd-data.md` (skipping any empty cluster).

Useful flags — the full list is in the script's `--help`:

| Flag | Effect |
|---|---|
| `--detail keys\|required\|full` | PK/FK/UK only (default), plus non-nullable, or every column |
| `--comments` | Include Felis descriptions. Off by default — it roughly doubles the size |
| `--tables A,B` | Just these tables, plus their direct neighbours as context |
| `--max-chars N` | Character budget, default 45000 |

**If the script exits 1 with a size error**, do not raise `--max-chars` to make it go away. The
budget exists because GitHub silently refuses to draw a diagram over 50,000 characters — a raised
budget produces a file that looks fine locally and is simply missing on GitHub. Take one of the
remedies it names: drop `--comments`, lower `--detail`, or `--split`.

If the user chose a renderer in Step 3, produce the image too, e.g.:

```bash
mmdc -i astrodb-build-artifacts/<schema-name>-erd.mmd -o astrodb-build-artifacts/<schema-name>-erd.svg
```

## Step 6: Verify the diagram is real

Do not report success on the script's exit code alone.

1. **Confirm the file exists and starts with `erDiagram`:**

   ```bash
   head -6 astrodb-build-artifacts/<schema-name>-erd.md
   ```

2. **Sanity-check the content against the schema** — the relationship count from `--stats` should
   match the number of `"@type": "ForeignKey"` constraints:

   ```bash
   grep -c '"@type": "ForeignKey"' <schema-path>
   ```

   A mismatch means a foreign key points at a table that is not in the schema; investigate rather
   than shipping a diagram with missing edges.

3. **Parse-check it if you can.** This is worth the trouble: mermaid's grammar has corners that look
   fine to the eye and fail in the renderer, and GitHub gives no error when a diagram fails to draw.

   ```bash
   mmdc -i astrodb-build-artifacts/<schema-name>-erd.mmd -o /tmp/erd.svg
   ```

   If `mmdc` is not on `PATH` but `npx` is, offer this — it fetches mermaid-cli into the npx cache
   rather than installing into the project, but it is still a download, so **ask first**:

   ```bash
   npx -y @mermaid-js/mermaid-cli -i astrodb-build-artifacts/<schema-name>-erd.mmd -o /tmp/erd.svg
   ```

   If neither is available, or the user declines, say plainly that the diagram was generated but not
   parse-checked. Do not imply it was validated when it was not.

## Step 7: Add the diagram to the repo

Write the diagram to its home in the user's repo. This is the deliverable, not an extra — the same
way `astrodb-build-06-create-db` writes the `.sqlite` and `astrodb-build-01-setup` edits the README.

```bash
uv run python <skill-dir>/scripts/felis_to_mermaid.py \
  --schema <schema-path> --detail keys \
  --inject docs/figures/schema_erd.md --title "<schema-name> schema"
```

`--inject` rewrites only the block between the `<!-- ERD:BEGIN -->` and `<!-- ERD:END -->` markers,
creating the file with them if it does not exist, so regenerating later is idempotent and never
touches anything a user has written around it.

If you generated per-cluster diagrams in Step 5, copy the flat cluster files into `docs/schema/`
(e.g. `docs/schema/erd-overview.md`, `docs/schema/erd-lookup.md`, …) using the same
`--split docs/schema/erd` prefix pattern.

Then give `README.md` a Schema section, **only if it does not already have one** — never overwrite a
section the user wrote. Use the `Edit` tool, not `sed`, so the rest of the file stays intact. Put it
after the description:

```markdown
## Schema

See the [entity relationship diagram](docs/figures/schema_erd.md) — GitHub renders it inline.
```

**A link, not an inline diagram and not an image.** An inline block would dirty the README on every
schema change; an image link is what broke in the template repo in the first place.
`astrodb-build-01-setup` removed the template's ERD image and its README link when the repo was
cloned, because they described the template's schema rather than the user's — this puts a diagram of
*their* schema back.

Tell the user which files you changed. If they would rather not have the README section, remove it —
but do not stop to ask first, any more than the other build skills ask before writing their output.

## Step 8: Report

Tell the user:

- Which backend was used, and that nothing had to be installed (if that is true)
- Where the diagram files are
- The table, column, and relationship counts, and the character count against the 50,000 limit
- Which files in their repo were changed
- That the diagram regenerates with one command when `schema.yaml` changes:

  ```bash
  uv run python <skill-dir>/scripts/felis_to_mermaid.py \
    --schema schema.yaml --detail keys --inject docs/figures/schema_erd.md
  ```

  and that adding `--check` to that command reports whether the committed diagram is stale without
  writing anything — useful in CI, and it needs no token or secret.

## Troubleshooting

**The `Make ER diagram` GitHub Action fails on push.** A repo cloned from `astrodb-template-db`
still contains `.github/workflows/make_erd.yml` and `scripts/make_schema_erd.py`. That workflow runs
on every push to `main`, `apt install`s graphviz, and commits a PNG back using `secrets.GH_TOKEN`
plus `USER_LOGIN` and `USER_ID` — none of which are set in a fresh repo, so the push step fails.
This is unrelated to this skill and this skill does not modify `.github/`. The ways out, in the order
worth suggesting:

1. Delete `.github/workflows/make_erd.yml` and `scripts/make_schema_erd.py`, and regenerate the
   diagram with this skill when the schema changes.
2. Replace the workflow's body with a staleness check that needs no secrets at all —
   `felis_to_mermaid.py --inject docs/figures/schema_erd.md --check`.
3. Keep it and create the secrets. Note that the PAT is not actually necessary: the workflow already
   declares `permissions: contents: write`, so `${{ github.token }}` would work in place of
   `secrets.GH_TOKEN`.

Whichever they pick, changing files under `.github/` is their call — ask first.

**`scripts/make_schema_erd.py` fails with `ModuleNotFoundError: eralchemy2`.** That script imports a
deprecated package (merged into upstream `eralchemy` at v1.5.0; current v1.7.0) and needs system
graphviz on top. It is the template's old ERD path; this skill replaces it. Worth logging as a
`gotcha` against `astrodb-template-db`.

**The diagram renders as "Maximum text size in diagram exceeded" on GitHub.** The block is over
50,000 characters and GitHub's limit cannot be configured. Regenerate with `--split`, a lower
`--detail`, or without `--comments`.

**The diagram is a wide, tangled sprawl.** Expected past ~15 tables: GitHub only offers Mermaid's
dagre layout engine and ignores direction hints for ER diagrams. There is no flag that fixes this —
`--split` is the fix. See `references/diagram-style.md`.

**A foreign key is missing from the diagram.** The emitter skips a constraint whose
`referencedColumns` name a table that is not defined in the same schema file. Fix the schema (Felis
validation would also flag it) rather than the diagram.

**A relationship points the wrong way, or shows the wrong optionality.** Check the child column's
`nullable` flag and the child table's `primaryKey`. Felis omits `nullable` when it is true, so a
column with no `nullable` key is optional and correctly draws as `|o`. The full mapping is in
`references/mermaid-er-syntax.md`.

## Final Step: Update `build-workflow.md`

Follow the convention in `references/astrodb-build-instructions.md`. Append one new entry to
`astrodb-build-artifacts/build-workflow.md` (create it with the standard header if it doesn't exist
yet). Record: which backend was chosen and why, whether anything was installed, the clustering the
user confirmed (and any departure from the default taxonomy), the detail level used and why, whether
which files in the repo were written or left alone (an existing README Schema section, say), and any
size-budget problem and how it was resolved.

## Completion Checklist

Before telling the user the diagram is done, verify every item in your section of the workflow
checklist file and reproduce the evidence-annotated list here, per the **completion-checklist
convention** in `references/astrodb-build-instructions.md`.

- [ ] You located the schema.yaml (stating which of the three locations it came from) and read its top-level `name:`.
- [ ] `scripts/detect_erd_backends.py` was actually run and its output saved to `astrodb-build-artifacts/erd-backends.md` — you reported what was found rather than assuming.
- [ ] The backend was chosen with the user (or carried over from a recorded earlier choice, which you said out loud). **You installed nothing**, and you did not recommend graphviz unless `dot` was already present and the user asked for it.
- [ ] For a schema past ~10 tables, you proposed the overview-plus-clusters split and had the user confirm the grouping before generating — per the "skills must ask, not assume" rule.
- [ ] The diagram files were written to `astrodb-build-artifacts/`, and the character count is under the budget. If the script exited on the size guard, you took one of the remedies it named rather than raising `--max-chars`.
- [ ] You verified the output beyond the exit code: the file starts with `erDiagram`, and the relationship count matches the schema's `ForeignKey` constraint count. If a parse check was possible you ran it; if not, you said so rather than implying the diagram was validated.
- [ ] The diagram was written to `docs/figures/schema_erd.md` (and flat `docs/schema/erd-*.md` cluster files if you split it), and `README.md` has a Schema section **linking** to it — not an inline mermaid block, not an image link. An existing Schema section was left alone rather than overwritten.
- [ ] You reported the backend used, the file paths, the table/column/relationship and character counts, which repo files changed, and the one-line command to regenerate (and to `--check` for staleness in CI).
- [ ] A decision-log entry was appended to `astrodb-build-artifacts/build-workflow.md` (created with the standard header if absent), recording the non-obvious choices this skill made and why — per the decision-log convention in `references/astrodb-build-instructions.md`.
- [ ] Any problem with the skills themselves was logged in `gotchas.md`, following the problem-log convention in `references/astrodb-instructions.md` — or there was none worth logging.

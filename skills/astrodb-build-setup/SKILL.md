---
name: astrodb-build-setup
description: First step in creating a new AstroDB database — run this FIRST, before any other astrodb-* skill, whenever the user wants to start, create, or set up a new AstroDB (astronomical) database, or asks "what's the first step to making a new astrodb." It stands up the database repository — ask for a database name (and suggest the user give their new GitHub repo that same name), have the user create that repo from the astrodb-template (https://github.com/astrodbtoolkit/astrodb-template-db, via "Use this template") and give you its address, clone that repo, verify it has the expected template structure (a data/ directory, a database.toml, and a schema.yaml), and update database.toml with the new name. This step only stands up and names the empty scaffold — it does not touch data files or ingestion, which come later. Trigger on "start a new astrodb," "set up an astronomical database," or "what's the first step to a new astrodb." When beginning a brand-new AstroDB, use this skill first.
compatibility: git, python
metadata:
  authors: ["Claude"]
---

# AstroDB Setup

Read `references/astrodb-directions.md` before starting — it documents the `workflow.md` convention
that this skill initializes and all subsequent skills maintain, plus the artifact-folder and
completion-checklist conventions this skill follows.

This is the **first step** in standing up a new AstroDB, and its whole job is to get a correctly
structured, named database repository onto the user's machine — nothing more. It deliberately stops
before any data is involved; bringing in a data table to parse and ingest is the *next* step, handled
by the other astrodb skills. Keeping this step small means the user finishes it holding a clean, valid,
empty database scaffold that is theirs to build on.

Every AstroDB starts from the **astrodb-template-db**, which is published as a GitHub *template*
repository. The right way to begin is not to clone that template directly — it's for the user to create
their *own* repository from it (so they own the history and can push their work), and then we clone
that. Work through the steps in order.

## The directions document: read it before you ask the user anything

A **directions document** is where the user records decisions about their database up front —
its name and description, how the license should read, and (for later skills) dataset-specific
notes like columns to skip and known issues. `references/directions_example.md` shows the shape.

Several steps below ask the user a question. **Every one of those questions should first be looked
for in the directions document.** Ask only for what the document doesn't answer. This matters because
a user who has written a directions document has already answered you — being asked again for
something they wrote down reads as though you never opened it, and it's the fastest way to make the
document feel pointless. The whole reason it exists is so the decisions live in one durable place
instead of being re-elicited in conversation every run.

So read it at the earliest moment you have access to one:

- **The user gave you a path** (in their opening message, say) — read it right away, before Step 1.
  This is the only source available before the repo exists, and it may already name the database.
- **You're inside a repo** (Path B, or after cloning in Step 2) — check
  `astrodb-build-artifacts/directions.md`, where a prior run would have persisted one.
- **Neither** — proceed and ask normally. The document is optional; never block on it.

When you find one, tell the user what you took from it rather than silently acting on it, so they can
correct a stale note before it propagates:

> I read your directions document — using "<name>" as the database name and the description from its
> Database section. I'll still need the license details, which it doesn't cover.

Treat it as the user's own words with the authority that implies, but not as a licence to invent: if
its Database section is missing or says nothing about, say, the license, that's an unanswered question
and you should ask it. Never infer a person's name or a description from surrounding data.

## Step 0: Decide which path you're on (do this first, explicitly)

Before anything else, consciously decide whether you still need to stand up a repo, or you are **already
inside one**. Do not drift past this — if you skip it, you will wrongly treat an already-cloned repo as
"mostly done" and skip the personalization checklist below (README, LICENSE, `db_name`). That is the bug
this step prevents.

Look at the current working directory:

```bash
# Is the current directory already a template-db repo, and has it been personalized yet?
for p in data database.toml schema.yaml; do [ -e "$p" ] && echo "✓ $p" || echo "✗ $p"; done
grep '^db_name' database.toml 2>/dev/null   # still "astrodb-template" => not yet personalized
git remote -v 2>/dev/null | grep '^origin'  # secondary signal only
```

Now branch on **unpersonalized state**, not merely on structure being present:

- **Path A — fresh start (default).** The current directory is *not* a cloned template DB (no
  `database.toml`/`schema.yaml`/`data/` here). You need to stand the repo up: go to **Step 1** and work
  through 1 → 9 in order.

- **Path B — already inside a cloned template repo.** The current directory already has the template
  structure (`data/`, `database.toml`, `schema.yaml`) **and** it is still unpersonalized —
  `db_name` in `database.toml` still reads `astrodb-template`, and/or the README still has the template
  title. The user cloned it themselves (their own repo, or the template directly) and started Claude
  inside it. **Skip the create-and-clone work in Steps 1–3** — you already have the repo — but do **not**
  skip anything else. Run the Step 3 structure verification against the current directory (`<repo-dir>` is
  `.`), then continue from **Step 4** through Step 9. You still need a database name: if the user gave one,
  use it; if not, ask for it (Step 1's naming prompt) before setting `db_name` in Step 5.

- **Don't run setup — already personalized.** If `db_name` is already something other than
  `astrodb-template` *and* the README no longer has the template title, this repo has already been set up.
  Every downstream astrodb skill also runs inside a repo with this same structure, so do **not** re-run
  setup. Tell the user setup already appears complete and point them at the next step (parse a data table)
  instead.

Whichever path you take, you must still satisfy the **full Completion Checklist** at the bottom before
reporting setup done — the checklist is identical for Path A and Path B.

## Step 1: Ask for a database name, then have the user create their repo from the template

The database name becomes `db_name` in `database.toml` and names the eventual SQLite file. If a
directions document already names the database, use that name and skip the question — you still need
the repo URL, so ask only for that.

Otherwise ask what they want to call it. Suggest they reuse that same name for the GitHub repo they're
about to create: picking it now is the only time it's free, since renaming a repo after the fact is just
extra busywork.

> What should I name the database? (e.g. `BdSurvey`.) I'd suggest using the same name for your GitHub
> repo when you create it below, so the two stay easy to match up later.
>
> To create the repo:
> 1. Go to https://github.com/astrodbtoolkit/astrodb-template-db
> 2. Click **Use this template → Create a new repository**, name it (matching the database name above
>    is a nice touch, but not required), and create it.
> 3. Paste the new repo's URL here (e.g. `https://github.com/<you>/<your-db>`).

Why a template repo: "Use this template" hands the user a brand-new repository that already contains the
full AstroDB structure (`schema.yaml`, `database.toml`, `data/`, `tests/`) yet is theirs to own and push
to — cleaner than forking or copying files by hand.

The same-name suggestion is a nice-to-have, not a gate: if the user already made their repo under a
different name, or gives you both the database name and repo URL in one message, just take both and move
on. Don't mention the mismatch upfront — wait until Step 8 (after setup is complete) to raise it.

Hold on to the database name for Step 4. Wait until you have a repo URL before continuing to Step 2; if
the user hasn't made the repo yet, walk them through the three steps above and pause until they do.

(This wait-for-a-URL gate applies only to **Path A**. On **Path B** — already inside a cloned repo — there
is no URL to wait for and no repo to create; you only need the database name, so ask for it if the user
didn't give one, then jump straight to Step 3's verification against the current directory.)

## Step 2: Clone the user's repo

Clone the repo they gave you into the current directory:

```bash
git clone <user-repo-url>
```

Do this without asking the user where to put it or what working directory to use — `git clone` creates a
new folder named after the repo right where you already are, which is exactly what's wanted. There's
nothing meaningful to ask about directories yet, since `<repo-dir>` doesn't exist until this command
finishes; that conversation belongs in Step 8, once it does.

If `git` isn't available or the clone fails (e.g. no network, or a private repo you can't access), don't
fake it or work around it — tell the user plainly, and if it's an access problem point them at making the
repo public or setting up credentials, then re-run.

## Step 3: Verify the structure matches the template

Confirm the repo really came from the template by checking it has the expected pieces — a `data/`
directory, a `database.toml`, and a `schema.yaml`. On Path A `<repo-dir>` is the folder you just cloned;
on Path B it is the current directory (`.`):

```bash
cd <repo-dir>
for p in data database.toml schema.yaml; do
  [ -e "$p" ] && echo "✓ $p" || echo "✗ MISSING $p"
done
```

If any of the three is missing, the repo probably wasn't created from the astrodb-template — tell the
user what's absent and have them confirm they used **Use this template** on astrodb-template-db before
going on.

Now that the repo is in place, initialize this skill's checklist file per the **completion-checklist
convention** in `references/astrodb-directions.md`. Create the artifact directory and copy the items
from `## Completion Checklist` (bottom of this file) into
`<repo-dir>/astrodb-build-artifacts/astrodb-build-setup-checklist.md`, then tick items with evidence as
you complete them through the rest of setup:

```bash
mkdir -p <repo-dir>/astrodb-build-artifacts
```

## Step 4: Remove generated schema representations from the template

The template ships with pre-generated schema files that reflect the *template* schema, not the user's
new database. Delete them now so they don't mislead anyone and so they can be regenerated fresh once
the user's real schema is in place:

```bash
rm -f <repo-dir>/docs/figures/schema_erd.png
rm -f <repo-dir>/docs/schema/*.md
```

Both removals are safe even if the files don't exist (`-f` suppresses errors). Don't skip this step —
leaving these stale files in place is the bug this step fixes.

Note the ERD really does live at `docs/figures/schema_erd.png`, not at the repo root. Because `-f`
swallows a missing-file error, a wrong path here fails silently and leaves the stale diagram in place
while looking like it worked — so confirm the file is actually gone rather than trusting the exit code:

```bash
ls <repo-dir>/docs/figures/schema_erd.png 2>/dev/null && echo "STILL PRESENT — check the path" || echo "removed"
```

## Step 5: Set the database name in database.toml

Update the cloned `database.toml` so `db_name` is the name from Step 1. It ships as
`db_name = "astrodb-template"`; change only that value and leave the rest of the file (and the trailing
comment) intact:

```bash
sed -i '' 's/db_name = "[^"]*"/db_name = "<new-name>"/' <repo-dir>/database.toml
grep '^db_name' <repo-dir>/database.toml   # confirm it now reads the user's name
```

Editing the line by hand is fine too — the point is that `db_name` ends up matching the user's chosen
name.

## Step 6: Update the README and CLAUDE.md

The cloned repo still has the template's generic descriptions. Now that the database has a name and the
user knows what it's for, update everything in one pass.

### 6a: Get the database description

**If the directions document describes the database, use that description** and skip the question —
say which text you're using so they can correct it, then go straight to 6b. The user already wrote this
down; asking again would waste their time and suggest you hadn't read it.

Otherwise, show the user the first few lines of the current README so they can see what's there:

```bash
head -12 <repo-dir>/README.md
```

Then ask:

> The README still has the template's placeholder text. What's a one- or two-sentence description of
> this database — what does it contain, and what science does it support? I'll update the title,
> description, and CLAUDE.md so they all reflect your work.

Once they give you a description, apply it in the places below.

### 6b: Update README.md

Update `README.md` in two places:

1. **Title line** (line 1): replace `astrodb-template-db` with the database name from Step 1.
2. **Description line**: replace `A template schema for astronomical databases.` with the user's
   description.

Remove the text that refers to the astrodb-utils package. Also remove the entity relationship diagram
(ERD) image link — it points to `docs/figures/schema_erd.png`, which Step 4 deleted, so the link would
now be broken.

Keep the Acknowledgements section and the credit line at the bottom that acknowledges the AstroDB Toolkit and template.

Do this with the `Edit` tool (not `sed`) so the rest of the file — badges, links, the credit line — stays
intact.

After editing, confirm with a brief summary:

> README updated — title is now `<new-name>` and the description reflects your database.

Verify the credit line at the bottom still acknowledges the AstroDB Toolkit and template:
`This repository is based on the [astrodb-template](https://github.com/astrodbtoolkit/astrodb-template-db) template repository, which is part of the [AstroDB Toolkit](https://github.com/astrodbtoolkit).`

If the user skips this step or says "later" or "skip it," replace the template placeholder text with
generic placeholders so the README doesn't still read as the template:

1. **Title line** (line 1): replace `astrodb-template-db` with `[Database name]`
2. **Description line**: replace `A template schema for astronomical databases.` with
   `[Add a brief description of this database here.]`

### 6c: Update CLAUDE.md (if present)

Check whether `CLAUDE.md` exists in the cloned repo:

```bash
ls <repo-dir>/CLAUDE.md
```

If `CLAUDE.md` does not exist, skip this sub-step.

If it does, read it and look for a project description section — typically a line like
`A template schema for astronomical databases, part of the astrodbtoolkit ecosystem.`
Replace it with the same description the user gave for the README. Use the `Edit` tool.

Remove the Git and GitHub instructions (the `## Git and GitHub` section). They describe the *template*
repo's own contribution workflow, not the user's — left in place, they'd point the user's agent at
conventions that don't apply to their database.

Replace references to `astrodb-template` with the new database name. In the current template these are
filenames like `astrodb-template.sqlite`, which becomes `<new-name>.sqlite` once `db_name` changes —
that's the rename you want. Read each hit before changing it rather than running a blind
find-and-replace: the same string appears inside links to the upstream template repo
(`astrodb-template-db`), and rewriting those points the user's docs at a repository that doesn't exist.
Rename what describes *this* database; leave anything that points at the upstream template alone.

If the user skips this step or says "later" or "skip it," that's fine — move on to Step 7 without
pressing.

## Step 7: Update the LICENSE

The cloned repo's `LICENSE` (BSD 3-Clause) still carries the template authors' copyright — the people who
wrote the AstroDB template, not whoever now owns this database. Like the README, this is the moment to
make it theirs.

Show the copyright line as it currently stands so they can see whose names are on it:

```bash
grep 'Copyright (c)' <repo-dir>/LICENSE
```

If there's no `LICENSE` file, say so and offer to add one — don't invent attribution.

**If the directions document specifies the license and/or the copyright name(s), use them** and skip
the question — report what you applied so they can correct it. Attribution is the one thing here you
must never guess at, so treat the document as the answer only where it actually says something: if it
names the holder but not the license, keep BSD 3-Clause and don't ask again about the name; if it names
neither, ask as below.

Otherwise ask:

> Your `LICENSE` still lists the template's authors:
> `<the copyright line you just printed>`
> You can put your own name(s) on it — added alongside those authors or replacing them — or switch to a
> different license entirely (MIT, Apache-2.0, …). The simplest is to add your name alongside. Whose
> name(s) should this database be under, and which license?

Act on their answer with the `Edit` tool (not `sed`), leaving the rest of the file intact:

- **Same license, new names** — change only the names in the `Copyright (c) <year>, …` line, adding or
  replacing as they asked. Leave the year as-is unless they want it updated.
- **A different license** — replace the whole `LICENSE` with the standard text of the license they chose,
  filling in the current year and their name in its copyright line. Don't leave a placeholder year or
  name behind. If they're unsure which to pick, point them to https://choosealicense.com.

If the user says "skip," "later," or "leave it," that's fine — move on to Step 7 without pressing.

## Step 9: Artifacts directory and directions document

Create the artifacts directory now, so everything downstream has a home to write to:

```bash
mkdir -p <repo-dir>/astrodb-build-artifacts
```

This is the canonical location the rest of the pipeline persists its work — parsed table results, the
generated schema, and the directions document if there is one. Standing up the empty directory is
cheap and makes the convention visible; it commits the user to nothing.

A **directions document** captures dataset-specific decisions, known issues, and ingestion notes.
Downstream skills (`astrodb-build-parse-table`, `astrodb-build-schema-match`, etc.) accept it as an
optional input — either as a user-provided file path, or from `astrodb-build-artifacts/directions.md`
if it was saved there in a prior run.

**If the user already provided a path** to a directions document, you will have read it long before
reaching this step (see "The directions document" above). What's left here is to *persist* it — copy it
into the repo so it survives:

```bash
cp <user-supplied-path> <repo-dir>/astrodb-build-artifacts/directions.md
```

Do this even though you've already read it. The path the user typed is theirs, often outside the repo
and specific to this one conversation; downstream skills look in `astrodb-build-artifacts/directions.md`
and have no way to guess where the original lives. Copying it in is what turns a one-off path into the
project's own record — otherwise the user has to re-supply it to every skill, which is exactly the
friction the document exists to remove. Then proceed to Step 9.

**Otherwise**, read `references/directions_example.md` and show the user what a directions document
covers. Ask:

> Would you like to write a directions document now? It's the best place to record notes about your
> data — columns to skip, how to handle tricky cases, schema decisions you've already made. You can
> always add to it later, or pass the path to a downstream skill when you're ready.

If the user wants to write one now, help them draft it from their notes and save it to
`<repo-dir>/astrodb-build-artifacts/directions.md`.

If they'd rather skip, leave the directory empty and move on — they can pass a path to a downstream
skill later. Don't copy the example in as a placeholder to fill later: downstream skills read the
presence of `directions.md` as a signal that real, user-authored guidance exists, so a file of unfilled
headings is worse than no file at all — it sends them looking for direction the user never gave.

## Step 11: Confirm, and point to what's next

Tell the user the scaffold is ready: where the repo was cloned, that the structure checks out, and that
`db_name` is set (along with any README and LICENSE edits they made). This is also the natural point to
bring up `<repo-dir>` as their project directory going forward — every other astrodb-* skill looks for
`database.toml`, `schema.yaml`, etc. in the current
directory, so they'll want to be inside `<repo-dir>` for the next step. Then name that next step,
`astro-parse-data-table`, without doing it — adding a data table to parse and map into this schema is a
separate skill:

> Your AstroDB repo is cloned into `<repo-dir>` — that's your project directory from here on (the other
> astrodb-* skills run from inside it). The structure matches the template, and `db_name` is set to
> `<new-name>`. The next step is to bring in a data table and run the `astro-parse-data-table` skill — let
> me know when you have one and we'll parse it into this database.

**If the repo name and database name don't match** (e.g. the repo is `test-astrodb` but `db_name` is
`BdSurvey`), add this after the wrap-up:

> One thing to consider: your repo is named `<repo-dir>` but the database is `<new-name>`. Would you like
> to rename the GitHub repo to match? If so:
> 1. Go to your repo on GitHub → Settings → rename it to `<new-name>`
> 2. Let me know and I'll update your local git remote to point to the new URL:
>    ```bash
>    git remote set-url origin https://github.com/<your-username>/<new-name>
>    ```
>    I can also rename the local directory if you'd like (`mv <repo-dir> <new-name>`).
>
> This is optional — GitHub redirects the old URL for a while — but keeping them in sync avoids confusion
> later.

Only raise this if there is an actual mismatch. If the names already match, skip this entirely.

## Final Step: Initialize `workflow.md`

Follow the convention in `references/astrodb-directions.md`. Create `workflow.md` in the
repo root (using the standard header) and append a setup entry recording: the database name
chosen, the GitHub repo URL, the README description provided, and whether a directions
document was completed now or deferred. Subsequent skills will append to this file.

## Completion Checklist

Track this checklist as a file per the **completion-checklist convention** in
`references/astrodb-directions.md`: you copied it to
`astrodb-build-artifacts/astrodb-build-setup-checklist.md` once the repo was in place and ticked items
with evidence as you went. Before telling the user setup is complete, read that file back — any unchecked
box means you are not done (finish it, or record the user's explicit waiver) — then reproduce the
evidence-annotated checklist here. Never tick a box by inventing a value (e.g. a name the user never
gave) or by claiming a check you didn't actually run.

Where an item says "asked", reading the answer out of the directions document counts — that's the point
of the document. What doesn't count is neither asking nor finding it written down.

- [ ] **Directions** — if the user gave a path, or `astrodb-build-artifacts/directions.md` existed, you read it before asking anything it could have answered, and told the user what you took from it.
- [ ] The repo is present — you cloned it (Path A) or it was already cloned and you're inside it (Path B) — and you verified it has the template structure: a `data/` directory, a `database.toml`, and a `schema.yaml`.
- [ ] The template's pre-generated schema representations were removed — `docs/figures/schema_erd.png` and `docs/schema/*.md` no longer exist in the repo (you confirmed the ERD is actually gone, not just that `rm -f` returned success).
- [ ] `db_name` in `database.toml` is set to the user's chosen name (it no longer reads `astrodb-template`).
- [ ] **README** — the title + description reflect this database, from the directions document or from the user's answer (or they explicitly skipped). Removed: the astrodb-utils line and the template ERD image link. Still intact: the bottom credit line acknowledging the AstroDB Toolkit/template.
- [ ] **CLAUDE.md** — if the repo has one, its project description reflects the user's database, the Git/GitHub instructions are gone, and no `astrodb-template` references remain (or the user explicitly skipped). If the repo has no `CLAUDE.md`, this is a no-op.
- [ ] **LICENSE** — the copyright/license reflects what the directions document or the user specified: new name(s) on the BSD 3-Clause copyright, or a different license with the year and name filled in (no placeholder left behind) — or they explicitly declined. You never put a name on it that neither the user nor the directions document gave.
- [ ] **Artifacts** — `astrodb-build-artifacts/` exists. If the user supplied a directions document by path, it has been copied to `astrodb-build-artifacts/directions.md`. It contains `directions.md` only if the user actually wrote one or supplied a path; you did not leave an unfilled template behind.
- [ ] You told the user the cloned directory is their project directory from here on, and named the next step (parse a data table).
- [ ] If — and only if — the repo name and `db_name` differ, you raised the mismatch at the end and offered the `git remote set-url` fix.

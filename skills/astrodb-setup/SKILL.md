---
name: astrodb-setup
description: First step in creating a new AstroDB database — run this FIRST, before any other astrodb-* skill, whenever the user wants to start, create, or set up a new AstroDB (astronomical) database, or asks "what's the first step to making a new astrodb." It stands up the database repository — instruct the user to create their own GitHub repo from the astrodb-template (https://github.com/astrodbtoolkit/astrodb-template-db, via "Use this template") and give you its address, ask for a database name, clone that repo into the working directory, verify it has the expected template structure (a data/ directory, a database.toml, and a schema.yaml), and update database.toml with the new name. This step only stands up and names the empty scaffold — it does not touch data files or ingestion, which come later. Trigger on "start a new astrodb," "set up an astronomical database," or "what's the first step to a new astrodb." When beginning a brand-new AstroDB, use this skill first.
compatibility: git, python
metadata:
  authors: ["Claude"]
---

# AstroDB Setup

This is the **first step** in standing up a new AstroDB, and its whole job is to get a correctly
structured, named database repository onto the user's machine — nothing more. It deliberately stops
before any data is involved; bringing in a data table to parse and ingest is the *next* step, handled
by the other astrodb skills. Keeping this step small means the user finishes it holding a clean, valid,
empty database scaffold that is theirs to build on.

Every AstroDB starts from the **astrodb-template-db**, which is published as a GitHub *template*
repository. The right way to begin is not to clone that template directly — it's for the user to create
their *own* repository from it (so they own the history and can push their work), and then we clone
that. Work through the steps in order.

## Step 1: Have the user create their repo from the template

Ask the user to create a new GitHub repository from the AstroDB template, then send you its address:

> 1. Go to https://github.com/astrodbtoolkit/astrodb-template-db
> 2. Click **Use this template → Create a new repository**, give it a name, and create it.
> 3. Paste the new repo's URL here (e.g. `https://github.com/<you>/<your-db>`).

Why this way: the template is a GitHub *template* repo, so "Use this template" hands the user a brand-new
repository that already contains the full AstroDB structure (`schema.yaml`, `database.toml`, `data/`,
`tests/`) yet is theirs to own and push to — cleaner than forking or copying files by hand.

Wait until the user gives you a repo URL before continuing. If they haven't made it yet, walk them
through the three steps above and pause until they do.

## Step 2: Ask for the database name

Ask what they want to call the database — this becomes `db_name` in `database.toml` and will name the
eventual SQLite file:

> What should I name the database? (e.g. `MyCoolSurvey`.)

Hold on to the answer for Step 5.

## Step 3: Clone the user's repo

Clone the repository they gave you into the working directory:

```bash
git clone <user-repo-url>
```

The clone lands in a folder named after their repo. If `git` isn't available or the clone fails (e.g.
no network, or a private repo you can't access), don't fake it or work around it — tell the user
plainly, and if it's an access problem point them at making the repo public or setting up credentials,
then re-run.

## Step 4: Verify the structure matches the template

Confirm the clone really came from the template by checking it has the expected pieces — a `data/`
directory, a `database.toml`, and a `schema.yaml`:

```bash
cd <repo-dir>
for p in data database.toml schema.yaml; do
  [ -e "$p" ] && echo "✓ $p" || echo "✗ MISSING $p"
done
```

If any of the three is missing, the repo probably wasn't created from the astrodb-template — tell the
user what's absent and have them confirm they used **Use this template** on astrodb-template-db before
going on.

## Step 5: Remove generated schema representations from the template

The template ships with pre-generated schema files that reflect the *template* schema, not the user's
new database. Delete them now so they don't mislead anyone and so they can be regenerated fresh once
the user's real schema is in place:

```bash
rm -f <repo-dir>/schema_erd.png
rm -f <repo-dir>/docs/schema/*.md
```

Both removals are safe even if the files don't exist (`-f` suppresses errors). Don't skip this step —
leaving these stale files in place is the bug this step fixes.

## Step 6: Set the database name in database.toml

Update the cloned `database.toml` so `db_name` is the name from Step 2. It ships as
`db_name = "astrodb-template"`; change only that value and leave the rest of the file (and the trailing
comment) intact:

```bash
sed -i -E 's/^(db_name[[:space:]]*=[[:space:]]*)"[^"]*"/\1"<new-name>"/' <repo-dir>/database.toml
grep '^db_name' <repo-dir>/database.toml   # confirm it now reads the user's name
```

Editing the line by hand is fine too — the point is that `db_name` ends up matching the user's chosen
name.

## Step 7: Create an artifacts directory and directions document

Create an `artifacts/` directory in the cloned repo to hold reproducibility artifacts:

```bash
mkdir -p <repo-dir>/artifacts
```

A **directions document** lives at `artifacts/directions.md` and captures dataset-specific decisions,
known issues, and ingestion notes. It is read automatically by subsequent skills
(`astrodb-parse-data-table`, `astrodb-match-schema`, etc.) to guide their decisions — so filling it
in now saves time and prevents inconsistencies later.

Read `references/directions_example.md` now, then show it to the user and explain what each section
captures. Ask:

> Would you like to fill in a directions document now? It's the best place to record notes about your
> data — columns to skip, how to handle tricky cases, schema decisions you've already made. You can
> always add to it later.

If the user wants to fill it in now, help them write one based on their notes and save it to
`<repo-dir>/artifacts/directions.md`. If they'd rather do it later, copy the example to
`<repo-dir>/artifacts/directions.md` with a comment at the top marking it as a template to fill in.

## Step 8: Confirm, and point to what's next

Tell the user the scaffold is ready: where the repo was cloned, that the structure checks out, that
`db_name` is set, and that an `artifacts/directions.md` has been created. Then name the next step,
`astrodb-parse-data-table`, without doing it — adding a data table to parse and map into this schema
is a separate skill:

> Your AstroDB repo is cloned into `<repo-dir>`, the structure matches the template, `db_name` is set
> to `<new-name>`, and a directions document is waiting at `artifacts/directions.md`. The next step is
> to bring in a data table and run the `astrodb-parse-data-table` skill — let me know when you have
> one and we'll parse it into this database.
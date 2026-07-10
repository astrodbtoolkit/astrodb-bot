---
name: astrodb-build-setup
description: First step in creating a new AstroDB database — run this FIRST, before any other astrodb-* skill, whenever the user wants to start, create, or set up a new AstroDB (astronomical) database, or asks "what's the first step to making a new astrodb." It stands up the database repository — ask for a database name (and suggest the user give their new GitHub repo that same name), have the user create that repo from the astrodb-template (https://github.com/astrodbtoolkit/astrodb-template-db, via "Use this template") and give you its address, clone that repo, verify it has the expected template structure (a data/ directory, a database.toml, and a schema.yaml), and update database.toml with the new name. This step only stands up and names the empty scaffold — it does not touch data files or ingestion, which come later. Trigger on "start a new astrodb," "set up an astronomical database," or "what's the first step to a new astrodb." When beginning a brand-new AstroDB, use this skill first.
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

## Step 1: Ask for a database name, then have the user create their repo from the template

Ask what they want to call the database — this becomes `db_name` in `database.toml` and names the
eventual SQLite file. Suggest they reuse that same name for the GitHub repo they're about to create:
picking it now is the only time it's free, since renaming a repo after the fact is just extra busywork.

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
on. Don't mention the mismatch upfront — wait until Step 5 (after setup is complete) to raise it.

Hold on to the database name for Step 4. Wait until you have a repo URL before continuing to Step 2; if
the user hasn't made the repo yet, walk them through the three steps above and pause until they do.

## Step 2: Clone the user's repo

Clone the repo they gave you into the current directory:

```bash
git clone <user-repo-url>
```

Do this without asking the user where to put it or what working directory to use — `git clone` creates a
new folder named after the repo right where you already are, which is exactly what's wanted. There's
nothing meaningful to ask about directories yet, since `<repo-dir>` doesn't exist until this command
finishes; that conversation belongs in Step 5, once it does.

If `git` isn't available or the clone fails (e.g. no network, or a private repo you can't access), don't
fake it or work around it — tell the user plainly, and if it's an access problem point them at making the
repo public or setting up credentials, then re-run.

## Step 3: Verify the structure matches the template

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

## Step 4: Set the database name in database.toml

Update the cloned `database.toml` so `db_name` is the name from Step 1. It ships as
`db_name = "astrodb-template"`; change only that value and leave the rest of the file (and the trailing
comment) intact:

```bash
sed -i '' 's/db_name = "[^"]*"/db_name = "<new-name>"/' <repo-dir>/database.toml
grep '^db_name' <repo-dir>/database.toml   # confirm it now reads the user's name
```

Editing the line by hand is fine too — the point is that `db_name` ends up matching the user's chosen
name.

## Step 5: Update the README

The cloned repo still has the template's generic README. Now that the database has a name and the user
knows what it's for, it's a good moment to make the README theirs.

Show the user the first few lines of the current README so they can see what's there:

```bash
head -12 <repo-dir>/README.md
```

Then ask:

> The README still has the template's placeholder text. What's a one- or two-sentence description of
> this database — what does it contain, and what science does it support? I'll update the title and
> description so it reflects your work.

Once they give you a description, update `README.md` in two places:

1. **Title line** (line 1): replace `astrodb-template-db` with the database name from Step 1.
2. **Description line**: replace `A template schema for astronomical databases.` with the user's
   description.

Remove the text that refers to the astrodb-utils package.

Keep the link to the entity relationship diagram (ERD) image, and the credit line at the bottom that acknowledges the AstroDB Toolkit and template.

Do this with the `Edit` tool (not `sed`) so the rest of the file — badges, links, the ERD image — stays
intact.

After editing, confirm with a brief summary:

> README updated — title is now `<new-name>` and the description reflects your database.

Also confirm that the user did not delete the credit line at the bottom of the README that acknowledges the AstroDB Toolkit and template: 
This repository is based on the [astrodb-template](https://github.com/astrodbtoolkit/astrodb-template-db) template repository, which is part of the [AstroDB Toolkit](https://github.com/astrodbtoolkit).

If the user skips this step or says "later" or "skip it," that's fine — just move on to Step 6 without
pressing.

## Step 6: Create an artifacts directory and directions document

Create an `artifacts/` directory in the cloned repo to hold reproducibility artifacts:

```bash
mkdir -p <repo-dir>/artifacts
```

A **directions document** lives at `artifacts/directions.md` and captures dataset-specific decisions,
known issues, and ingestion notes. It is read automatically by subsequent skills
(`astrodb-build-parse-table`, `astrodb-build-schema-match`, etc.) to guide their decisions — so filling
it in now saves time and prevents inconsistencies later.

Read `references/directions_example.md` now, then show it to the user and explain what each section
captures. Ask:

> Would you like to fill in a directions document now? It's the best place to record notes about your
> data — columns to skip, how to handle tricky cases, schema decisions you've already made. You can
> always add to it later.

If the user wants to fill it in now, help them write one based on their notes and save it to
`<repo-dir>/artifacts/directions.md`. If they'd rather do it later, copy the example to
`<repo-dir>/artifacts/directions.md` with a comment at the top marking it as a template to fill in.

After the directions document is handled, initialize the workflow log. Read
`references/astrodb-directions.md` for the full convention. Create `workflow.md` in the
repo root (using the standard header from `references/astrodb-directions.md`), then append
a setup entry recording: the database name chosen, the GitHub repo URL, the README
description provided, and whether a directions document was completed now or deferred.

## Step 7: Confirm, and point to what's next

Tell the user the scaffold is ready: where the repo was cloned, that the structure checks out, and that
`db_name` is set. This is also the natural point to bring up `<repo-dir>` as their project directory going
forward — every other astrodb-* skill looks for `database.toml`, `schema.yaml`, etc. in the current
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

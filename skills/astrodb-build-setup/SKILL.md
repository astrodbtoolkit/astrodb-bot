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

## Step 4: Remove generated schema representations from the template

The template ships with pre-generated schema files that reflect the *template* schema, not the user's
new database. Delete them now so they don't mislead anyone and so they can be regenerated fresh once
the user's real schema is in place:

```bash
rm -f <repo-dir>/schema_erd.png
rm -f <repo-dir>/docs/schema/*.md
```

Both removals are safe even if the files don't exist (`-f` suppresses errors). Don't skip this step —
leaving these stale files in place is the bug this step fixes.

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

## Step 6: Update the README

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

Remove the text that refers to the astrodb-utils package. Also remove the entity relationship diagram (ERD) image link — it points to the template's `schema_erd.png`, which Step 4 deleted, so the link would now be broken.

Keep the credit line at the bottom that acknowledges the AstroDB Toolkit and template.

Do this with the `Edit` tool (not `sed`) so the rest of the file — badges, links, the credit line — stays
intact.

After editing, confirm with a brief summary:

> README updated — title is now `<new-name>` and the description reflects your database.

Also confirm that the user did not delete the credit line at the bottom of the README that acknowledges the AstroDB Toolkit and template: 
This repository is based on the [astrodb-template](https://github.com/astrodbtoolkit/astrodb-template-db) template repository, which is part of the [AstroDB Toolkit](https://github.com/astrodbtoolkit).

If the user skips this step or says "later" or "skip it," replace the template placeholder text with
generic placeholders so the README doesn't still read as the template:

1. **Title line** (line 1): replace `astrodb-template-db` with `[Database name]`
2. **Description line**: replace `A template schema for astronomical databases.` with
   `[Add a brief description of this database here.]`

Then move on to Step 7 without pressing further.

## Step 7: Update the LICENSE

The cloned repo's `LICENSE` (BSD 3-Clause) still carries the template authors' copyright — the people who
wrote the AstroDB template, not whoever now owns this database. Like the README, this is the moment to
make it theirs.

Show the copyright line as it currently stands so they can see whose names are on it:

```bash
grep 'Copyright (c)' <repo-dir>/LICENSE
```

If there's no `LICENSE` file, say so and offer to add one — don't invent attribution.

Then ask:

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

## Step 8: Directions document (optional input)

A **directions document** captures dataset-specific decisions, known issues, and ingestion notes.
Downstream skills (`astrodb-build-parse-table`, `astrodb-build-schema-match`, etc.) accept it as an
optional input — either as a user-provided file path, or from `astrodb-build-artifacts/directions.md`
if it was saved there in a prior run.

**If the user already provided a path** to a directions document at the start of this skill (e.g.
as part of their initial message), read it now and acknowledge it. No need to ask — proceed to
Step 9.

**Otherwise**, read `references/directions_example.md` and show the user what a directions document
covers. Ask:

> Would you like to write a directions document now? It's the best place to record notes about your
> data — columns to skip, how to handle tricky cases, schema decisions you've already made. You can
> always add to it later, or pass the path to a downstream skill when you're ready.

If the user wants to write one now, help them draft it based on their notes. Save it wherever they
tell you to save it — do not prescribe a location.

If they'd rather skip, that's fine — they can provide the path to a directions document when running
downstream skills.

## Step 9: Confirm, and point to what's next

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

## Completion Checklist

Before telling the user setup is complete, confirm every item below. Anything unmet must be done — or
explicitly waived by the user — first. Never tick a box by inventing a value (e.g. a name the user never
gave) or by claiming a check you didn't actually run.

- [ ] The repo is present — you cloned it (Path A) or it was already cloned and you're inside it (Path B) — and you verified it has the template structure: a `data/` directory, a `database.toml`, and a `schema.yaml`.
- [ ] `db_name` in `database.toml` is set to the user's chosen name (it no longer reads `astrodb-template`).
- [ ] **README** — you prompted for a description and updated the title + description (or the user explicitly skipped). Removed: the astrodb-utils line and the template ERD image link. Still intact: the bottom credit line acknowledging the AstroDB Toolkit/template.
- [ ] **LICENSE** — you showed the current copyright line and acted on the user's choice: new name(s) on the BSD 3-Clause copyright, or a different license with the year and name filled in (no placeholder left behind) — or the user explicitly declined. You never put a name on it that the user didn't give.
- [ ] You told the user the cloned directory is their project directory from here on, and named the next step (parse a data table).
- [ ] If — and only if — the repo name and `db_name` differ, you raised the mismatch at the end and offered the `git remote set-url` fix.

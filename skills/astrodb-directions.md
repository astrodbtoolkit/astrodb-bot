# AstroDB Directions: Shared Skill Conventions

This document collects the conventions that **every** skill in the AstroDB pipeline follows, so they
live in one place instead of being repeated in each `SKILL.md`. It covers the `workflow.md` decision
log, the artifact-folder convention, and the completion-checklist convention. Each skill's
`references/astrodb-directions.md` is a symlink to this file, so a skill reads all three by reading it.

## Purpose: the `workflow.md` decision log

`workflow.md` is a living decision log maintained in the user's **current working directory**
(the project root, alongside `database.toml` and `schema.yaml`). Every skill in the AstroDB
pipeline reads it and appends to it.

Its purpose is to answer "why did the skill make that decision?" — recording dataset-specific
context, choices, and reasoning that would otherwise disappear after the conversation ends.
A future reader (or a later skill) can open `workflow.md` and understand what was done and why,
without having to re-examine the data or re-run anything.

## Every skill must

1. **Read** `workflow.md` at the start (if it exists) — to carry forward context from prior skills.
2. **Create** `workflow.md` with the standard header if it does not exist yet.
3. **Append** one entry after completing its main work, recording decisions made and why.

## Standard header

If `workflow.md` does not exist yet, create it with:

```markdown
# AstroDB Workflow Log

This file records decisions made during the ingestion workflow — what was chosen and why.
Each skill appends one entry. Do not edit existing entries; add new ones at the end.
```

## Entry format

```markdown
## <Skill Name> — <YYYY-MM-DD>

**Input:** <data file path or description of what was processed>

### Decisions

- **<topic>:** <what was decided> — *because <reason>*

### Open questions

- <anything deferred, unresolved, or left for a later skill to address>
```

Omit the "Open questions" section if there are none.

## What to log

Log any non-obvious choice a future reader might question:

- Why a specific file reader was used (e.g., pandas instead of astropy, or a specific format hint)
- Why a column was mapped to a particular field, especially for Low or Medium confidence matches
- Why a column was skipped, ignored, or marked Unmatched
- Why a new table or field was proposed instead of mapping to an existing one
- What the user confirmed when the skill stopped to ask for input
- Any assumption made in the absence of explicit directions from `artifacts/directions.md`
- Why a file format was converted from one type to another

Do **not** log mechanical steps (creating directories, opening files, installing packages,
running validation commands that passed without issues).

## Artifact folder convention

Each skill writes its outputs inside its **artifact directory** in the current working directory:
`astrodb-build-artifacts/` for the build and website skills, `astrodb-ingest-artifacts/` for the
ingest skills. Create it before writing any files:

```bash
mkdir -p astrodb-build-artifacts    # or astrodb-ingest-artifacts, for the ingest skills
```

If this fails, stop and tell the user you cannot create the output directory.

## Completion-checklist convention

Every skill ends with a `## Completion Checklist` — a short list of verifiable outcomes that must
hold before the skill reports itself done. Treat that checklist as **file-tracked**, not something you
read once at the start and try to remember. On a long run, an unchecked list read only at the outset
quietly falls out of attention, and the items that get skipped are exactly the ones with no immediate
visible failure — a deleted-file that wasn't deleted, a `SAVE_DB` left flipped, a check never run.
Keeping the checklist in a file you revisit is what keeps it honest.

So for **every** skill:

1. **Create the checklist file at the start.** Copy the items from that skill's `## Completion
   Checklist` section — verbatim and unchecked — into `<artifact-dir>/<skill-name>-checklist.md`
   (e.g. `astrodb-build-artifacts/astrodb-build-parse-table-checklist.md`). `<artifact-dir>` is the
   skill's artifact directory from the convention above. Overwrite any copy a previous run left behind.

2. **Tick items as they are genuinely done.** The moment an item is satisfied, flip its `[ ]` to `[x]`
   in the file and add a one-line evidence note — the value you set, the path you wrote, or the command
   output that proves it. Never tick a box by inventing a value or claiming a check you didn't run.
   Where an item depends on the user, record what actually happened ("prompted and the user declined"),
   never a forced action you didn't take.

3. **Verify before reporting done.** Read the checklist file back. Any unchecked box means you are not
   finished — complete the item, or record the user's explicit waiver as its evidence note. Then
   reproduce the evidence-annotated checklist in your completion message, so the user sees exactly what
   was verified instead of a bare "all checks passed."

If you reach the end and the file was never created, create it now and backfill honestly — tick only
what you can still prove.

## Skills must ask, not assume

If `workflow.md` and `artifacts/directions.md` do not address a decision the current skill
must make, **stop and ask the user** rather than silently applying a default. Record the
user's answer in `workflow.md`. The log is most valuable when it captures real, explicit
choices — silent guesses are not helpful to a future reader.

# AstroDB Directions: Shared Skill Conventions

This document collects the conventions that **every** skill in the AstroDB pipeline follows, so they
live in one place instead of being repeated in each `SKILL.md`. It covers the `workflow.md` decision
log, the artifact-folder convention, the `gotchas.md` problem log, and the completion-checklist
convention. Each skill's `references/astrodb-directions.md` is a symlink to this file, so a skill reads
them all by reading it.

Two things vary by **workflow phase** (build / ingest / website) and are defined in that phase's own
directions file — `astrodb-build-directions.md`, `astrodb-ingest-directions.md`, or
`astrodb-website-directions.md` (symlinked into each skill as `references/astrodb-<phase>-directions.md`):
the exact **decision-log file** a phase uses, and whether the phase **persists** its completion
checklist. Everything below applies everywhere.

Each **workflow** has its own artifact directory in the current working directory, and every skill in
that workflow writes its outputs there.

## The decision log

Every phase keeps a **decision log** — a living record of *why* the skill made the choices it did,
capturing dataset-specific context and reasoning that would otherwise disappear after the conversation.
A future reader (or a later skill) can open it and understand what was done and why, without re-examining
the data or re-running anything. Read it at the start (if it exists) to carry forward context, and add
an entry after your main work.

Each phase keeps its log in **its own artifact directory** (not the project root), so the phases don't
share one file. **Which file it is, and whether entries are appended or prepended, is defined in your
phase's `astrodb-<phase>-directions.md`.** Use this standard entry format:

```markdown
## <Skill Name> — <YYYY-MM-DD>

**Input:** <data file path or description of what was processed>

### Decisions
- **<topic>:** <what was decided> — *because <reason>*

### Open questions
- <anything deferred, unresolved, or left for a later skill to address>
```

Omit "Open questions" if there are none.

### What to log

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

Each **workflow** has its own artifact directory in the current working directory, and every skill in
that workflow writes its outputs there:

| Workflow | Skills | Artifact directory |
|----------|--------|--------------------|
| build    | `astrodb-build-*` | `astrodb-build-artifacts/` |
| ingest   | `astrodb-ingest-*` | `astrodb-ingest-artifacts/` |
| website  | `astrodb-website` | `astrodb-website-artifacts/` |

Create the directory before writing any files:

```bash
mkdir -p astrodb-build-artifacts   # or astrodb-ingest-artifacts / astrodb-website-artifacts
```

If this fails, stop and tell the user you cannot create the output directory.

## Problem log: `gotchas.md`

`gotchas.md` is a running log of problems with **the skills themselves**, kept in the user's current
working directory alongside `workflow.md`. The two files answer different questions and should not be
mixed:

| File | Question it answers | Written for |
|------|---------------------|-------------|
| `workflow.md` | Why did the skill decide *that* for *this dataset*? | whoever works on this database later |
| `gotchas.md`  | What tripped the skill up, and what should change in the skill? | the maintainers of the astrodb-bot repo |

Without this file, everything learned the hard way during a run disappears when the conversation ends, and
the next user rediscovers the same trap. Create `gotchas.md` with the standard header below if it does not
exist yet; otherwise append. Never rewrite or delete an existing entry.

### Standard header

```markdown
# AstroDB Gotchas

Problems hit while running the AstroDB skills, and suggested fixes to the skills themselves.
Entries marked **gotcha** are worth reporting at
https://github.com/astrodbtoolkit/astrodb-bot/issues/new.
Each skill appends its own entries; do not edit existing ones.
```

### What counts as a significant problem

Log it if any of these are true:

- The skill's instructions were wrong, incomplete, or ambiguous enough that you had to guess.
- You deviated from the written steps to get a working result.
- A dependency (`astropy`, `pandas`, `felis`, `astrodbkit`, `astrodb_utils`, the `astrodb-template-db` or
  `astrodb-web` templates) behaved differently than the skill describes.
- A step reported success while producing a wrong or misleading result.
- The same trip-up happened more than once during the session.

Do **not** log:

- Dataset-specific quirks and the reasoning around them — those belong in `workflow.md`.
- Transient failures: a dropped connection, an ADS timeout, a file locked by another program.
- A user typo or wrong path that was corrected immediately.
- Anything the skill already documents — if it warned you and the warning worked, the skill did its job.

### Self-identify the gotchas

Classify every entry yourself, because the two kinds get different treatment:

- **`gotcha`** — the cause is in the skill or its tooling, and another user or another dataset would hit it
  again. These are the ones worth reporting.
- **`one-off`** — specific to this data, this machine, or this session. Logged for the record, not reported.

When it's genuinely unclear, ask whether you'd have to invent the same workaround again on a different
dataset. If yes, it's a gotcha.

### Entry format

Write each entry so it can be pasted into a GitHub issue as-is — the heading is the issue title and the
rest is the body:

```markdown
## <one-line summary> — <skill-name>, <YYYY-MM-DD>

**Kind:** gotcha | one-off
**Where:** <skill and step, or script path — e.g. astrodb-build-parse-table Step 3>
**What happened:** <the symptom; include the verbatim error text if there was one>
**Workaround:** <what you actually did to get past it>
**Suggested change:** <a concrete edit — which file and step, and what it should say instead>
```

**Suggested change** is required for a `gotcha` and is the most useful line in the entry. "The skill was
confusing" is not actionable; "Step 3 should say to check for the `Byte-by-byte Description` header before
treating a `.txt` file as CSV" is.

### Tell the user, but never file anything yourself

If you logged one or more `gotcha` entries during this run, end your completion message with a short block:

```markdown
**Worth reporting:** <one line per gotcha>

These look like problems with the skills rather than with your data. If you agree, please open an issue —
or a PR, if you'd like to make the fix — at https://github.com/astrodbtoolkit/astrodb-bot/issues/new.
The drafted text is in `gotchas.md` and can be pasted in as-is.
```

Whether to report is the user's call: do not open an issue or PR yourself, and do not run `gh`, even if it
is installed and authenticated. If you logged only `one-off` entries, say nothing — the file is there if
the user wants it.

## Completion-checklist convention

Every skill ends with a `## Completion Checklist` — a short list of verifiable outcomes that must hold
before the skill reports itself done. For **every** skill, regardless of phase:

1. **Verify every item before reporting done.** Treat the list as something you actually re-check at the
   end, not something you read once and try to remember — on a long run the items that quietly get
   skipped are exactly the ones with no immediate visible failure (a file that wasn't deleted, a
   `SAVE_DB` left flipped, a check never run).
2. **Never claim an item you didn't verify.** Where an item depends on the user, record what actually
   happened ("prompted and the user declined"), never a forced action you didn't take.
3. **Reproduce the evidence-annotated checklist in your completion message** — each item with a one-line
   note (the value you set, the path you wrote, the command output that proves it) — so the user sees
   exactly what was verified instead of a bare "all checks passed."

**Whether you also persist the checklist to a file** (`checklists.md`) is defined in your phase's
`astrodb-<phase>-directions.md`. Some phases track it in a file because they span many skills; others
verify-and-report only, to avoid bloat. Follow your phase's rule.

## Skills must ask, not assume

If the decision log and `artifacts/directions.md` do not address a decision the current skill must make,
**stop and ask the user** rather than silently applying a default. Record the user's answer in the
decision log. The log is most valuable when it captures real, explicit choices — silent guesses are not
helpful to a future reader.

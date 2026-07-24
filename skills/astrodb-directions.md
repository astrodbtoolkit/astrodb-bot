# AstroDB Directions: Shared Skill Conventions

This document collects the conventions that **every** skill in the AstroDB pipeline follows — build,
ingest, and website alike — so they live in one place instead of being repeated in each `SKILL.md`.
Each skill's `references/astrodb-directions.md` is a symlink to this file.

Two things vary by **workflow phase** (build / ingest / website) and are defined in that phase's own
directions file — `astrodb-build-directions.md`, `astrodb-ingest-directions.md`, or
`astrodb-website-directions.md` (symlinked into each skill as `references/astrodb-<phase>-directions.md`):
the exact **decision-log file** a phase uses, and whether the phase **persists** its completion
checklist. Everything below applies everywhere.

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

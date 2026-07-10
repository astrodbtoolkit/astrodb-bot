# AstroDB Directions: The `workflow.md` Convention

## Purpose

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

## Skills must ask, not assume

If `workflow.md` and `artifacts/directions.md` do not address a decision the current skill
must make, **stop and ask the user** rather than silently applying a default. Record the
user's answer in `workflow.md`. The log is most valuable when it captures real, explicit
choices — silent guesses are not helpful to a future reader.

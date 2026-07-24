# AstroDB Build Directions: conventions for the build workflow

These refine the shared conventions in `astrodb-directions.md` for the **build** skills
(`astrodb-build-*`). Read `astrodb-directions.md` first — it covers the artifact folder, the
decision-log entry format and what-to-log, the general completion-checklist behavior, and the
"ask, don't assume" rule. This file only states what is specific to the build phase.

## Decision log: `build-workflow.md`

The build phase's decision log is **`astrodb-build-artifacts/build-workflow.md`** — inside the build
artifact directory, so each phase keeps its own log in its own artifact folder rather than sharing one
project-root file.

- **Read** `build-workflow.md` at the start if it exists.
- **Create** it with the standard header if it doesn't:

  ```markdown
  # AstroDB Build Workflow Log

  Decisions made during the build phase — what was chosen and why.
  Each skill adds one entry. Do not edit existing entries; add new ones at the end.
  ```

- **Append** one entry (using the standard entry format from `astrodb-directions.md`) after your main
  work — newest at the **end**.

## Completion checklist: persisted to `checklists.md`

Beyond the shared verify-and-report behavior, the build phase **persists** its checklist to a single
shared file, `astrodb-build-artifacts/checklists.md`. The build workflow spans six skills run at
different times, so a file that accumulates one section per skill shows the whole phase's verification in
one place — worth the small overhead here. For every build skill:

1. **Record your section at the start.** If `astrodb-build-artifacts/checklists.md` doesn't exist yet,
   create it with a title line (e.g. `# AstroDB build-workflow checklists`). Then add — or, if you're
   re-running, replace — a `## <skill-name>` section (e.g. `## astrodb-build-parse-table`) holding this
   skill's `## Completion Checklist` items, verbatim and unchecked. Leave every other skill's section
   untouched.

2. **Tick your items as they are genuinely done.** The moment an item is satisfied, flip its `[ ]` to
   `[x]` under your section and add a one-line evidence note. Never tick a box by inventing a value or
   claiming a check you didn't run.

3. **Verify before reporting done.** Re-read your section; any unchecked box means you are not finished.
   Then reproduce your evidence-annotated section in your completion message (the shared convention).

If you reach the end and never opened the file, add your section now and backfill honestly — tick only
what you can still prove.

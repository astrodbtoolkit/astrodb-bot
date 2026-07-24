# AstroDB Website Directions: conventions for the website workflow

These refine the shared conventions in `astrodb-directions.md` for the **website** skill
(`astrodb-website`). Read `astrodb-directions.md` first — it covers the artifact folder, the
decision-log entry format and what-to-log, the general completion-checklist behavior, and the
"ask, don't assume" rule. This file only states what is specific to the website phase.

## Decision log: `website-workflow.md`

The website phase keeps its own decision log, **`astrodb-website-artifacts/website-workflow.md`** —
inside the website artifact directory, so each phase keeps its own log in its own artifact folder
rather than sharing one project-root file.

- **Read** `website-workflow.md` at the start if it exists. You may also read the build phase's
  `astrodb-build-artifacts/build-workflow.md` for context on how the database was produced.
- **Append** one entry (using the standard entry format from `astrodb-directions.md`, newest at the
  **end**), creating the file with the standard header if needed, only if the setup involved a notable
  decision worth recording — a non-default host/port, a chosen `--db-path`, or a config the user had to
  confirm. Purely mechanical setup needs no entry.

## Completion checklist: verify and report, don't persist

The website workflow is a **single** skill, so a persisted `checklists.md` would hold exactly one section
— pure overhead. Follow the shared verify-and-report behavior only: verify every item, reproduce the
evidence-annotated list in your completion message, and never claim an item you didn't verify. Do not
write the checklist out to a separate artifact file.

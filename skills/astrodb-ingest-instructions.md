# AstroDB Ingest Instructions: conventions for the ingest workflow

These refine the shared conventions in `astrodb-instructions.md` for the **ingest** skills
(`astrodb-ingest-*`). Read `astrodb-instructions.md` first — it covers the artifact folder, the
decision-log entry format and what-to-log, the general completion-checklist behavior, and the
"ask, don't assume" rule. This file only states what is specific to the ingest phase.

## Decision log: `ingest-workflow.md`

The ingest phase keeps its **own** decision log, separate from the build phase's `build-workflow.md`,
because the two phases run at different times and shouldn't share one file. Like every phase, it lives in
its own artifact directory: **`astrodb-ingest-artifacts/ingest-workflow.md`**.

- **Read** it at the start if it exists (and you may also read the build phase's
  `astrodb-build-artifacts/build-workflow.md` for upstream context).
- **Create** it with the standard header if it doesn't:

  ```markdown
  # AstroDB Ingest Workflow Log

  Decisions made during ingestion — what was chosen and why. Newest entry first.
  ```

- **Prepend** one entry (using the standard entry format from `astrodb-instructions.md`) after your main
  work — **most recent on top, each entry dated**. Do not edit existing entries; add a new one above them.

## Post-ingest checkpoint: link the database

After every ingest that actually writes to the database (`SAVE_DB` was flipped to `True` and the save
succeeded — not a dry run), tell the user where the `.sqlite` file lives and invite them to inspect it
before moving on:

- Resolve the real path — `<project-root>/<db_name>.sqlite` for the JSON template layout (read `db_name`
  from `database.toml`), or the standalone `.sqlite` path the user already pointed you to.
- Report it as a clickable markdown link (e.g. `[MyDataset.sqlite](MyDataset.sqlite)`) and suggest a quick
  way to look at it — open it in DB Browser for SQLite/TablePlus, or run a one-off query against the table
  you just touched.
- Do this even when the ingest reported success and nothing looked wrong. The checkpoint exists to catch
  what the ingest helpers can't — a description that's subjectively off, a row attached to the wrong
  source — not just to confirm the write happened.

This happens every time data is written, independent of the completion checklist below.

## Completion checklist: verify and report, don't persist

The ingest phase does **not** persist its checklist to a `checklists.md` file — the shared
verify-and-report behavior (verify every item, reproduce the evidence-annotated list in your completion
message, never fabricate) is all that's needed. The reason: the ingest helpers (`ingest_publication`,
`ingest_source`, `ingest_photometry`, …) already **fail loudly** when a precondition isn't met — a
missing reference, an unresolved source, a band absent from `PhotometryFilters`. If the ingest succeeded,
the important preconditions were met by construction, so a persisted "I checked this" file would add bloat
without adding safety.

So: run through the checklist, satisfy every item (or record the user's explicit waiver in
`ingest-workflow.md`), and report the evidence-annotated list in your final message — but do not write it
out to a separate artifact file.

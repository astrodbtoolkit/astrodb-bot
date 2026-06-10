---
name: astrodb-website
description: Set up and run a web interface for an AstroDB database using the astrodb-web template. Use this skill whenever a user wants to "view the database in a browser", "start the web interface", "see the data", or "set up the website".
compatibility: python, fastapi, uvicorn
---

# AstroDB Website

This skill sets up a FastAPI web interface ([astrodb-web](https://github.com/astrodbtoolkit/astrodb-web)) to browse and visualize an AstroDB SQLite database.

## Prerequisites

- An existing AstroDB SQLite database (`.sqlite` or `.db`).
- `uv` installed.
- Python 3.13+.

## Step 1: Have the User Create their Repo from the Template

Ask the user to create a new GitHub repository from the astrodb-web template, then send you its address:

> 1. Go to https://github.com/astrodbtoolkit/astrodb-web
> 2. Click **Use this template → Create a new repository**, give it a name, and create it.
> 3. Paste the new repo's URL here (e.g. `https://github.com/<you>/<your-website>`).

Why this way: the website is a GitHub *template* repo, so "Use this template" hands the user a brand-new
repository that already contains the full astrodb-web structure yet is theirs to own and push to — cleaner than forking or copying files by hand.

Wait until the user gives you a repo URL before continuing. If they haven't made it yet, walk them
through the three steps above and pause until they do.

## Step 2: Clone the astrodb-web Repository

Ask the user to confirm the directory name to use for their website, suggesting `website/`.
Then clone the repository into that directory using the user provided repo URL:

```bash
git clone https://github.com/<you>/<your-website> website
```

## Step 3: Set up the Website Configuration

Use the bundled setup script to generate the `.env` file. You must point it to the database file and the directory where you cloned the website.

### Step 3.1: Verify Table and Column Names (Crucial)

Before running the setup script, verify the primary table name and coordinate columns to ensure the web interface correctly maps the data.

1. **Check for primary table**: Run `sqlite3 <path-to-your-db>.sqlite ".tables"`
   - If a table named `Sources` or `sources` is not found, **identify the most likely primary table** or ask the user.
2. **Check coordinate columns**: Run `sqlite3 <path-to-your-db>.sqlite "PRAGMA table_info(<primary_table>);"`
   - Identify the RA and Dec column names (e.g., `ra` vs `ra_deg`). If they are missing, the website may fail to render maps.
3. **Identify Foreign Keys**: Check if there's a configuration file (like `database.toml`) that defines `lookup_tables` or foreign key relationships to ensure multi-table views work.

### Step 3.2: Run Setup Script

Check the script location (eg, .agents/skills, .claude/skills or similar) and run the script with the verified table and column names:

```bash
uv run python .agents/skills/astrodb-website/scripts/setup_website.py \
  --db-path <path-to-your-db>.sqlite \
  --website-dir website/ \
  --primary-table <primary_table_name> \
  --ra-col <ra_column_name> \
  --dec-col <dec_column_name> \
  --source-col <source_column_name> \
  --fk-col <foreign_key_column_name>
```

### Step 3.3: Validate .env Persistence (Crucial)

Immediately after running the script, **cat the generated `.env` file** to ensure it contains the expected values:
- `ASTRO_WEB_DATABASE_URL` (should be an absolute `sqlite:///` path).
- `ASTRO_WEB_PRIMARY_TABLE`
- `ASTRO_WEB_RA_COLUMN` / `ASTRO_WEB_DEC_COLUMN`

If the `.env` is empty or missing these keys, re-run Step 3.2.

## Step 4: Install Dependencies and Start the Server

```bash
cd website/
uv sync
uv run serve
```

*Note: `uv run serve` typically starts uvicorn on port 8000.*

## Step 5: Verify the Website

You **MUST** verify the website is actually serving data before finishing.

1. **Start in background** if needed: `uv run uvicorn astro_web.main:app --port 8000 &`
2. **Wait and Check**: Give it a few seconds to initialize, then:
   ```bash
   curl -s http://localhost:8000/browse | grep -i "<table"
   ```

**Failure Recovery:**
- If `curl` returns nothing or an error, check the server output/logs.
- **Common issue**: Table name case sensitivity (`Galaxies` vs `galaxies`).
- **Common issue**: Relative paths in `.env`. Ensure `ASTRO_WEB_DATABASE_URL` uses an absolute path.

## Step 6: Report Success

Inform the user that the website is running at **http://localhost:8000**.
Remind them they can stop the server with `Ctrl+C`.

## Step 7: Provide Advice on Next Steps

Notify the user that changes to the sqlite binary file should be reflected in the website. They may need to restart the server if changes are not reflected.

Notify the user that their next step should be to set up a permanent hosting solution for production use, such as using a cloud provider or a dedicated server.

## Troubleshooting

- **Database not found**: Ensure the `--db-path` provided to `setup_website.py` is correct.
- **Port already in use**: If 8000 is taken, use `--port <other-port>` with uvicorn.
- **Import errors**: Ensure `uv sync` was run in the `astrodb-web` directory.

---
name: astrodb-website
description: Set up and run a web interface for an AstroDB database using the Astro-Web template. Use this skill whenever a user wants to "view the database in a browser", "start the web interface", "see the data", or "set up the website".
compatibility: python, fastapi, uvicorn
---

# AstroDB Website

This skill sets up a FastAPI web interface ([Astro-Web](https://github.com/astrodbtoolkit/Astro-Web)) in your project directory to browse and visualize an AstroDB SQLite database.

## Prerequisites

- An existing AstroDB SQLite database (`.sqlite` or `.db`).
- `uv` installed.
- Python 3.13+.

## Step 1: Clone the Astro-Web Repository

The website should be set up in a directory named `website/` (or similar) in your project root. If it doesn't exist, clone it:

```bash
git clone https://github.com/astrodbtoolkit/Astro-Web website
```

## Step 2: Set up the Website Configuration

Use the bundled setup script to generate the `.env` file. You must point it to the database file and the directory where you cloned the website.

### Step 2.1: Verify Table and Column Names (Crucial)

Before running the setup script, verify the primary table name and coordinate columns:

1. **Check for primary table**: Run `sqlite3 <path-to-your-db>.sqlite ".tables"`
   - If a table named `Sources` or `sources` is not found, **ask the user** what the primary sources table is.
2. **Check coordinate columns**: Run `sqlite3 <path-to-your-db>.sqlite "PRAGMA table_info(<primary_table>);"`
   - Identify the RA and Dec column names (e.g., `ra` vs `ra_deg`).

### Step 2.2: Run Setup Script

Run the script with the verified table and column names:

```bash
uv run python .claude/skills/astrodb-website/scripts/setup_website.py \
  --db-path <path-to-your-db>.sqlite \
  --website-dir website/ \
  --primary-table <primary_table_name> \
  --ra-col <ra_column_name> \
  --dec-col <dec_column_name>
```

The script will:
1. Create a `.env` file inside `website/`.
2. Configure it to point to your database.
3. Read `lookup_tables` from `database.toml` if it exists.
4. Set the primary table and coordinate column names.

## Step 3: Install Dependencies and Start the Server

```bash
cd website/
uv sync
uv run serve
```

Alternatively, you can run it manually with:
```bash
uv run uvicorn astro_web.main:app --reload --port 8000
```

## Step 4: Verify the Website

After starting the server, verify that the `/browse` endpoint is accessible and returns the expected content. You should run the server in the background or use a separate command to check it.

```bash
# Verify the browse endpoint
curl -s http://localhost:8000/browse | grep -i "<table"
```

Verify that:
1. The response is valid HTML.
2. It contains a `<table>` (the sources list).

If the verification fails, check the server logs and verify your `.env` configuration.

## Step 5: Report Success

Inform the user that the website is running at **http://localhost:8000**.
Remind them they can stop the server with `Ctrl+C`.

## Troubleshooting

- **Database not found**: Ensure the `--db-path` provided to `setup_website.py` is correct.
- **Port already in use**: If 8000 is taken, use `--port <other-port>` with uvicorn.
- **Import errors**: Ensure `uv sync` was run in the `Astro-Web` directory.

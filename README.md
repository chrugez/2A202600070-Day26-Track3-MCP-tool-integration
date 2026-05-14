# Lab: Build a Database MCP Server with FastMCP and SQLite

## Goal

Build a Model Context Protocol (MCP) server using FastMCP that exposes a small database through:

- `search`
- `insert`
- `aggregate`

You must also expose the database schema as an MCP resource, test the server with Inspector or equivalent tooling, and show the server working from at least one MCP client.

## Learning Outcomes

By the end of this lab, students should be able to:

- explain what MCP tools and resources are
- build a FastMCP server in Python
- connect FastMCP to a SQLite database
- safely validate database requests before executing SQL
- expose dynamic schema context through `@mcp.resource(...)`
- test tool schemas, normal calls, and error responses
- connect the server to an MCP client such as Claude Code, Codex, or Gemini CLI

## Required Features

### Part 1: MCP Server

Implement a FastMCP server that exposes exactly these tool categories:

1. `search`
2. `insert`
3. `aggregate`

Your server may use SQLite for the main implementation. If you want to support PostgreSQL too, design the code so the database layer can be swapped later.

### Part 2: Resource

Expose database schema information as MCP resources:

- one resource for the full database schema
- one dynamic resource template for a single table schema

Suggested URIs:

- `schema://database`
- `schema://table/{table_name}`

### Part 3: Validation and Error Handling

Your tools must reject unsafe or invalid requests:

- unknown table names
- unknown column names
- unsupported filter operators
- invalid aggregate requests
- empty inserts

Do not build SQL by blindly concatenating raw user input.

### Part 4: Testing and Verification

Verify all of the following:

1. the server starts correctly
2. the three tools are discoverable
3. the schema resource is discoverable
4. valid tool calls return useful results
5. invalid tool calls return clear errors
6. at least one MCP client can connect and use the server

### Part 5: Demo Deliverables

Prepare:

- GitHub repository
- setup instructions
- tool descriptions
- testing steps
- at least one client configuration example
- short demo video, around 2 minutes

Inspector screenshots are recommended if you use MCP Inspector.

## Suggested Project Structure

```text
implementation/
  db.py
  init_db.py
  mcp_server.py
  verify_server.py
  tests/
    test_server.py
```

## Recommended Data Model

Use a small relational dataset so `search`, `insert`, and `aggregate` are easy to demo. Example:

- `students`
- `courses`
- `enrollments`

## Example Tasks to Demonstrate

- search all students in cohort `A1`
- insert a new student
- count rows in a table
- compute average score by cohort
- read the full schema resource
- read `schema://table/students`
- show an invalid request, such as searching a missing table

## FastMCP and Inspector References

- FastMCP quickstart: https://gofastmcp.com/v2/getting-started/quickstart
- FastMCP resources: https://gofastmcp.com/v2/servers/resources
- MCP Inspector: https://modelcontextprotocol.io/docs/tools/inspector

## Client Setup Notes

### Claude Code

Anthropic documents local JSON config and `claude mcp add` flows here:

- https://code.claude.com/docs/en/mcp

Claude Code supports MCP resources via `@server:resource-uri` references and supports environment variable expansion in `.mcp.json`.

### Codex

OpenAI documents Codex MCP setup here:

- https://developers.openai.com/learn/docs-mcp

Codex supports MCP server configuration through the CLI and `~/.codex/config.toml`.

### Gemini CLI

Gemini CLI has a built-in MCP manager. In the verified local workflow, the simplest path is:

```bash
gemini mcp add sqlite-lab /ABSOLUTE/PATH/TO/python /ABSOLUTE/PATH/TO/implementation/mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
```

Gemini CLI also documents configuration details here:

- https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md

Expected outcome:

- the server appears as `Connected`
- Gemini can discover `search`, `insert`, and `aggregate`
- a headless smoke test works with `gemini --allowed-mcp-server-names sqlite-lab --yolo -p "..."`

### Antigravity

Antigravity commonly uses an `mcp_config.json` file with a shape similar to Gemini CLI. Verify the current product behavior in your installed version before grading against exact UI steps.

## Deliverable Checklist

- working FastMCP server
- SQLite database and seed data
- `search`, `insert`, `aggregate` tools
- schema resource and schema resource template
- verification steps
- automated tests or repeatable verification script
- client configuration example
- README with setup and demo steps
- Inspector startup command or helper script
- at least one verified Gemini CLI or Claude/Codex client test

## Bonus

Optional bonus:

- add authentication for SSE or HTTP transport
- support both SQLite and PostgreSQL with the same MCP surface
- add richer output annotations or pagination

## Reference Implementation

This repository includes a complete SQLite + FastMCP implementation in `implementation/`.

### Project Layout

```text
implementation/
  db.py                 # SQLite adapter, validation, safe query building
  init_db.py            # reproducible schema and seed data
  mcp_server.py         # FastMCP tools and resources
  verify_server.py      # repeatable smoke verification
  requirements.txt      # uv-installed dependencies
  tests/
    test_db.py          # automated adapter tests
```

The database file is created at `implementation/lab.db`.

### Setup With uv

Install `uv` first if it is not already available:

```bash
pip install uv
```

Create a virtual environment at the repository root:

```bash
uv venv .venv
```

Install dependencies:

```bash
uv pip install --no-cache -r implementation/requirements.txt
```

You can run all commands through `uv run` even if your shell has not activated `.venv`.

### Initialize The Database

```bash
uv run --no-cache python implementation/init_db.py
```

This command recreates the SQLite database with three tables:

- `students(id, name, cohort, email, created_at)`
- `courses(id, code, title, credits)`
- `enrollments(id, student_id, course_id, score, status)`

### Run Tests And Verification

Run automated tests:

```bash
uv run --no-cache pytest implementation/tests --basetemp .pytest-tmp -p no:cacheprovider
```

Run the repeatable smoke verification:

```bash
uv run --no-cache python implementation/verify_server.py
```

Run MCP-level verification:

```bash
uv run --no-cache python implementation/verify_mcp.py
```

The verification scripts check:

- database initialization
- schema inspection
- valid `search`, `insert`, and `aggregate` calls
- clear rejection of an invalid table
- MCP discovery for tools, resources, and resource templates
- MCP calls through a real FastMCP client

### Run The MCP Server

```bash
uv run --no-cache python implementation/mcp_server.py
```

The server uses stdio transport by default.

### Tools

The server exposes exactly three MCP tools:

- `search(table, filters=None, columns=None, limit=20, offset=0, order_by=None, descending=False)`
- `insert(table, values)`
- `aggregate(table, metric, column=None, filters=None, group_by=None)`

Supported filter operators:

- `eq`
- `ne`
- `gt`
- `gte`
- `lt`
- `lte`
- `contains`
- `in`

Supported aggregate metrics:

- `count`
- `avg`
- `sum`
- `min`
- `max`

Example tool payloads:

```json
{
  "table": "students",
  "filters": {
    "cohort": "A1"
  },
  "order_by": "name"
}
```

```json
{
  "table": "students",
  "values": {
    "name": "Lan Ho",
    "cohort": "A1",
    "email": "lan.ho@example.edu"
  }
}
```

```json
{
  "table": "enrollments",
  "metric": "avg",
  "column": "score",
  "group_by": "status"
}
```

### Resources

The server exposes database schema context as MCP resources:

- `schema://database`
- `schema://table/{table_name}`

Examples:

- `schema://database`
- `schema://table/students`

### Safety Behavior

The implementation rejects:

- unknown table names
- unknown column names
- unsupported filter operators
- empty inserts
- invalid aggregate metrics
- aggregate calls missing required columns
- invalid `limit`, `offset`, `order_by`, or `group_by`

SQL values are passed through SQLite parameters. Table and column identifiers are only used after validation against the live database schema.

## MCP Inspector

Run Inspector from the repository root:

```bash
npx -y @modelcontextprotocol/inspector uv run --no-cache python implementation/mcp_server.py
```

Inspector checklist:

- `search`, `insert`, and `aggregate` appear in the tools list
- `schema://database` appears in resources
- `schema://table/{table_name}` appears as a resource template
- valid tool calls succeed
- invalid tool calls return clear errors

## Codex Client Setup

Codex is the primary client for this lab submission.

Add this MCP server to `~/.codex/config.toml`. Replace the path if your checkout is in a different location.

```toml
[mcp_servers.sqlite_lab]
command = "uv"
args = ["run", "--no-cache", "python", "D:/AI/26AI/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"]
```

Recommended project instruction in `AGENTS.md`:

```md
Use the `sqlite_lab` MCP server whenever the task needs database schema context or SQL-backed record lookup.
```

Suggested Codex verification prompts:

```text
Use the sqlite_lab MCP server and read schema://database.
```

```text
Use the sqlite_lab MCP server to search students in cohort A1.
```

```text
Use the sqlite_lab MCP server to compute average enrollment score grouped by status.
```

```text
Use the sqlite_lab MCP server to search a missing table and show the error.
```

## Two Minute Demo Script

1. Show `implementation/` structure and `requirements.txt`.
2. Run `uv run --no-cache python implementation/init_db.py`.
3. Run `uv run --no-cache pytest implementation/tests --basetemp .pytest-tmp -p no:cacheprovider`.
4. Run `uv run --no-cache python implementation/verify_server.py`.
5. Run `uv run --no-cache python implementation/verify_mcp.py` and show discovered tools/resources.
6. Open Inspector and show the three tools plus schema resources.
7. Call valid `search`, `insert`, and `aggregate`.
8. Call an invalid table and show the clear error.
9. Show Codex configured with `sqlite_lab` and using the server.

## Demo Evidence Checklist

Include at least one screenshot or short clip showing:

- Inspector or Codex discovering `search`, `insert`, and `aggregate`.
- Inspector or Codex reading `schema://database`.
- A successful `search` or `aggregate` call.
- A failing call against `missing_table` with the clear error.

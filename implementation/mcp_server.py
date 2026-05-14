from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from db import DEFAULT_DB_PATH, SQLiteAdapter, ValidationError
from init_db import create_database


if not Path(DEFAULT_DB_PATH).exists():
    create_database(DEFAULT_DB_PATH)

adapter = SQLiteAdapter(DEFAULT_DB_PATH)
mcp = FastMCP("SQLite Lab MCP Server")


@mcp.tool(name="search")
def search(
    table: str,
    filters: Any = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows in a validated table with optional filters, ordering, and pagination."""
    try:
        return adapter.search(
            table=table,
            filters=filters,
            columns=columns,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one row into a validated table and return the inserted payload."""
    try:
        return adapter.insert(table=table, values=values)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: Any = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    """Run a safe aggregate query over one validated table."""
    try:
        return adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return the full SQLite schema as JSON text."""
    return json.dumps(adapter.describe_database(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return one table schema as JSON text."""
    try:
        payload = {"table": table_name, "columns": adapter.get_table_schema(table_name)}
        return json.dumps(payload, indent=2)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run()

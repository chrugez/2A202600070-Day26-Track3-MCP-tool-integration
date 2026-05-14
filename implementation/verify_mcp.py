from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastmcp import Client

from init_db import create_database
from mcp_server import DEFAULT_DB_PATH, mcp


def _jsonable(value: Any) -> Any:
    if hasattr(value, "data"):
        return _jsonable(value.data)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


async def main() -> None:
    create_database(DEFAULT_DB_PATH)

    async with Client(mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        resource_templates = await client.list_resource_templates()

        tool_names = {tool.name for tool in tools}
        resource_uris = {str(resource.uri) for resource in resources}
        template_uris = {str(template.uriTemplate) for template in resource_templates}

        assert {"search", "insert", "aggregate"} <= tool_names
        assert "schema://database" in resource_uris
        assert "schema://table/{table_name}" in template_uris

        schema = await client.read_resource("schema://database")
        students_schema = await client.read_resource("schema://table/students")
        search_result = await client.call_tool(
            "search",
            {"table": "students", "filters": {"cohort": "A1"}, "order_by": "name"},
        )
        insert_result = await client.call_tool(
            "insert",
            {
                "table": "students",
                "values": {
                    "name": "MCP Client Student",
                    "cohort": "A1",
                    "email": "mcp.client.student@example.edu",
                },
            },
        )
        aggregate_result = await client.call_tool(
            "aggregate",
            {
                "table": "enrollments",
                "metric": "avg",
                "column": "score",
                "group_by": "status",
            },
        )

        invalid_error = ""
        try:
            logging.disable(logging.CRITICAL)
            await client.call_tool("search", {"table": "missing_table"})
        except Exception as exc:
            invalid_error = str(exc)
        finally:
            logging.disable(logging.NOTSET)
        assert "unknown table" in invalid_error

    report = {
        "discovered_tools": sorted(tool_names),
        "discovered_resources": sorted(resource_uris),
        "discovered_resource_templates": sorted(template_uris),
        "schema_database": _jsonable(schema),
        "schema_students": _jsonable(students_schema),
        "search_students_a1": _jsonable(search_result),
        "insert_student": _jsonable(insert_result),
        "aggregate_avg_score_by_status": _jsonable(aggregate_result),
        "invalid_table_error": invalid_error,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

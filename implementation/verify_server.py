from __future__ import annotations

import json

from db import DEFAULT_DB_PATH, SQLiteAdapter, ValidationError
from init_db import create_database


def main() -> None:
    create_database(DEFAULT_DB_PATH)
    adapter = SQLiteAdapter(DEFAULT_DB_PATH)

    checks = {
        "tables": adapter.list_tables(),
        "schema_resource_payload": adapter.describe_database(),
        "search_students_a1": adapter.search("students", filters={"cohort": "A1"}, order_by="name"),
        "search_top_scores": adapter.search("enrollments", limit=2, order_by="score", descending=True),
        "insert_student": adapter.insert(
            "students",
            {
                "name": "Test Student",
                "cohort": "A1",
                "email": "test.student@example.edu",
            },
        ),
        "count_students": adapter.aggregate("students", "count"),
        "avg_score_by_status": adapter.aggregate("enrollments", "avg", column="score", group_by="status"),
    }

    try:
        adapter.search("missing_table")
    except ValidationError as exc:
        checks["invalid_table_error"] = str(exc)
    else:
        raise AssertionError("invalid table check did not fail")

    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()

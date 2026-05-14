from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import SQLiteAdapter, ValidationError
from init_db import create_database


@pytest.fixture()
def adapter(tmp_path: Path) -> SQLiteAdapter:
    db_path = tmp_path / "lab.db"
    create_database(db_path)
    return SQLiteAdapter(db_path)


def test_init_database_is_repeatable(tmp_path: Path) -> None:
    db_path = tmp_path / "lab.db"
    create_database(db_path)
    create_database(db_path)
    adapter = SQLiteAdapter(db_path)

    assert adapter.list_tables() == ["courses", "enrollments", "students"]


def test_search_students_by_cohort(adapter: SQLiteAdapter) -> None:
    result = adapter.search("students", filters={"cohort": "A1"}, order_by="name")

    assert result["table"] == "students"
    assert result["count"] == 2
    assert {row["name"] for row in result["rows"]} == {"An Nguyen", "Binh Tran"}


def test_search_enrollments_ordered_and_limited(adapter: SQLiteAdapter) -> None:
    result = adapter.search("enrollments", limit=2, order_by="score", descending=True)

    assert result["count"] == 2
    assert result["rows"][0]["score"] >= result["rows"][1]["score"]


def test_insert_student_returns_inserted_row(adapter: SQLiteAdapter) -> None:
    result = adapter.insert(
        "students",
        {
            "name": "Lan Ho",
            "cohort": "A1",
            "email": "lan.ho@example.edu",
        },
    )

    assert result["inserted"]["id"]
    assert result["inserted"]["name"] == "Lan Ho"


def test_aggregate_count_students(adapter: SQLiteAdapter) -> None:
    result = adapter.aggregate("students", "count")

    assert result["rows"] == [{"value": 5}]


def test_aggregate_average_score_by_status(adapter: SQLiteAdapter) -> None:
    result = adapter.aggregate("enrollments", "avg", column="score", group_by="status")

    assert {row["group_key"] for row in result["rows"]} == {"active", "completed", "dropped"}
    assert all(row["value"] is not None for row in result["rows"])


@pytest.mark.parametrize(
    ("operation", "expected_message"),
    [
        (lambda db: db.search("missing"), "unknown table"),
        (lambda db: db.search("students", columns=["missing"]), "unknown column"),
        (lambda db: db.search("students", filters={"cohort": {"startswith": "A"}}), "unsupported filter operator"),
        (lambda db: db.aggregate("students", "median", column="id"), "unsupported aggregate metric"),
        (lambda db: db.aggregate("students", "avg"), "avg requires a column"),
        (lambda db: db.insert("students", {}), "insert values must be a non-empty object"),
    ],
)
def test_invalid_requests_are_rejected(adapter: SQLiteAdapter, operation, expected_message: str) -> None:
    with pytest.raises(ValidationError, match=expected_message):
        operation(adapter)

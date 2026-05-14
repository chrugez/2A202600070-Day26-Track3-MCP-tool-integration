from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).with_name("lab.db")


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    ALLOWED_OPERATORS = {
        "eq": "=",
        "ne": "!=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "contains": "LIKE",
        "in": "IN",
    }
    ALLOWED_METRICS = {"count", "avg", "sum", "min", "max"}
    NUMERIC_TYPES = {"INTEGER", "REAL", "NUMERIC", "DECIMAL", "FLOAT", "DOUBLE"}

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = OFF")
        return connection

    def list_tables(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        self._validate_table(table)
        with self.connect() as connection:
            rows = connection.execute(f"PRAGMA table_info({self._quote_identifier(table)})").fetchall()
        return [
            {
                "name": row["name"],
                "type": row["type"],
                "not_null": bool(row["notnull"]),
                "default": row["dflt_value"],
                "primary_key": bool(row["pk"]),
            }
            for row in rows
        ]

    def describe_database(self) -> dict[str, Any]:
        return {
            "database": str(self.db_path),
            "tables": {table: self.get_table_schema(table) for table in self.list_tables()},
        }

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: Any = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        self._validate_table(table)
        selected_columns = self._validate_columns(table, columns) if columns else ["*"]
        self._validate_limit_offset(limit, offset)

        select_sql = "*" if selected_columns == ["*"] else ", ".join(self._quote_identifier(c) for c in selected_columns)
        where_sql, params = self._build_where_clause(table, filters)

        order_sql = ""
        if order_by:
            self._validate_column(table, order_by)
            direction = "DESC" if descending else "ASC"
            order_sql = f" ORDER BY {self._quote_identifier(order_by)} {direction}"

        sql = (
            f"SELECT {select_sql} FROM {self._quote_identifier(table)}"
            f"{where_sql}{order_sql} LIMIT ? OFFSET ?"
        )
        with self.connect() as connection:
            rows = connection.execute(sql, [*params, limit, offset]).fetchall()

        return {
            "table": table,
            "count": len(rows),
            "rows": [dict(row) for row in rows],
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        self._validate_table(table)
        if not isinstance(values, dict) or not values:
            raise ValidationError("insert values must be a non-empty object")

        columns = list(values.keys())
        self._validate_columns(table, columns)
        column_sql = ", ".join(self._quote_identifier(column) for column in columns)
        placeholder_sql = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {self._quote_identifier(table)} ({column_sql}) VALUES ({placeholder_sql})"

        with self.connect() as connection:
            cursor = connection.execute(sql, [values[column] for column in columns])
            row_id = cursor.lastrowid
            connection.commit()
            inserted = self._fetch_inserted_row(connection, table, values, row_id)

        return {"table": table, "inserted": inserted}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: Any = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        self._validate_table(table)
        metric = metric.lower()
        if metric not in self.ALLOWED_METRICS:
            raise ValidationError(f"unsupported aggregate metric: {metric}")

        target_sql = "*"
        if metric != "count":
            if not column:
                raise ValidationError(f"{metric} requires a column")
            self._validate_column(table, column)
            if metric in {"avg", "sum"} and not self._is_numeric_column(table, column):
                raise ValidationError(f"{metric} requires a numeric column")
            target_sql = self._quote_identifier(column)
        elif column and column != "*":
            self._validate_column(table, column)
            target_sql = self._quote_identifier(column)

        select_parts = []
        group_sql = ""
        if group_by:
            self._validate_column(table, group_by)
            group_identifier = self._quote_identifier(group_by)
            select_parts.append(f"{group_identifier} AS group_key")
            group_sql = f" GROUP BY {group_identifier}"

        select_parts.append(f"{metric.upper()}({target_sql}) AS value")
        where_sql, params = self._build_where_clause(table, filters)
        sql = f"SELECT {', '.join(select_parts)} FROM {self._quote_identifier(table)}{where_sql}{group_sql}"

        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        return {
            "table": table,
            "metric": metric,
            "column": column,
            "group_by": group_by,
            "rows": [dict(row) for row in rows],
        }

    def _fetch_inserted_row(
        self,
        connection: sqlite3.Connection,
        table: str,
        values: dict[str, Any],
        row_id: int,
    ) -> dict[str, Any]:
        schema = self.get_table_schema(table)
        primary_keys = [column["name"] for column in schema if column["primary_key"]]
        if len(primary_keys) == 1 and primary_keys[0] in values:
            pk = primary_keys[0]
            row = connection.execute(
                f"SELECT * FROM {self._quote_identifier(table)} WHERE {self._quote_identifier(pk)} = ?",
                [values[pk]],
            ).fetchone()
        else:
            row = connection.execute(
                f"SELECT * FROM {self._quote_identifier(table)} WHERE rowid = ?",
                [row_id],
            ).fetchone()
        return dict(row) if row else dict(values)

    def _build_where_clause(self, table: str, filters: Any) -> tuple[str, list[Any]]:
        normalized_filters = self._normalize_filters(filters)
        if not normalized_filters:
            return "", []

        clauses: list[str] = []
        params: list[Any] = []
        for item in normalized_filters:
            column = item["column"]
            operator = item.get("op", "eq")
            value = item.get("value")
            self._validate_column(table, column)
            if operator not in self.ALLOWED_OPERATORS:
                raise ValidationError(f"unsupported filter operator: {operator}")

            column_sql = self._quote_identifier(column)
            if operator == "contains":
                clauses.append(f"{column_sql} LIKE ?")
                params.append(f"%{value}%")
            elif operator == "in":
                if not isinstance(value, list) or not value:
                    raise ValidationError("in filter value must be a non-empty list")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f"{column_sql} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{column_sql} {self.ALLOWED_OPERATORS[operator]} ?")
                params.append(value)

        return f" WHERE {' AND '.join(clauses)}", params

    def _normalize_filters(self, filters: Any) -> list[dict[str, Any]]:
        if filters in (None, {}, []):
            return []
        if isinstance(filters, list):
            normalized = []
            for item in filters:
                if not isinstance(item, dict) or "column" not in item:
                    raise ValidationError("each filter must include a column")
                normalized.append(
                    {
                        "column": item["column"],
                        "op": item.get("op", "eq"),
                        "value": item.get("value"),
                    }
                )
            return normalized
        if isinstance(filters, dict):
            normalized = []
            for column, spec in filters.items():
                if isinstance(spec, dict) and "op" in spec:
                    normalized.append({"column": column, "op": spec["op"], "value": spec.get("value")})
                elif isinstance(spec, dict):
                    for operator, value in spec.items():
                        normalized.append({"column": column, "op": operator, "value": value})
                else:
                    normalized.append({"column": column, "op": "eq", "value": spec})
            return normalized
        raise ValidationError("filters must be an object or list")

    def _validate_table(self, table: str) -> None:
        if table not in self.list_tables():
            raise ValidationError(f"unknown table: {table}")

    def _validate_columns(self, table: str, columns: list[str]) -> list[str]:
        if not isinstance(columns, list) or not columns:
            raise ValidationError("columns must be a non-empty list")
        for column in columns:
            self._validate_column(table, column)
        return columns

    def _validate_column(self, table: str, column: str) -> None:
        schema_columns = {item["name"] for item in self.get_table_schema(table)}
        if column not in schema_columns:
            raise ValidationError(f"unknown column for {table}: {column}")

    def _validate_limit_offset(self, limit: int, offset: int) -> None:
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValidationError("limit must be an integer between 1 and 100")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset must be a non-negative integer")

    def _is_numeric_column(self, table: str, column: str) -> bool:
        for item in self.get_table_schema(table):
            if item["name"] == column:
                declared_type = (item["type"] or "").upper()
                return any(type_name in declared_type for type_name in self.NUMERIC_TYPES)
        return False

    def _quote_identifier(self, identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

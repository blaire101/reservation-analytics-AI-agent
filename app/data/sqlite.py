from __future__ import annotations

import csv
from pathlib import Path
import sqlite3
from typing import Any

from app.settings import ROOT, Settings


INTEGER_COLUMNS = {
    "fid",
    "fcampaign_status",
    "fis_active",
    "freserve_flag",
    "forder_flag",
    "ftag_reserved_not_paid",
}


class SQLiteBackend:
    """Local backend seeded from sample CSV files for deterministic demos/tests."""

    name = "sqlite"

    def __init__(self, settings: Settings):
        self.path = settings.sqlite_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.seed_from_sample_data()

    def execute(self, sql: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(sql).fetchall()
        return [dict(row) for row in rows]

    def seed_from_sample_data(self) -> None:
        csv_files = sorted((ROOT / "sample_data").glob("*.csv"))
        with sqlite3.connect(self.path) as connection:
            for csv_file in csv_files:
                self._replace_table_from_csv(connection, csv_file)
            connection.commit()

    def _replace_table_from_csv(
        self,
        connection: sqlite3.Connection,
        csv_file: Path,
    ) -> None:
        columns, rows = self._read_csv(csv_file)
        table_name = csv_file.stem

        connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        schema = ", ".join(
            f'"{column}" {self._sqlite_type(column)}'
            for column in columns
        )
        connection.execute(f'CREATE TABLE "{table_name}" ({schema})')

        if not rows:
            return

        placeholders = ",".join("?" for _ in columns)
        values = [
            [self._convert_value(column, row[column]) for column in columns]
            for row in rows
        ]
        connection.executemany(
            f'INSERT INTO "{table_name}" VALUES ({placeholders})',
            values,
        )

    @staticmethod
    def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return list(reader.fieldnames or []), list(reader)

    @staticmethod
    def _sqlite_type(column: str) -> str:
        return "INTEGER" if column in INTEGER_COLUMNS else "TEXT"

    @staticmethod
    def _convert_value(column: str, value: str) -> int | str:
        if column in INTEGER_COLUMNS and value:
            return int(value)
        return value

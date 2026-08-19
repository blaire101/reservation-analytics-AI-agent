"""Local SQLite backend used for deterministic demos and unit tests."""

from __future__ import annotations

import csv
from pathlib import Path
import sqlite3
from typing import Any

from app.settings import ROOT, Settings


# These CSV columns should be created as SQLite INTEGER fields; all other demo
# columns are created as TEXT to keep local setup intentionally simple.
INTEGER_COLUMNS = {
    'fid',
    'fcampaign_status',
    'fis_active',
    'freserve_flag',
    'forder_flag',
    'ftag_reserved_not_paid',
}


class SQLiteBackend:
    """Provide a local query backend with sample data loaded from CSV files."""

    name = 'sqlite'

    def __init__(self, settings: Settings):
        """Prepare the local database and load deterministic sample tables."""
        self.path = settings.sqlite_path
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Rebuild demo tables from sample_data so local behavior is repeatable.
        self.seed_from_sample_data()

    def execute(self, sql: str) -> list[dict[str, Any]]:
        """Execute controlled SQL against SQLite and return dictionary rows."""
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(sql).fetchall()

        return [dict(row) for row in rows]

    def seed_from_sample_data(self) -> None:
        """Replace local SQLite tables with the CSV files in ``sample_data``.

        Flow:
            sample_data/*.csv
                -> infer simple schema
                -> DROP/CREATE table
                -> INSERT rows
        """
        with sqlite3.connect(self.path) as connection:
            for csv_file in sorted((ROOT / 'sample_data').glob('*.csv')):
                self._replace_table(connection, csv_file)

            connection.commit()

    def _replace_table(self, connection, csv_file: Path) -> None:
        """Create one SQLite table whose name and rows come from one CSV file."""
        # Read the entire tiny demo CSV.
        with csv_file.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            rows = list(reader)

        table = csv_file.stem

        # Keep local seeding deterministic: replace the table completely.
        connection.execute(f'DROP TABLE IF EXISTS "{table}"')

        schema = ', '.join(
            f'"{column}" {"INTEGER" if column in INTEGER_COLUMNS else "TEXT"}'
            for column in columns
        )
        connection.execute(f'CREATE TABLE "{table}" ({schema})')

        if not rows:
            return

        placeholders = ','.join('?' for _ in columns)

        # Convert known integer fields; keep all other values as text.
        values = [
            [
                int(row[column])
                if column in INTEGER_COLUMNS and row[column]
                else row[column]
                for column in columns
            ]
            for row in rows
        ]

        connection.executemany(
            f'INSERT INTO "{table}" VALUES ({placeholders})',
            values,
        )

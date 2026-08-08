from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any

from app.settings import ROOT, Settings


class SQLiteBackend:
    name = "sqlite"

    def __init__(self, settings: Settings):
        self.path = settings.sqlite_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.seed()

    @staticmethod
    def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return list(reader.fieldnames or []), list(reader)

    def seed(self) -> None:
        sources = {
            "dim_campaign": ROOT / "sample_data" / "dim_campaign.csv",
            "dm_reservation_conversion": ROOT / "sample_data" / "dm_reservation_conversion.csv",
        }

        with sqlite3.connect(self.path) as con:
            for table, path in sources.items():
                columns, rows = self._rows(path)
                con.execute(f'DROP TABLE IF EXISTS "{table}"')

                integer_cols = {"reserve_flag", "order_flag", "reserved_not_ordered_flag"}
                schema = ", ".join(
                    f'"{col}" {"INTEGER" if col in integer_cols else "TEXT"}'
                    for col in columns
                )
                con.execute(f'CREATE TABLE "{table}" ({schema})')

                if rows:
                    placeholders = ",".join("?" for _ in columns)
                    values = []
                    for row in rows:
                        values.append([
                            int(row[col]) if col in integer_cols else row[col]
                            for col in columns
                        ])
                    con.executemany(
                        f'INSERT INTO "{table}" VALUES ({placeholders})', values
                    )
            con.commit()

    def execute(self, sql: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            return [dict(row) for row in con.execute(sql).fetchall()]

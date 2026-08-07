from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any

from app.config import AppSettings


class SQLiteBackend:
    """Default local SQL backend.

    It creates a real SQLite database from the sample DIM + DM CSV files. This
    lets the agent execute controlled SQL against a constructed Reservation Data
    Mart without AWS or an internal company data platform.
    """

    name = "sqlite"

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.db_path = settings.sqlite_file
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if settings.local_seed_on_start or not self.db_path.exists():
            self.seed()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row

        # Compatibility helpers so the controlled SQL templates stay close to
        # Athena/Trino syntax in this project project.
        con.create_function("month", 1, lambda x: int(str(x)[5:7]) if x else None)
        con.create_function("year", 1, lambda x: int(str(x)[:4]) if x else None)

        # Allow reservation_dm.table and reservation_dim.table qualified names.
        path = str(self.db_path).replace("'", "''")
        con.execute(f"ATTACH DATABASE '{path}' AS reservation_dm")
        con.execute(f"ATTACH DATABASE '{path}' AS reservation_dim")
        return con

    @staticmethod
    def _load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            return list(reader.fieldnames or []), rows

    def seed(self) -> None:
        campaign_cols, campaign_rows = self._load_csv(self.settings.mock_campaign_file)
        dm_cols, dm_rows = self._load_csv(self.settings.mock_dm_file)

        with sqlite3.connect(self.db_path) as con:
            con.execute(f'DROP TABLE IF EXISTS "{self.settings.campaign_table}"')
            con.execute(f'DROP TABLE IF EXISTS "{self.settings.dm_table}"')

            campaign_schema = ", ".join(f'"{c}" TEXT' for c in campaign_cols)
            con.execute(
                f'CREATE TABLE "{self.settings.campaign_table}" ({campaign_schema})'
            )
            if campaign_rows:
                placeholders = ",".join("?" for _ in campaign_cols)
                con.executemany(
                    f'INSERT INTO "{self.settings.campaign_table}" VALUES ({placeholders})',
                    [[r.get(c, "") for c in campaign_cols] for r in campaign_rows],
                )

            integer_cols = {"reserve_flag", "order_flag", "tag_reserved_not_paid"}
            dm_schema = ", ".join(
                f'"{c}" {"INTEGER" if c in integer_cols else "TEXT"}' for c in dm_cols
            )
            con.execute(f'CREATE TABLE "{self.settings.dm_table}" ({dm_schema})')
            if dm_rows:
                placeholders = ",".join("?" for _ in dm_cols)
                values = []
                for r in dm_rows:
                    values.append([
                        int(r[c]) if c in integer_cols and r.get(c, "") != "" else r.get(c, "")
                        for c in dm_cols
                    ])
                con.executemany(
                    f'INSERT INTO "{self.settings.dm_table}" VALUES ({placeholders})',
                    values,
                )
            con.commit()

    def execute(self, sql: str, database: str) -> list[dict[str, Any]]:
        del database  # kept for the shared backend interface
        with self._connect() as con:
            cur = con.execute(sql)
            return [dict(row) for row in cur.fetchall()]

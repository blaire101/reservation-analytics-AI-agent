from __future__ import annotations

import json
from typing import Any
from urllib import request, error

from app.config import AppSettings


class SQLGatewayError(RuntimeError):
    pass


class InternalSQLGatewayClient:
    """Example adapter for an enterprise SQL gateway.

    Expected request contract (adapt to the company's real gateway):
      POST endpoint
      Authorization: Bearer <token>
      X-User-Id: <user_id>
      JSON: {sql, catalog, database, region, cluster}

    Expected response: {"rows": [{...}, ...]}
    """

    name = "internal_sql_gateway"

    def __init__(self, settings: AppSettings):
        self.settings = settings
        if not settings.sql_gateway_endpoint:
            raise ValueError("SQL_GATEWAY_ENDPOINT is required.")
        if not settings.sql_gateway_user_id:
            raise ValueError("SQL_GATEWAY_USER_ID is required.")
        if not settings.sql_gateway_token:
            raise ValueError("SQL_GATEWAY_TOKEN is required.")

    def execute(self, sql: str, database: str) -> list[dict[str, Any]]:
        payload = json.dumps({
            "sql": sql,
            "catalog": self.settings.sql_gateway_catalog,
            "database": database,
            "region": self.settings.data_region,
            "cluster": self.settings.data_cluster,
        }).encode("utf-8")

        req = request.Request(
            self.settings.sql_gateway_endpoint,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.sql_gateway_token}",
                "X-User-Id": self.settings.sql_gateway_user_id,
            },
        )
        try:
            with request.urlopen(req, timeout=self.settings.sql_gateway_timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except error.URLError as exc:
            raise SQLGatewayError(f"SQL gateway request failed: {exc}") from exc

        rows = body.get("rows")
        if not isinstance(rows, list):
            raise SQLGatewayError("SQL gateway response must contain a 'rows' list.")
        return rows

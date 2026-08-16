from __future__ import annotations

import json
import time
from typing import Any
import urllib.request

from app.settings import Settings


class AthenaBackend:
    """Remote QueryBackend implementation for AWS Athena."""

    name = "athena"

    def __init__(self, settings: Settings):
        self.settings = settings

    def execute(self, sql: str) -> list[dict[str, Any]]:
        import boto3

        client = boto3.client("athena", region_name=self.settings.aws_region)
        query_id = client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": self.settings.athena_database},
            WorkGroup=self.settings.athena_workgroup,
            ResultConfiguration={
                "OutputLocation": self.settings.athena_output_location,
            },
        )["QueryExecutionId"]

        self._wait_until_finished(client, query_id)
        result_set = client.get_query_results(
            QueryExecutionId=query_id
        )["ResultSet"]
        return self._rows_from_athena(result_set)

    @staticmethod
    def _wait_until_finished(client, query_id: str) -> None:
        while True:
            execution = client.get_query_execution(QueryExecutionId=query_id)
            state = execution["QueryExecution"]["Status"]["State"]

            if state == "SUCCEEDED":
                return
            if state in {"FAILED", "CANCELLED"}:
                raise RuntimeError(f"Athena query ended with state={state}")

            time.sleep(1)

    @staticmethod
    def _rows_from_athena(result_set: dict) -> list[dict[str, Any]]:
        rows = result_set.get("Rows", [])
        if not rows:
            return []

        headers = [
            item.get("VarCharValue", "")
            for item in rows[0]["Data"]
        ]
        return [
            dict(
                zip(
                    headers,
                    [item.get("VarCharValue") for item in row["Data"]],
                )
            )
            for row in rows[1:]
        ]


class SQLGatewayBackend:
    """Remote QueryBackend implementation for an internal HTTP SQL gateway."""

    name = "sql_gateway"

    def __init__(self, settings: Settings):
        if not settings.sql_gateway_endpoint:
            raise ValueError("SQL_GATEWAY_ENDPOINT is required.")
        self.settings = settings

    def execute(self, sql: str) -> list[dict[str, Any]]:
        request = urllib.request.Request(
            self.settings.sql_gateway_endpoint,
            data=self._payload(sql),
            headers=self._headers(),
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))

        if isinstance(body, list):
            return body
        return body.get("rows", [])

    def _payload(self, sql: str) -> bytes:
        return json.dumps(
            {
                "sql": sql,
                "region": self.settings.data_region,
                "cluster": self.settings.data_cluster,
            }
        ).encode("utf-8")

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-User-Id": self.settings.sql_gateway_user_id or "",
            "Authorization": f"Bearer {self.settings.sql_gateway_token or ''}",
        }

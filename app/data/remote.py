from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

from app.settings import Settings


class AthenaBackend:
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
            ResultConfiguration={"OutputLocation": self.settings.athena_output},
        )["QueryExecutionId"]

        while True:
            state = client.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]["Status"]["State"]
            if state == "SUCCEEDED":
                break
            if state in {"FAILED", "CANCELLED"}:
                raise RuntimeError(f"Athena query ended with state={state}")
            time.sleep(1)

        result = client.get_query_results(QueryExecutionId=query_id)["ResultSet"]
        rows = result.get("Rows", [])
        if not rows:
            return []
        headers = [x.get("VarCharValue", "") for x in rows[0]["Data"]]
        return [
            dict(zip(headers, [x.get("VarCharValue") for x in row["Data"]]))
            for row in rows[1:]
        ]


class SQLGatewayBackend:
    name = "sql_gateway"

    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.sql_gateway_endpoint:
            raise ValueError("SQL_GATEWAY_ENDPOINT is required.")

    def execute(self, sql: str) -> list[dict[str, Any]]:
        payload = json.dumps({
            "sql": sql,
            "region": self.settings.region,
            "cluster": self.settings.cluster,
        }).encode("utf-8")
        request = urllib.request.Request(
            self.settings.sql_gateway_endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-User-Id": self.settings.sql_gateway_user_id or "",
                "Authorization": f"Bearer {self.settings.sql_gateway_token or ''}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("rows", body if isinstance(body, list) else [])

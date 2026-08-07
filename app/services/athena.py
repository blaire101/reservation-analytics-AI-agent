from __future__ import annotations

import time
from typing import Any
import boto3

from app.config import AppSettings


class AthenaQueryError(RuntimeError):
    pass


class AthenaClient:
    name = "athena"

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.client = boto3.client("athena", region_name=settings.aws_region)

    def execute(self, sql: str, database: str) -> list[dict[str, Any]]:
        kwargs = {
            "QueryString": sql,
            "QueryExecutionContext": {"Database": database},
            "WorkGroup": self.settings.athena_workgroup,
        }
        if self.settings.athena_output and "CHANGE-ME" not in self.settings.athena_output:
            kwargs["ResultConfiguration"] = {
                "OutputLocation": self.settings.athena_output
            }

        response = self.client.start_query_execution(**kwargs)
        query_id = response["QueryExecutionId"]

        started = time.time()
        while True:
            status = self.client.get_query_execution(
                QueryExecutionId=query_id
            )["QueryExecution"]["Status"]
            state = status["State"]

            if state == "SUCCEEDED":
                break
            if state in {"FAILED", "CANCELLED"}:
                raise AthenaQueryError(
                    f"Athena query {query_id} {state}: "
                    f"{status.get('StateChangeReason', 'unknown reason')}"
                )
            if time.time() - started > self.settings.athena_timeout_seconds:
                self.client.stop_query_execution(QueryExecutionId=query_id)
                raise AthenaQueryError(f"Athena query timed out: {query_id}")

            time.sleep(self.settings.athena_poll_seconds)

        result = self.client.get_query_results(QueryExecutionId=query_id)
        rows = result["ResultSet"]["Rows"]
        if not rows:
            return []

        headers = [x.get("VarCharValue", "") for x in rows[0]["Data"]]
        output = []
        for row in rows[1:]:
            values = [x.get("VarCharValue") for x in row["Data"]]
            values += [None] * (len(headers) - len(values))
            output.append(dict(zip(headers, values)))
        return output


def sql_literal(value: str) -> str:
    # The LLM never produces arbitrary SQL. All queries are fixed templates,
    # and user values are escaped before interpolation.
    return "'" + value.replace("'", "''") + "'"

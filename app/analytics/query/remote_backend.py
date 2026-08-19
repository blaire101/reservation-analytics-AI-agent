"""Optional remote query adapters for AWS Athena and an internal SQL Gateway."""

from __future__ import annotations

import json
import time
from typing import Any
import urllib.request

from app.settings import Settings


class AthenaBackend:
    """Execute controlled analytics SQL through AWS Athena."""

    name = 'athena'

    def __init__(self, settings: Settings):
        """Store Athena region, database, workgroup, and result-location settings."""
        self.settings = settings

    def execute(self, sql: str) -> list[dict[str, Any]]:
        """Submit SQL to Athena, wait for completion, and normalize result rows.

        Flow:
            SQL
                -> start_query_execution
                -> poll query state
                -> get_query_results
                -> list[dict]
        """
        import boto3

        client = boto3.client(
            'athena',
            region_name=self.settings.aws_region,
        )

        # Start the controlled query and capture Athena's query execution ID.
        response = client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={
                'Database': self.settings.athena_database,
            },
            WorkGroup=self.settings.athena_workgroup,
            ResultConfiguration={
                'OutputLocation': self.settings.athena_output_location,
            },
        )
        query_id = response['QueryExecutionId']

        # Athena is asynchronous, so poll until it reaches a terminal state.
        while True:
            execution = client.get_query_execution(QueryExecutionId=query_id)
            state = execution['QueryExecution']['Status']['State']

            if state == 'SUCCEEDED':
                break
            if state in {'FAILED', 'CANCELLED'}:
                raise RuntimeError(f'Athena query ended with state={state}')

            time.sleep(1)

        result = client.get_query_results(QueryExecutionId=query_id)['ResultSet']
        rows = result.get('Rows', [])

        if not rows:
            return []

        # Athena returns the first row as column headers.
        headers = [
            cell.get('VarCharValue', '')
            for cell in rows[0]['Data']
        ]

        return [
            dict(
                zip(
                    headers,
                    [cell.get('VarCharValue') for cell in row['Data']],
                )
            )
            for row in rows[1:]
        ]


class SQLGatewayBackend:
    """Execute controlled SQL through an internal HTTP SQL Gateway."""

    name = 'sql_gateway'

    def __init__(self, settings: Settings):
        """Validate gateway configuration and store connection settings."""
        if not settings.sql_gateway_endpoint:
            raise ValueError('SQL_GATEWAY_ENDPOINT is required.')

        self.settings = settings

    def execute(self, sql: str) -> list[dict[str, Any]]:
        """POST controlled SQL to the gateway and normalize returned rows."""
        payload = {
            'sql': sql,
            'region': self.settings.data_region,
            'cluster': self.settings.data_cluster,
        }

        request = urllib.request.Request(
            self.settings.sql_gateway_endpoint,
            data=json.dumps(payload).encode(),
            headers={
                'Content-Type': 'application/json',
                'X-User-Id': self.settings.sql_gateway_user_id or '',
                'Authorization': (
                    f'Bearer {self.settings.sql_gateway_token or ""}'
                ),
            },
            method='POST',
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode('utf-8'))

        # Support either a direct list response or {'rows': [...]}.
        return body if isinstance(body, list) else body.get('rows', [])

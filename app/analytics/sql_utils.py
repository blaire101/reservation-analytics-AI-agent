from __future__ import annotations


def sql_string(value: str) -> str:
    """Quote a string literal for the controlled SQL used by this demo."""

    return "'" + value.replace("'", "''") + "'"

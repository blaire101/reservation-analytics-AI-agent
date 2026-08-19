"""Small SQL-literal helpers used by this simple demo."""


def sql_string(value: str) -> str:
    """Escape a Python string as a single-quoted SQL literal.

    Args:
        value: Raw string value used by a controlled SQL builder.

    Returns:
        Single-quoted SQL literal with embedded single quotes escaped.

    Note:
        This helper keeps the demo portable across simple backends. A real
        production implementation should prefer parameterized queries or the
        target platform's safe query-parameter API.
    """
    return "'" + str(value).replace("'", "''") + "'"

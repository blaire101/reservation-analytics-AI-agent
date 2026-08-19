"""Load application configuration from small env files and OS environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


# Project root: one directory above ``app/``.
ROOT = Path(__file__).resolve().parents[1]


def _read_env(path: Path) -> dict[str, str]:
    """Read a simple ``KEY=VALUE`` file into a dictionary.

    Args:
        path: Environment file path.

    Returns:
        Dictionary of parsed values. Missing files return an empty dictionary.
    """
    if not path.exists():
        return {}

    values: dict[str, str] = {}

    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()

        # Ignore comments, blank lines, and malformed lines.
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()

    return values


def _get(values: dict[str, str], key: str, default: str = '') -> str:
    """Read one setting, giving OS environment variables highest priority."""
    return os.environ.get(key, values.get(key, default))


@dataclass(frozen=True)
class Settings:
    """Typed application configuration shared across the project."""

    # Runtime mode / data backend.
    app_env: str = 'local'
    backend: str = 'sqlite'

    # Local paths.
    knowledge_dir: Path = ROOT / 'knowledge'
    sqlite_path: Path = ROOT / 'local_data' / 'reservation_analytics.db'

    # LLM / embedding configuration.
    openai_api_key: str | None = None
    openai_model: str = 'gpt-4.1-mini'
    embedding_model: str = 'text-embedding-3-small'

    # Generic data platform identifiers.
    data_region: str = 'local'
    data_cluster: str = 'local'
    data_database: str = 'reservation_analytics'

    # Athena adapter settings.
    athena_workgroup: str = 'primary'
    athena_output_location: str = 's3://change-me/athena-results/'

    # Internal SQL Gateway adapter settings.
    sql_gateway_endpoint: str | None = None
    sql_gateway_user_id: str | None = None
    sql_gateway_token: str | None = None

    @property
    def aws_region(self) -> str:
        """Expose ``data_region`` under the name expected by Athena."""
        return self.data_region

    @property
    def athena_database(self) -> str:
        """Expose ``data_database`` under the name expected by Athena."""
        return self.data_database

    def require_llm(self) -> None:
        """Fail clearly when an LLM-dependent path has no API key configured."""
        if not self.openai_api_key:
            raise RuntimeError(
                'LLM service is unavailable: OPENAI_API_KEY is not configured.'
            )


def load_settings(env_file: str = 'config/local.env') -> Settings:
    """Load settings from config file, .env, and OS environment variables.

    Priority from lowest to highest:
        defaults -> config/<env>.env -> .env -> OS environment variables

    Args:
        env_file: Project-relative base configuration file.

    Returns:
        Immutable ``Settings`` object used by the application.
    """
    values = _read_env(ROOT / env_file)

    # Local .env values override the selected config file.
    values.update(_read_env(ROOT / '.env'))

    # _get() then lets real OS environment variables override both files.
    return Settings(
        app_env=_get(values, 'APP_ENV', 'local'),
        backend=_get(values, 'DATA_BACKEND', 'sqlite').lower(),
        knowledge_dir=ROOT / _get(values, 'KNOWLEDGE_DIR', 'knowledge'),
        sqlite_path=ROOT / _get(
            values,
            'SQLITE_PATH',
            'local_data/reservation_analytics.db',
        ),
        openai_api_key=_get(values, 'OPENAI_API_KEY') or None,
        openai_model=_get(values, 'OPENAI_MODEL', 'gpt-4.1-mini'),
        embedding_model=_get(
            values,
            'OPENAI_EMBEDDING_MODEL',
            'text-embedding-3-small',
        ),
        data_region=_get(values, 'DATA_REGION', 'local'),
        data_cluster=_get(values, 'DATA_CLUSTER', 'local'),
        data_database=_get(values, 'DATA_DATABASE', 'reservation_analytics'),
        athena_workgroup=_get(values, 'ATHENA_WORKGROUP', 'primary'),
        athena_output_location=_get(
            values,
            'ATHENA_OUTPUT_LOCATION',
            's3://change-me/athena-results/',
        ),
        sql_gateway_endpoint=_get(values, 'SQL_GATEWAY_ENDPOINT') or None,
        sql_gateway_user_id=_get(values, 'SQL_GATEWAY_USER_ID') or None,
        sql_gateway_token=_get(values, 'SQL_GATEWAY_TOKEN') or None,
    )

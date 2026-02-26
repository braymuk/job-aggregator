from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    database_url: str
    digest_email_to: str
    digest_email_from: str
    digest_smtp_host: str
    digest_smtp_port: int
    digest_smtp_username: str
    digest_smtp_password: str
    digest_use_tls: bool
    preference_keywords: tuple[str, ...]
    preference_location: str
    preference_remote_only: bool
    ingest_enable_real_sources: bool
    ingest_enable_skeleton_source: bool
    ingest_enable_placeholder_sources: bool
    ingest_request_timeout_seconds: int


def _split_csv(raw_value: str) -> tuple[str, ...]:
    return tuple(item.strip().lower() for item in raw_value.split(",") if item.strip())


def _load_local_config() -> dict[str, Any]:
    config_path = Path(os.getenv("LOCAL_CONFIG_PATH", "config.local.json"))
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _get_raw(name: str, file_config: dict[str, Any]) -> Any:
    env_value = os.getenv(name)
    if env_value is not None:
        return env_value
    return file_config.get(name)


def _get_str(name: str, file_config: dict[str, Any], default: str = "") -> str:
    value = _get_raw(name, file_config)
    if value is None:
        return default
    return str(value)


def _get_int(name: str, file_config: dict[str, Any], default: int) -> int:
    value = _get_raw(name, file_config)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_bool(name: str, file_config: dict[str, Any], default: bool = False) -> bool:
    value = _get_raw(name, file_config)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_keywords(file_config: dict[str, Any]) -> tuple[str, ...]:
    value = _get_raw("PREFERENCE_KEYWORDS", file_config)
    if value is None:
        return _split_csv("python,backend,api")
    if isinstance(value, list):
        return tuple(str(item).strip().lower() for item in value if str(item).strip())
    return _split_csv(str(value))


def get_settings() -> Settings:
    file_config = _load_local_config()
    return Settings(
        database_url=_get_str(
            "DATABASE_URL",
            file_config,
            "postgresql+psycopg://postgres:postgres@localhost:5432/job_aggregator",
        ),
        digest_email_to=_get_str("DIGEST_EMAIL_TO", file_config, "you@example.com"),
        digest_email_from=_get_str("DIGEST_EMAIL_FROM", file_config, "jobs@example.com"),
        digest_smtp_host=_get_str("DIGEST_SMTP_HOST", file_config, "localhost"),
        digest_smtp_port=_get_int("DIGEST_SMTP_PORT", file_config, 1025),
        digest_smtp_username=_get_str("DIGEST_SMTP_USERNAME", file_config),
        digest_smtp_password=_get_str("DIGEST_SMTP_PASSWORD", file_config),
        digest_use_tls=_get_bool("DIGEST_USE_TLS", file_config),
        preference_keywords=_get_keywords(file_config),
        preference_location=_get_str("PREFERENCE_LOCATION", file_config, "united states").strip().lower(),
        preference_remote_only=_get_bool("PREFERENCE_REMOTE_ONLY", file_config, default=True),
        ingest_enable_real_sources=_get_bool("INGEST_ENABLE_REAL_SOURCES", file_config, default=False),
        ingest_enable_skeleton_source=_get_bool(
            "INGEST_ENABLE_SKELETON_SOURCE", file_config, default=True
        ),
        ingest_enable_placeholder_sources=_get_bool(
            "INGEST_ENABLE_PLACEHOLDER_SOURCES", file_config, default=False
        ),
        ingest_request_timeout_seconds=_get_int("INGEST_REQUEST_TIMEOUT_SECONDS", file_config, 20),
    )

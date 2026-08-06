"""Validated process configuration for development and production."""

from dataclasses import dataclass
import os
from typing import Mapping, Optional
from urllib.parse import urlsplit


DEVELOPMENT = "development"
PRODUCTION = "production"
DEFAULT_ADMIN_TOKEN_TTL_SECONDS = 12 * 60 * 60
MIN_ADMIN_TOKEN_TTL_SECONDS = 60
MAX_ADMIN_TOKEN_TTL_SECONDS = 24 * 60 * 60


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing or unsafe."""


@dataclass(frozen=True)
class AppConfig:
    environment: str
    admin_password: str
    allowed_origins: tuple[str, ...]
    admin_token_ttl_seconds: int

    @property
    def is_development(self) -> bool:
        return self.environment == DEVELOPMENT


def _required_value(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required")
    return value


def _parse_origins(raw_origins: str, *, production: bool) -> tuple[str, ...]:
    origins: list[str] = []
    for raw_origin in raw_origins.split(","):
        origin = raw_origin.strip()
        if not origin:
            raise ConfigError("ALLOWED_ORIGINS contains an empty origin")
        if "*" in origin:
            raise ConfigError("ALLOWED_ORIGINS must not contain wildcards")

        parsed = urlsplit(origin)
        try:
            parsed_port = parsed.port
        except ValueError as error:
            raise ConfigError(f"Invalid origin in ALLOWED_ORIGINS: {origin}") from error
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ConfigError(f"Invalid origin in ALLOWED_ORIGINS: {origin}")
        if production and parsed.scheme != "https":
            raise ConfigError("Production ALLOWED_ORIGINS must use https")

        host = parsed.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        normalized = f"{parsed.scheme.lower()}://{host}"
        if parsed_port is not None:
            normalized += f":{parsed_port}"
        if normalized not in origins:
            origins.append(normalized)

    if not origins:
        raise ConfigError("ALLOWED_ORIGINS must contain at least one origin")
    return tuple(origins)


def load_app_config(environ: Optional[Mapping[str, str]] = None) -> AppConfig:
    source = os.environ if environ is None else environ
    environment = _required_value(source, "CHGKA_ENV").lower()
    if environment not in (DEVELOPMENT, PRODUCTION):
        raise ConfigError("CHGKA_ENV must be development or production")

    admin_password = _required_value(source, "ADMIN_PASSWORD")
    if environment == PRODUCTION:
        if admin_password == "admin123" or len(admin_password) < 12:
            raise ConfigError(
                "Production ADMIN_PASSWORD must contain at least 12 characters "
                "and must not use the development password"
            )

    allowed_origins = _parse_origins(
        _required_value(source, "ALLOWED_ORIGINS"),
        production=environment == PRODUCTION,
    )

    raw_ttl = source.get(
        "ADMIN_TOKEN_TTL_SECONDS",
        str(DEFAULT_ADMIN_TOKEN_TTL_SECONDS),
    ).strip()
    try:
        admin_token_ttl_seconds = int(raw_ttl)
    except ValueError as error:
        raise ConfigError("ADMIN_TOKEN_TTL_SECONDS must be an integer") from error
    if not MIN_ADMIN_TOKEN_TTL_SECONDS <= admin_token_ttl_seconds <= MAX_ADMIN_TOKEN_TTL_SECONDS:
        raise ConfigError(
            "ADMIN_TOKEN_TTL_SECONDS must be between "
            f"{MIN_ADMIN_TOKEN_TTL_SECONDS} and {MAX_ADMIN_TOKEN_TTL_SECONDS}"
        )

    return AppConfig(
        environment=environment,
        admin_password=admin_password,
        allowed_origins=allowed_origins,
        admin_token_ttl_seconds=admin_token_ttl_seconds,
    )

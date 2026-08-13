import pytest

from config import ConfigError, load_app_config


def _environment(**overrides):
    values = {
        "CHGKA_ENV": "development",
        "ADMIN_PASSWORD": "admin123",
        "ALLOWED_ORIGINS": "http://localhost:5173",
        "CHGKA_DB_PATH": ":memory:",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    "missing",
    ["CHGKA_ENV", "ADMIN_PASSWORD", "ALLOWED_ORIGINS", "CHGKA_DB_PATH"],
)
def test_required_security_environment_is_explicit(missing):
    environment = _environment()
    environment.pop(missing)

    with pytest.raises(ConfigError, match=missing):
        load_app_config(environment)


def test_environment_name_is_strict():
    with pytest.raises(ConfigError, match="development or production"):
        load_app_config(_environment(CHGKA_ENV="staging"))


@pytest.mark.parametrize("password", ["admin123", "too-short"])
def test_production_rejects_development_or_short_password(password):
    with pytest.raises(ConfigError, match="at least 12"):
        load_app_config(
            _environment(
                CHGKA_ENV="production",
                ADMIN_PASSWORD=password,
                ALLOWED_ORIGINS="https://game.example.com",
            )
        )


def test_origins_are_normalized_deduplicated_and_https_in_production():
    config = load_app_config(
        _environment(
            CHGKA_ENV="production",
            ADMIN_PASSWORD="a-long-production-password",
            ALLOWED_ORIGINS=" https://GAME.example.com/,https://game.example.com ",
            CHGKA_DB_PATH="/data/chgka.sqlite3",
        )
    )

    assert config.allowed_origins == ("https://game.example.com",)

    with pytest.raises(ConfigError, match="must use https"):
        load_app_config(
            _environment(
                CHGKA_ENV="production",
                ADMIN_PASSWORD="a-long-production-password",
                ALLOWED_ORIGINS="http://game.example.com",
            )
        )


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.com",
        "https://game.example.com/path",
        "https://game.example.com?query=1",
        "https://user:password@game.example.com",
    ],
)
def test_invalid_origins_are_rejected(origin):
    with pytest.raises(ConfigError, match="origin|wildcard"):
        load_app_config(_environment(ALLOWED_ORIGINS=origin))


@pytest.mark.parametrize("ttl", ["not-a-number", "59", "86401"])
def test_admin_token_ttl_is_bounded(ttl):
    with pytest.raises(ConfigError, match="ADMIN_TOKEN_TTL_SECONDS"):
        load_app_config(_environment(ADMIN_TOKEN_TTL_SECONDS=ttl))


def test_development_defaults_to_twelve_hour_admin_token():
    config = load_app_config(_environment())

    assert config.is_development is True
    assert config.admin_token_ttl_seconds == 43_200
    assert config.database_path == ":memory:"


@pytest.mark.parametrize("database_path", [":memory:", "relative.sqlite3"])
def test_production_requires_absolute_durable_database_path(database_path):
    with pytest.raises(ConfigError, match="CHGKA_DB_PATH"):
        load_app_config(
            _environment(
                CHGKA_ENV="production",
                ADMIN_PASSWORD="a-long-production-password",
                ALLOWED_ORIGINS="https://game.example.com",
                CHGKA_DB_PATH=database_path,
            )
        )

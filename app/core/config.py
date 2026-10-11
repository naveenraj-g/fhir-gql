"""
Central application configuration, loaded from three layered sources —
mirrors fhir-server's own app/core/config.py precedence and split:

  1. Real env var (highest precedence) — set in the shell or by an orchestrator.
  2. `.env` — true per-environment values only: where the downstream FHIR
     Server/terminology service/IAM live, and the Redis connection string.
     These vary by deployment and are never committed with real values.
  3. `configs/config.yaml` — checked-in, non-secret application *behavior*:
     CORS, the Redis on/off switch, rate limits, logging, and FastAPI app
     metadata. Same spirit as fhir-server's configs/config.yaml — not a
     secret, safe to commit, and the thing an operator actually hand-edits
     to change how the app behaves without touching code.
  4. Field defaults (lowest precedence) — defined on the models below.

Deliberately NOT brought over from fhir-server: a `routes:`-style config for
toggling individual GraphQL queries/mutations on or off. This gateway's
schema is fixed at import time (app/gql/schema.py composes every resource's
Query/Mutation unconditionally) — there is no per-field enable/disable
mechanism here, and none was asked for.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class AppConfig(BaseModel):
    """FastAPI app metadata + interactive-docs exposure — same fields as
    fhir-server's AppConfig."""

    title: str = "Middleware API — Patient"
    version: str = "0.1.0"

    # Gates only the interactive /docs (Swagger) and /redoc UIs. /openapi.json
    # itself stays reachable regardless of this setting.
    docs_enabled: bool = True


class CorsConfig(BaseModel):
    """No CORSMiddleware is registered at all while `enabled` is false.
    Never set `allow_credentials: true` together with `allow_origins: ["*"]`
    — browsers reject that combination outright, so it's rejected here too."""

    enabled: bool = True
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    allow_credentials: bool = True
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])

    @model_validator(mode="after")
    def _reject_wildcard_with_credentials(self) -> CorsConfig:
        if self.allow_credentials and "*" in self.allow_origins:
            raise ValueError(
                "cors.allow_credentials cannot be true while cors.allow_origins "
                "includes '*' — browsers reject that combination outright. "
                "List explicit origins instead."
            )
        return self


class RedisConfig(BaseModel):
    """Global Redis on/off switch. `enabled: false` makes the app skip
    attempting a Redis connection at startup entirely (app/main.py's
    lifespan) and go straight to RateLimitMiddleware's in-process fallback —
    same intent as fhir-server's RedisConfig, adapted to this app's
    connect-and-detect-failure pattern rather than a per-dependent `backend`
    field (there's only one Redis-backed dependent here: rate limiting, and
    it already falls back to a local store automatically whenever
    `app.state.redis` is None)."""

    enabled: bool = True


class RateLimitConfig(BaseModel):
    """Sliding-window limits enforced by RateLimitMiddleware
    (app/middleware/rate_limit.py). Reads get a higher allowance than writes
    because reads are expected to be far more frequent in a clinical UI."""

    read_limit: int = 100
    write_limit: int = 20
    window_seconds: int = 60


class LogConfig(BaseModel):
    """Consumed by app.core.logging.setup_logging() and trace_methods()."""

    # Root log level. DEBUG turns on the per-method flow tracing that
    # trace_methods()-wrapped services/clients emit; INFO keeps only the
    # access log and hand-placed business events.
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # "json" (one JSON object per line — what log aggregators want) or
    # "console" (flat, human-readable; local development only).
    format: Literal["json", "console"] = "json"

    # ⚠️ PHI WARNING — LOCAL DEVELOPMENT ONLY. trace_methods() dumps a
    # resolver/service/client call's Pydantic-model arguments in full at
    # DEBUG when this is on — patient names, addresses, identifiers, etc.
    # `redact` below is a backstop for obvious secrets, NOT a PHI safeguard.
    debug_payloads: bool = False

    # Field names masked by trace_methods() even when debug_payloads is on.
    # Matched case-insensitively, at any nesting depth.
    redact: list[str] = Field(
        default_factory=lambda: ["authorization", "token", "password", "secret"]
    )

    # Matched case-insensitively — `format: JSON` / `level: debug` are as
    # valid as the canonical spellings, so a reasonable hand-edit to
    # configs/config.yaml doesn't crash the app at import time.
    @field_validator("level", "format", mode="before")
    @classmethod
    def _normalise_case(cls, v):
        if isinstance(v, str):
            return v.upper() if v.upper() in _LOG_LEVELS else v.lower()
        return v


class Settings(BaseSettings):
    """
    Application-wide settings. Pydantic-settings resolves each field from
    the highest-precedence source that defines it — see
    settings_customise_sources() below for the exact order.
    """

    # Base URL of the downstream FHIR Server that owns persistence.
    FHIR_SERVER_URL: str = "http://localhost:8001/api/fhir/v1"

    # Terminology is mounted outside the FHIR namespace on the FHIR Server
    # (/api/v1/terminology, not /api/fhir/v1/...), so it needs its own base URL.
    TERMINOLOGY_SERVER_URL: str = "http://localhost:8001/api/v1/terminology"

    # BetterAuth / IAM — JWT validation endpoints.
    IAM_JWKS_URL: str = "http://localhost:5000/api/auth/jwks"
    IAM_ISSUER: str = "http://localhost:5000"

    # Controls logging verbosity and GraphiQL exposure (see app/gql/schema.py).
    # Accepted values: "development" | "staging" | "production"
    ENVIRONMENT: str = "development"

    # Redis connection URL used by RateLimitMiddleware. Only required when
    # redis.enabled (below) is true — the default.
    REDIS_URL: str = "redis://localhost:6379/0"

    app: AppConfig = Field(default_factory=AppConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    logging: LogConfig = Field(default_factory=LogConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Precedence, highest first: real env var > `.env` >
        `configs/config.yaml` > field defaults. `.env` stays reserved for
        values that vary per deployment (where the FHIR Server/terminology/
        IAM live, the Redis URL); everything else — CORS, the Redis on/off
        switch, rate limits, logging, app metadata — is checked-in
        application behavior that lives in configs/config.yaml instead.

        Any nested field can still be overridden by a real env var using
        `__` as the nesting delimiter without touching the committed YAML —
        e.g. `RATE_LIMIT__WRITE_LIMIT=7` or `CORS__ENABLED=false`.
        """
        yaml_settings = YamlConfigSettingsSource(
            settings_cls,
            yaml_file="configs/config.yaml",
            yaml_file_encoding="utf-8",
        )
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_settings,
            file_secret_settings,
        )


# Module-level singleton — import `settings` everywhere instead of instantiating
# Settings() multiple times to avoid re-reading the environment/YAML on each import.
settings = Settings()

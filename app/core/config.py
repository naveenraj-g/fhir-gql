"""
Central application configuration, loaded from three layered sources —
mirrors fhir-server's own app/core/config.py precedence and split:

  1. Real env var (highest precedence) — set in the shell or by an orchestrator.
  2. `.env` — true per-environment values only: where the downstream FHIR
     Server/terminology service/IAM live, and the Redis connection string.
     These vary by deployment and are never committed with real values.
  3. `configs/config.yaml` — checked-in, non-secret application *behavior*:
     which connector is active, CORS, the Redis on/off switch, rate limits,
     logging, and FastAPI app metadata. Same spirit as fhir-server's
     configs/config.yaml — not a secret, safe to commit, and the thing an
     operator actually hand-edits to change how the app behaves without
     touching code. `configs/connectors/<name>.yaml` sits alongside it at
     the same precedence tier — one file per entry in
     app.connectors.registry.CONNECTORS, holding that connector's own
     settings (base_url, auth_method, ...) instead of crowding every
     connector's settings into one flat file. Secrets a connector needs
     (client_id/secret, token_url, ...) are never committed YAML — they're
     real env vars using the `__` nesting delimiter below, same as
     IAM_JWKS_URL already is.
  4. Field defaults (lowest precedence) — defined on the models below.

`routes.enabled` (configs/config.yaml) mirrors fhir-server's list of the same
name: app/gql/schema.py composes the root Query/Mutation only from the
resources named there. Not listed = its queries/mutations are not in the schema.
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


class InternalConnectorConfig(BaseModel):
    """Checked-in behavior for the internal connector (our own fhir-server -
    see app.connectors.internal for why it's named "internal"). See
    configs/connectors/internal.yaml. base_url lives here so everything about
    this one connector stays in its own file; override per environment with
    CONNECTORS__INTERNAL__BASE_URL.

    auth_method is always "token_passthrough": the caller's own inbound JWT is
    forwarded and no token is acquired (fhir-server trusts the same IAM)."""

    base_url: str = "http://localhost:8001/api/fhir/v1"
    auth_method: Literal["token_passthrough"] = "token_passthrough"


class OAuthClientConfig(BaseModel):
    """The login settings every EXTERNAL connector shares; each connector's own
    config adds its URLs on top. app.connectors.token_manager.build_token_manager
    turns these into the right token manager.

    auth_method:
      client_secret   - client id + secret (needs client_id, client_secret)
      private_key_jwt - signed-JWT login (needs client_id, private_key_path; the
                        matching public JWKS is registered with the backend)

    client_id / client_secret / private_key_path are real secrets or secret
    paths: env vars only (CONNECTORS__<NAME>__CLIENT_ID etc.), never committed
    YAML. They default to "" so a connector that isn't active costs nothing; the
    token manager raises at construction if the ones the chosen method needs are
    empty, so a misconfigured active connector fails at startup, not on first use.
    """

    token_url: str
    auth_method: Literal["client_secret", "private_key_jwt"]
    scope: str = ""
    client_id: str = ""
    client_secret: str = ""
    private_key_path: str = ""


class MedplumConnectorConfig(OAuthClientConfig):
    """Medplum (genuinely FHIR-R4-compliant external backend). See
    configs/connectors/medplum.yaml. Logs in with a client secret."""

    base_url: str = "http://localhost:8103/fhir/R4"
    token_url: str = "http://localhost:8103/oauth2/token"
    auth_method: Literal["client_secret", "private_key_jwt"] = "client_secret"


class OpenEmrConnectorConfig(OAuthClientConfig):
    """OpenEMR standard FHIR R4 API (system scopes). See
    configs/connectors/openemr.yaml. System scopes need the signed-JWT login."""

    base_url: str = "http://localhost/apis/default/fhir"
    token_url: str = "http://localhost/oauth2/default/token"
    auth_method: Literal["client_secret", "private_key_jwt"] = "private_key_jwt"
    scope: str = "system/Organization.read system/Location.read"


class EpicConnectorConfig(OAuthClientConfig):
    """Epic on FHIR R4 (read-only). See configs/connectors/epic.yaml. Epic backend
    apps use the signed-JWT login; scopes come from the app registration so
    `scope` stays empty."""

    base_url: str = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
    token_url: str = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
    auth_method: Literal["client_secret", "private_key_jwt"] = "private_key_jwt"


class OracleHealthConnectorConfig(OAuthClientConfig):
    """Oracle Health / Cerner Millennium FHIR R4. See
    configs/connectors/oracle_health.yaml. Either login works; {tenant_id} is
    filled into both URLs."""

    tenant_id: str = "ec2458f2-1e24-41c8-b71b-0e701af7583d"
    base_url: str = "https://fhir-ehr-code.cerner.com/r4/{tenant_id}"
    token_url: str = (
        "https://authorization.cerner.com/tenants/{tenant_id}"
        "/protocols/oauth2/profiles/smart-v1/token"
    )
    auth_method: Literal["client_secret", "private_key_jwt"] = "client_secret"
    scope: str = (
        "system/Organization.read system/Organization.write system/Location.read"
    )


class ConnectorsConfig(BaseModel):
    """Selects which backend system this gateway's resource clients and
    services talk to — see app.connectors.base.Connector (the interface)
    and app.connectors.registry (the name -> implementation mapping this
    `active` value is looked up in).

    Every resource client (app/fhir_client/*.py) and service is written
    against the Connector Protocol, never against a specific backend —
    `active` is the only thing that decides which concrete system is live.
    "internal" (this application, see app.connectors.internal — named for
    being our own first-party backend, not "fhir_server", since every
    external connector is also a FHIR server in the generic sense) is the
    default. "medplum" (see app.connectors.medplum) is registered as a
    second option — a genuinely FHIR-R4-compliant backend, authenticating
    via a client secret or signed JWT rather than internal's token_passthrough.
    Adding a further connector (e.g. Epic) means writing a package
    satisfying the Protocol (app/connectors/<name>/, not a single file —
    see app.connectors.internal's module docstring), registering it in
    app.connectors.registry.CONNECTORS, adding its own
    configs/connectors/<name>.yaml for checked-in behavior (auth_method,
    etc. — secrets like client_id/secret are real env vars instead, e.g.
    CONNECTORS__EPIC__CLIENT_ID, never committed YAML), and extending the
    Literal below to match — then `active` can be flipped to it."""

    active: Literal["internal", "medplum", "openemr", "epic", "oracle_health"] = (
        "internal"
    )

    # Per-connector behavior sub-config — one field per entry in
    # app.connectors.registry.CONNECTORS, each populated from its own
    # configs/connectors/<name>.yaml.
    internal: InternalConnectorConfig = Field(
        default_factory=InternalConnectorConfig
    )
    medplum: MedplumConnectorConfig = Field(default_factory=MedplumConnectorConfig)
    openemr: OpenEmrConnectorConfig = Field(default_factory=OpenEmrConnectorConfig)
    epic: EpicConnectorConfig = Field(default_factory=EpicConnectorConfig)
    oracle_health: OracleHealthConnectorConfig = Field(
        default_factory=OracleHealthConnectorConfig
    )


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


class RoutesConfig(BaseModel):
    """Which resources' GraphQL queries/mutations are exposed — resource names
    are the keys of app.gql.schema.RESOURCES (e.g. "organization",
    "location"). Unknown names fail at startup."""

    enabled: list[str] = Field(default_factory=list)


class Settings(BaseSettings):
    """
    Application-wide settings. Pydantic-settings resolves each field from
    the highest-precedence source that defines it — see
    settings_customise_sources() below for the exact order.
    """

    # Base URL of the downstream FHIR Server that owns persistence lives in
    # connectors.internal.base_url (InternalConnectorConfig) instead of
    # here — see configs/connectors/internal.yaml.

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
    connectors: ConnectorsConfig = Field(default_factory=ConnectorsConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    logging: LogConfig = Field(default_factory=LogConfig)
    routes: RoutesConfig = Field(default_factory=RoutesConfig)

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
        # One file per connector (configs/connectors/<name>.yaml), same
        # precedence tier as configs/config.yaml — see module docstring and
        # ConnectorsConfig. pydantic-settings deep-merges nested dict keys
        # across sources, so this and yaml_settings both contributing to
        # the shared `connectors.*` key combine rather than clobber.
        connector_yaml_settings = YamlConfigSettingsSource(
            settings_cls,
            yaml_file="configs/connectors/internal.yaml",
            yaml_file_encoding="utf-8",
        )
        medplum_yaml_settings = YamlConfigSettingsSource(
            settings_cls,
            yaml_file="configs/connectors/medplum.yaml",
            yaml_file_encoding="utf-8",
        )
        openemr_yaml_settings = YamlConfigSettingsSource(
            settings_cls,
            yaml_file="configs/connectors/openemr.yaml",
            yaml_file_encoding="utf-8",
        )
        epic_yaml_settings = YamlConfigSettingsSource(
            settings_cls,
            yaml_file="configs/connectors/epic.yaml",
            yaml_file_encoding="utf-8",
        )
        oracle_health_yaml_settings = YamlConfigSettingsSource(
            settings_cls,
            yaml_file="configs/connectors/oracle_health.yaml",
            yaml_file_encoding="utf-8",
        )
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_settings,
            connector_yaml_settings,
            medplum_yaml_settings,
            openemr_yaml_settings,
            epic_yaml_settings,
            oracle_health_yaml_settings,
            file_secret_settings,
        )


# Module-level singleton — import `settings` everywhere instead of instantiating
# Settings() multiple times to avoid re-reading the environment/YAML on each import.
settings = Settings()

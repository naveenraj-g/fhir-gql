"""
Per-resource tunable configuration, loaded from config/resources.json.

These are structural/business tuning knobs owned by a specific resource's
service (e.g. a bounded loop depth), not deployment secrets or
environment-varying URLs — so unlike app.config.Settings, they live in a
versioned JSON file instead of environment variables/.env. Add a new
`<Resource>ResourceConfig` model and a field on `ResourceConfig` (plus a
matching section in config/resources.json) as more resources need one.
"""

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class LocationResourceConfig(BaseModel):
    # Bounded depth for the part_of ancestor-chain walk in
    # LocationService._check_no_cycle — guards against looping forever if
    # the fhir-server ever contains a pre-existing cycle from outside this
    # service's control.
    max_hierarchy_depth: int = 50


class ResourceConfig(BaseSettings):
    """
    Root per-resource config object. One field per resource that has its own
    tunables; each resource keeps its own `<Resource>ResourceConfig` model.
    """

    location: LocationResourceConfig = LocationResourceConfig()

    model_config = SettingsConfigDict(
        json_file="config/resources.json", json_file_encoding="utf-8"
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
        # JSON file only — deliberately no env/dotenv source, so these values
        # can't be silently overridden by a stray environment variable the
        # way app.config.Settings' fields can be.
        return (init_settings, JsonConfigSettingsSource(settings_cls))


# Module-level singleton — import `resource_config` everywhere instead of
# instantiating ResourceConfig() multiple times, same convention as
# app.config.settings.
resource_config = ResourceConfig()

"""
Dependency-injection sub-container for the Location domain.

Wires LocationClient and LocationService together and exposes them to the
root Container. Both are declared as Factory providers (not Singleton)
because the client and service are stateless — a new instance per injection
avoids any cross-request state leakage. The shared FhirClient singleton is
passed in from the CoreContainer via the `core` DependenciesContainer
placeholder. Identical shape to app/di/modules/organization.py — Location no
longer needs an `organization` sibling container now that
managing_organization/part_of validation lives entirely on fhir-server (see
app/services/location_service.py's docstring).
"""

from dependency_injector import containers, providers

from app.fhir_client.location import LocationClient
from app.services.location_service import LocationService


class LocationContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the Location resource domain.

    Receives the CoreContainer instance via the `core` placeholder so it can
    reference the shared FhirClient singleton without creating a second HTTP
    session. Wired into the root Container in app.di.container.
    """

    # Placeholder replaced by the root Container at wiring time with the actual
    # CoreContainer instance — allows LocationClient to depend on core.fhir_client.
    core = providers.DependenciesContainer()

    # LocationClient wraps FhirClient with Location-specific paths.
    # Factory ensures a fresh instance per injection (stateless, safe to recreate).
    location_client = providers.Factory(
        LocationClient,
        fhir=core.fhir_client,
    )

    # LocationService owns all business logic for Location CRUD.
    # Depends on location_client — also Factory so both are recreated together per request.
    location_service = providers.Factory(
        LocationService,
        client=location_client,
    )

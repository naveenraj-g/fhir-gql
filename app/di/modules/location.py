"""
Dependency-injection sub-container for the Location domain.

Wires LocationClient and LocationService together. Unlike PatientContainer/
OrganizationContainer (which only need `core`), LocationContainer also
receives an `organization` placeholder — LocationService needs
OrganizationClient directly to validate `managing_organization` references
(see app/services/location_service.py's docstring). Both providers are
Factory (stateless, safe to recreate per injection).
"""

from dependency_injector import containers, providers

from app.fhir_client.location import LocationClient
from app.services.location_service import LocationService


class LocationContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the Location resource domain.

    Receives both the CoreContainer instance (via `core`, for the shared
    FhirClient singleton) and the OrganizationContainer instance (via
    `organization`, for its organization_client provider) from the root
    Container at wiring time.
    """

    # Placeholder replaced by the root Container with the actual CoreContainer
    # instance — allows LocationClient to depend on core.fhir_client.
    core = providers.DependenciesContainer()

    # Placeholder replaced by the root Container with the actual
    # OrganizationContainer instance — allows LocationService to validate
    # managing_organization references without LocationContainer importing
    # OrganizationContainer directly.
    organization = providers.DependenciesContainer()

    # LocationClient wraps FhirClient with Location-specific paths.
    location_client = providers.Factory(
        LocationClient,
        fhir=core.fhir_client,
    )

    # LocationService owns all business logic for Location CRUD, including
    # part_of/managing_organization validation.
    location_service = providers.Factory(
        LocationService,
        client=location_client,
        organization_client=organization.organization_client,
    )

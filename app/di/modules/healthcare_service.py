"""
Dependency-injection sub-container for the HealthcareService domain.

Wires HealthcareServiceClient and HealthcareServiceService together. Like
LocationContainer, this container receives sibling sub-containers beyond
`core` — HealthcareServiceService needs both OrganizationClient (to validate
`provided_by`) and LocationClient (to validate `location[]`/
`coverage_area[]`), so it receives `organization` and `location`
placeholders in addition to `core`.
"""

from dependency_injector import containers, providers

from app.fhir_client.healthcare_service import HealthcareServiceClient
from app.services.healthcare_service_service import HealthcareServiceService


class HealthcareServiceContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the HealthcareService resource domain.

    Receives the CoreContainer instance (via `core`, for the shared
    FhirClient singleton), the OrganizationContainer instance (via
    `organization`), and the LocationContainer instance (via `location`)
    from the root Container at wiring time.
    """

    core = providers.DependenciesContainer()
    organization = providers.DependenciesContainer()
    location = providers.DependenciesContainer()

    # HealthcareServiceClient wraps FhirClient with HealthcareService-specific paths.
    healthcare_service_client = providers.Factory(
        HealthcareServiceClient,
        fhir=core.fhir_client,
    )

    # HealthcareServiceService owns all business logic for HealthcareService CRUD,
    # including provided_by/location/coverage_area validation.
    healthcare_service_service = providers.Factory(
        HealthcareServiceService,
        client=healthcare_service_client,
        organization_client=organization.organization_client,
        location_client=location.location_client,
    )

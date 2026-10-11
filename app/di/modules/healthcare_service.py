"""
Dependency-injection sub-container for the HealthcareService domain.

Wires HealthcareServiceClient and HealthcareServiceService together and
exposes them to the root Container. Both are declared as Factory providers
(not Singleton) because the client and service are stateless — a new
instance per injection avoids any cross-request state leakage. The shared
FhirClient singleton is passed in from the CoreContainer via the `core`
DependenciesContainer placeholder. Identical shape to
app/di/modules/organization.py — HealthcareService no longer needs
`organization`/`location` sibling containers now that provided_by/location/
coverage_area validation lives entirely on fhir-server (see
app/services/healthcare_service_service.py's docstring).
"""

from dependency_injector import containers, providers

from app.fhir_client.healthcare_service import HealthcareServiceClient
from app.services.healthcare_service_service import HealthcareServiceService


class HealthcareServiceContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the HealthcareService resource domain.

    Receives the CoreContainer instance via the `core` placeholder so it can
    reference the shared FhirClient singleton without creating a second HTTP
    session. Wired into the root Container in app.di.container.
    """

    # Placeholder replaced by the root Container at wiring time with the actual
    # CoreContainer instance — allows HealthcareServiceClient to depend on core.fhir_client.
    core = providers.DependenciesContainer()

    # HealthcareServiceClient wraps FhirClient with HealthcareService-specific paths.
    # Factory ensures a fresh instance per injection (stateless, safe to recreate).
    healthcare_service_client = providers.Factory(
        HealthcareServiceClient,
        fhir=core.fhir_client,
    )

    # HealthcareServiceService owns all business logic for HealthcareService CRUD.
    # Depends on healthcare_service_client — also Factory so both are recreated together per request.
    healthcare_service_service = providers.Factory(
        HealthcareServiceService,
        client=healthcare_service_client,
    )

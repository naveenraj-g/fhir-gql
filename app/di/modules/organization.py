"""
Dependency-injection sub-container for the Organization domain.

Wires OrganizationClient and OrganizationsService together and exposes them
to the root Container. Both are declared as Factory providers (not
Singleton) because the client and service are stateless — a new instance
per injection avoids any cross-request state leakage. The shared FhirClient
singleton is passed in from the CoreContainer via the `core`
DependenciesContainer placeholder. Identical shape to
app/di/modules/patient.py's PatientContainer.
"""

from dependency_injector import containers, providers

from app.fhir_client.organization import OrganizationClient
from app.services.organization_service import OrganizationsService


class OrganizationContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the Organization resource domain.

    Receives the CoreContainer instance via the `core` placeholder so it can
    reference the shared FhirClient singleton without creating a second HTTP
    session. Wired into the root Container in app.di.container.
    """

    # Placeholder replaced by the root Container at wiring time with the actual
    # CoreContainer instance — allows OrganizationClient to depend on core.fhir_client.
    core = providers.DependenciesContainer()

    # OrganizationClient wraps FhirClient with Organization-specific paths.
    # Factory ensures a fresh instance per injection (stateless, safe to recreate).
    organization_client = providers.Factory(
        OrganizationClient,
        fhir=core.fhir_client,
    )

    # OrganizationsService owns all business logic for Organization CRUD.
    # Depends on organization_client — also Factory so both are recreated together per request.
    organization_service = providers.Factory(
        OrganizationsService,
        client=organization_client,
    )

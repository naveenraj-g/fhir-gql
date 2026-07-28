"""
Dependency-injection sub-container for the Practitioner domain.

Wires PractitionerClient and PractitionerService together. Like
LocationContainer/HealthcareServiceContainer, this container receives an
`organization` placeholder in addition to `core` — PractitionerService
needs OrganizationClient to validate qualification.issuer references (see
app/services/practitioner_service.py's docstring).
"""

from dependency_injector import containers, providers

from app.fhir_client.practitioner import PractitionerClient
from app.services.practitioner_service import PractitionerService


class PractitionerContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the Practitioner resource domain.

    Receives the CoreContainer instance (via `core`, for the shared
    FhirClient singleton) and the OrganizationContainer instance (via
    `organization`) from the root Container at wiring time.
    """

    core = providers.DependenciesContainer()
    organization = providers.DependenciesContainer()

    # PractitionerClient wraps FhirClient with Practitioner-specific paths and sub-resource methods.
    practitioner_client = providers.Factory(
        PractitionerClient,
        fhir=core.fhir_client,
    )

    # PractitionerService owns all business logic for Practitioner CRUD and sub-resource operations.
    practitioner_service = providers.Factory(
        PractitionerService,
        client=practitioner_client,
        organization_client=organization.organization_client,
    )

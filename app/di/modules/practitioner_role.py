"""
Dependency-injection sub-container for the PractitionerRole domain.

Wires PractitionerRoleClient and PractitionerRoleService together. The
deepest cross-container fan-out yet: PractitionerRoleService needs
PractitionerClient, OrganizationClient, LocationClient, and
HealthcareServiceClient to validate its four cross-resource references
(practitioner, organization, location[], healthcare_service[]) — see
app/services/practitioner_role_service.py's docstring.
"""

from dependency_injector import containers, providers

from app.fhir_client.practitioner_role import PractitionerRoleClient
from app.services.practitioner_role_service import PractitionerRoleService


class PractitionerRoleContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the PractitionerRole resource domain.

    Receives CoreContainer (via `core`), PractitionerContainer (via
    `practitioner`), OrganizationContainer (via `organization`),
    LocationContainer (via `location`), and HealthcareServiceContainer (via
    `healthcare_service`) from the root Container at wiring time.
    """

    core = providers.DependenciesContainer()
    practitioner = providers.DependenciesContainer()
    organization = providers.DependenciesContainer()
    location = providers.DependenciesContainer()
    healthcare_service = providers.DependenciesContainer()

    # PractitionerRoleClient wraps FhirClient with PractitionerRole-specific paths.
    practitioner_role_client = providers.Factory(
        PractitionerRoleClient,
        fhir=core.fhir_client,
    )

    # PractitionerRoleService owns all business logic for PractitionerRole
    # CRUD, including practitioner/organization/location/healthcare_service
    # reference validation.
    practitioner_role_service = providers.Factory(
        PractitionerRoleService,
        client=practitioner_role_client,
        practitioner_client=practitioner.practitioner_client,
        organization_client=organization.organization_client,
        location_client=location.location_client,
        healthcare_service_client=healthcare_service.healthcare_service_client,
    )

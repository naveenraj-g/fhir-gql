"""
Dependency-injection sub-container for the PractitionerRole domain.

Wires PractitionerRoleClient and PractitionerRoleService together and
exposes them to the root Container. No longer depends on `practitioner`/
`organization`/`location`/`healthcare_service` sibling containers —
practitioner/organization/location[]/healthcare_service[] reference
validation now lives entirely on fhir-server (see
app/services/practitioner_role_service.py's docstring). Both providers are
Factory (stateless, safe to recreate per injection), same shape as
app/di/modules/organization.py.
"""

from dependency_injector import containers, providers

from app.fhir_client.practitioner_role import PractitionerRoleClient
from app.services.practitioner_role_service import PractitionerRoleService


class PractitionerRoleContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the PractitionerRole resource domain.

    Receives the CoreContainer instance via the `core` placeholder so it can
    reference the shared FhirClient singleton without creating a second HTTP
    session. Wired into the root Container in app.di.container.
    """

    # Placeholder replaced by the root Container at wiring time with the actual
    # CoreContainer instance — allows PractitionerRoleClient to depend on core.fhir_client.
    core = providers.DependenciesContainer()

    # PractitionerRoleClient wraps FhirClient with PractitionerRole-specific paths.
    # Factory ensures a fresh instance per injection (stateless, safe to recreate).
    practitioner_role_client = providers.Factory(
        PractitionerRoleClient,
        fhir=core.fhir_client,
    )

    # PractitionerRoleService owns all business logic for PractitionerRole CRUD.
    # Depends on practitioner_role_client — also Factory so both are recreated together per request.
    practitioner_role_service = providers.Factory(
        PractitionerRoleService,
        client=practitioner_role_client,
    )

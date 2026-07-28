"""
Business logic service for the PractitionerRole resource.

PractitionerRoleService sits between the router/resolvers and
PractitionerRoleClient. It owns:
  - `practitioner` (-> Practitioner, scalar), `organization` (-> Organization,
    scalar), `location[]` (-> Location, list), and `healthcare_service[]`
    (-> HealthcareService, list) validation on create — each must reference
    an existing resource in the caller's own tenant, via the shared
    app.services.tenant_scope.validate_reference helper. This is the fourth
    resource to need this pattern (after Organization, Location,
    HealthcareService, Practitioner) and the deepest cross-container
    dependency yet — four sibling clients. `endpoint[]` (-> Endpoint) is NOT
    validated, since this project doesn't implement Endpoint (same as every
    other resource's own unvalidated `endpoint` field).
  - None of these references are patchable — PractitionerRolePatchSchema
    only exposes active/period_start/period_end/availability_exceptions —
    so no re-validation path is needed on update(), matching Organization's/
    HealthcareService's create-only reference shape.
  - Empty-patch rejection (422 if the caller sends an empty PATCH body).
  - `list_for_booking()` — a straightforward proxy to the fhir-server's
    enriched booking endpoint; no joining happens in this service.

The service does NOT inject created_by/updated_by — FhirClient does that
automatically from actor.sub on every POST and PATCH. No tenant-ownership
enforcement on by-id routes — user_id/org_id are Optional here, matching
Organization's/HealthcareService's convention.
"""

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.fhir_client.healthcare_service import HealthcareServiceClient
from app.fhir_client.location import LocationClient
from app.fhir_client.organization import OrganizationClient
from app.fhir_client.practitioner import PractitionerClient
from app.fhir_client.practitioner_role import PractitionerRoleClient
from app.schemas.practitioner_role.input import (
    ListPractitionerRolesSchema,
    PractitionerRoleCreateSchema,
    PractitionerRolePatchSchema,
)
from app.services.tenant_scope import validate_reference


class PractitionerRoleService:
    """
    Application service for PractitionerRole CRUD use cases.

    Instantiated per-request by the DI container (PractitionerRoleContainer)
    via Factory provider, so it holds no shared state between requests.
    """

    def __init__(
        self,
        client: PractitionerRoleClient,
        practitioner_client: PractitionerClient,
        organization_client: OrganizationClient,
        location_client: LocationClient,
        healthcare_service_client: HealthcareServiceClient,
    ) -> None:
        """
        Args:
            client:                    The PractitionerRoleClient injected by the DI container.
            practitioner_client:       PractitionerClient, injected purely to validate `practitioner`.
            organization_client:       OrganizationClient, injected purely to validate `organization`.
            location_client:          LocationClient, injected purely to validate `location[]` entries.
            healthcare_service_client: HealthcareServiceClient, injected purely to validate
                                       `healthcare_service[]` entries.
        """
        self._client = client
        self._practitioner_client = practitioner_client
        self._org_client = organization_client
        self._location_client = location_client
        self._healthcare_service_client = healthcare_service_client

    async def create(self, dto: PractitionerRoleCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """
        Create a new PractitionerRole resource, validating `practitioner`,
        `organization`, `location[]`, and `healthcare_service[]` references
        when provided.

        Raises:
            HTTPException(422): If any reference is malformed.
            HTTPException(404): If any reference points at a non-existent or cross-tenant resource.
        """
        if dto.practitioner is not None:
            await validate_reference(
                dto.practitioner,
                resource_type="Practitioner",
                get_by_id=self._practitioner_client.get_by_id,
                actor=actor,
                field_name="practitioner",
            )
        if dto.organization is not None:
            await validate_reference(
                dto.organization,
                resource_type="Organization",
                get_by_id=self._org_client.get_by_id,
                actor=actor,
                field_name="organization",
            )
        if dto.location is not None:
            for entry in dto.location:
                await validate_reference(
                    entry.reference,
                    resource_type="Location",
                    get_by_id=self._location_client.get_by_id,
                    actor=actor,
                    field_name="location",
                )
        if dto.healthcare_service is not None:
            for entry in dto.healthcare_service:
                await validate_reference(
                    entry.reference,
                    resource_type="HealthcareService",
                    get_by_id=self._healthcare_service_client.get_by_id,
                    actor=actor,
                    field_name="healthcare_service",
                )

        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(self, resource_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """Fetch a single PractitionerRole by its numeric ID, with all child arrays."""
        return await self._client.get_by_id(resource_id, accept=accept)

    async def list(self, filters: ListPractitionerRolesSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Return a paginated, optionally filtered list of PractitionerRole resources."""
        return await self._client.list(
            accept=accept,
            active=filters.active,
            practitioner_id=filters.practitioner_id,
            user_id=filters.user_id,
            org_id=filters.org_id,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update(
        self, resource_id: int, dto: PractitionerRolePatchSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Partially update a PractitionerRole's scalar fields.

        Raises:
            HTTPException(422): If the patch body is empty.
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(resource_id, payload, actor, accept=accept)

    async def list_for_booking(
        self,
        active: bool = True,
        specialty_code: str | None = None,
        day_of_week: str | None = None,
        org_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        accept: str | None = None,
    ) -> dict:
        """
        List PractitionerRoles enriched with Practitioner details for booking UIs.

        Proxies directly to the fhir-server's /practitioner-roles/booking
        endpoint, which joins each role with its linked Practitioner and
        enriched Location/HealthcareService data in a single query — no
        joining happens in this service.
        """
        return await self._client.list_for_booking(
            accept=accept,
            active=active,
            specialty_code=specialty_code,
            day_of_week=day_of_week,
            org_id=org_id,
            limit=limit,
            offset=offset,
        )

    async def delete(self, resource_id: int, actor: AuthUser) -> None:
        """Permanently delete a PractitionerRole and all its child records."""
        await self._client.delete(resource_id)

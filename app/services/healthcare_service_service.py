"""
Business logic service for the HealthcareService resource.

HealthcareServiceService sits between the router/resolvers and
HealthcareServiceClient. It owns:
  - `provided_by` (-> Organization, scalar), `location[]` (-> Location,
    list), and `coverage_area[]` (-> Location, list) validation on create —
    each must reference an existing resource in the caller's own tenant,
    via the shared app.services.tenant_scope.validate_reference helper
    (also used by OrganizationsService and LocationService). None of these
    are patchable — HealthcareServicePatchSchema only exposes scalar/photo
    fields, matching Organization's create-only reference shape, not
    Location's patchable one — so no re-validation is needed on update().
  - Empty-patch rejection (422 if the caller sends an empty PATCH body).
  - Tenant-ownership enforcement on by-id operations: get_by_id/update/delete
    fetch the resource first and 404 if its org_id doesn't match the
    caller's, via the shared check_tenant_ownership helper.

The service does NOT inject created_by/updated_by — FhirClient does that
automatically from actor.sub on every POST and PATCH.
"""

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.fhir_client.healthcare_service import HealthcareServiceClient
from app.fhir_client.location import LocationClient
from app.fhir_client.organization import OrganizationClient
from app.schemas.healthcare_service.input import (
    HealthcareServiceCreateSchema,
    HealthcareServicePatchSchema,
    ListHealthcareServicesSchema,
)
from app.services.tenant_scope import check_tenant_ownership, validate_reference


class HealthcareServiceService:
    """
    Application service for HealthcareService CRUD use cases.

    Instantiated per-request by the DI container (HealthcareServiceContainer)
    via Factory provider, so it holds no shared state between requests.
    """

    def __init__(
        self,
        client: HealthcareServiceClient,
        organization_client: OrganizationClient,
        location_client: LocationClient,
    ) -> None:
        """
        Args:
            client:              The HealthcareServiceClient injected by the DI container.
            organization_client: OrganizationClient, injected purely to validate
                                  `provided_by` references — see class docstring.
            location_client:     LocationClient, injected purely to validate
                                  `location[]`/`coverage_area[]` references.
        """
        self._client = client
        self._org_client = organization_client
        self._location_client = location_client

    async def create(
        self,
        dto: HealthcareServiceCreateSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Create a new HealthcareService resource, validating `provided_by`,
        `location[]`, and `coverage_area[]` references when provided.

        Args:
            dto:    Validated creation payload from the request body.
            actor:  Authenticated user performing the creation.
            accept: Content-type preference forwarded to the fhir-server.

        Returns:
            The newly created HealthcareService resource dict (plain JSON or FHIR R4).

        Raises:
            HTTPException(422): If any reference is malformed.
            HTTPException(404): If any reference points at a non-existent or cross-tenant resource.
        """
        if dto.provided_by is not None:
            await validate_reference(
                dto.provided_by,
                resource_type="Organization",
                get_by_id=self._org_client.get_by_id,
                actor=actor,
                field_name="provided_by",
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
        if dto.coverage_area is not None:
            for entry in dto.coverage_area:
                await validate_reference(
                    entry.reference,
                    resource_type="Location",
                    get_by_id=self._location_client.get_by_id,
                    actor=actor,
                    field_name="coverage_area",
                )

        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(
        self, service_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Fetch a single HealthcareService by its numeric ID, scoped to the caller's org.

        Raises:
            HTTPException(404): If not found, or found but owned by a different org.
        """
        internal = await self._client.get_by_id(service_id)
        check_tenant_ownership(
            internal, actor, not_found_detail="HealthcareService not found."
        )
        if accept is None:
            return internal
        return await self._client.get_by_id(service_id, accept=accept)

    async def list(
        self,
        filters: ListHealthcareServicesSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Return a paginated, optionally filtered list of HealthcareService resources.

        No ownership check here — matches OrganizationsService.list()/LocationService.list().
        """
        return await self._client.list(
            accept=accept,
            name=filters.name,
            active=filters.active,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update(
        self,
        service_id: int,
        dto: HealthcareServicePatchSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Partially update a HealthcareService resource, scoped to the caller's org.

        No reference re-validation needed — HealthcareServicePatchSchema
        doesn't expose provided_by/location/coverage_area at all.

        Raises:
            HTTPException(404): If not found, or found but owned by a different org.
            HTTPException(422): If the request body contained no updateable fields.
        """
        internal = await self._client.get_by_id(service_id)
        check_tenant_ownership(
            internal, actor, not_found_detail="HealthcareService not found."
        )

        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(service_id, payload, actor, accept=accept)

    async def delete(self, service_id: int, actor: AuthUser) -> None:
        """
        Delete a HealthcareService resource, scoped to the caller's org.

        Raises:
            HTTPException(404): If not found, or found but owned by a different org.
        """
        internal = await self._client.get_by_id(service_id)
        check_tenant_ownership(
            internal, actor, not_found_detail="HealthcareService not found."
        )
        await self._client.delete(service_id)

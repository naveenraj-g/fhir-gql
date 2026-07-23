"""
Business logic service for the Location resource.

LocationService sits between the router/resolvers and LocationClient. It owns:
  - `part_of` (parent Location) validation — existence, tenant match, and
    cycle prevention. Unlike Organization's `partof` (create-only,
    immutable), Location's `part_of` is patchable, so re-parenting is a real
    operation that must be re-validated on every change, not just create.
  - `managing_organization` validation — existence + tenant match. This is
    the one place LocationService reaches into a different resource
    domain's client (OrganizationClient) — a small, direct dependency for a
    single reference check, not the app/workflows/ orchestration tier (see
    dev-docs/13-workflow-orchestration.md; that tier is reserved for genuine
    multi-resource workflows like Appointment booking).
  - Empty-patch rejection (422 if the caller sends an empty PATCH body).
  - Tenant-ownership enforcement on by-id operations: get_by_id/update/delete
    fetch the resource first and 404 if its org_id doesn't match the
    caller's, via the shared app.services.tenant_scope.check_tenant_ownership
    helper (also used by OrganizationsService).

The service does NOT inject created_by/updated_by — FhirClient does that
automatically from actor.sub on every POST and PATCH.
"""

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.core.resource_config import resource_config
from app.fhir_client.location import LocationClient
from app.fhir_client.organization import OrganizationClient
from app.schemas.location.input import (
    ListLocationsSchema,
    LocationCreateSchema,
    LocationPatchSchema,
)
from app.services.tenant_scope import check_tenant_ownership, validate_reference

# Bounded depth for the part_of ancestor-chain walk in _check_no_cycle — guards
# against looping forever if the fhir-server ever contains a pre-existing
# cycle from outside this service's control. Sourced from config/resources.json
# (see app.core.resource_config) rather than hardcoded here.
_MAX_HIERARCHY_DEPTH = resource_config.location.max_hierarchy_depth


class LocationService:
    """
    Application service for Location CRUD use cases.

    Instantiated per-request by the DI container (LocationContainer) via
    Factory provider, so it holds no shared state between requests.
    """

    def __init__(
        self, client: LocationClient, organization_client: OrganizationClient
    ) -> None:
        """
        Args:
            client:              The LocationClient injected by the DI container.
            organization_client: OrganizationClient, injected purely to validate
                                  `managing_organization` references — see class docstring.
        """
        self._client = client
        self._org_client = organization_client

    async def _validate_part_of(
        self, part_of: str, actor: AuthUser, *, location_id: int | None = None
    ) -> None:
        """
        Verify a `part_of` parent-Location reference.

        Always checks the reference is well-formed, the parent exists, and
        belongs to the caller's tenant (delegated to the shared
        `validate_reference` helper). When `location_id` is given (i.e. this
        is an update, not a create — a brand-new Location has no id yet and
        so cannot be part of a cycle), also walks the parent's ancestor
        chain to reject re-parenting that would introduce a circular
        hierarchy.

        Args:
            part_of:     Raw FHIR reference string, e.g. "Location/230001".
            actor:       Authenticated caller — the parent's org_id must match.
            location_id: The Location being created/updated, if this is an
                         update (None on create, since cycles are impossible then).

        Raises:
            HTTPException(422): If `part_of` is malformed, or would make the
                Location its own parent.
            HTTPException(404): If the parent doesn't exist, or belongs to a different tenant.
            HTTPException(409): If re-parenting would create a circular hierarchy.
        """
        parent = await validate_reference(
            part_of,
            resource_type="Location",
            get_by_id=self._client.get_by_id,
            actor=actor,
            field_name="part_of",
        )

        if location_id is not None:
            await self._check_no_cycle(location_id, parent["id"])

    async def _check_no_cycle(self, location_id: int, new_parent_id: int) -> None:
        """
        Walk `new_parent_id`'s ancestor chain to ensure re-parenting
        `location_id` under it would not create a cycle.

        Bounded to `_MAX_HIERARCHY_DEPTH` hops so a pre-existing cycle in
        fhir-server data (outside this request's control) can't hang the
        request forever — such data is a separate, pre-existing problem this
        check isn't responsible for catching.

        Args:
            location_id:    The Location being re-parented.
            new_parent_id:  The proposed new `part_of` target.

        Raises:
            HTTPException(422): If `new_parent_id == location_id` (self-reference).
            HTTPException(409): If `location_id` appears anywhere in the new
                parent's existing ancestor chain.
        """
        if new_parent_id == location_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A Location cannot be its own part_of parent.",
            )

        current_id = new_parent_id
        seen: set[int] = set()
        for _ in range(_MAX_HIERARCHY_DEPTH):
            if current_id in seen:
                return  # pre-existing cycle elsewhere in the data — not this request's fault
            seen.add(current_id)

            node = await self._client.get_by_id(current_id)
            raw_parent_id = node.get("part_of_id")
            if raw_parent_id is None:
                return  # chain terminates without ever reaching location_id — safe

            next_id = int(raw_parent_id)
            if next_id == location_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This would create a circular Location hierarchy.",
                )
            current_id = next_id

    async def _validate_managing_organization(self, ref: str, actor: AuthUser) -> None:
        """
        Verify a `managing_organization` reference before allowing it to be set.

        Args:
            ref:   Raw FHIR reference string, e.g. "Organization/190001".
            actor: Authenticated caller — the organization's org_id must match.

        Raises:
            HTTPException(422): If `ref` is not a well-formed "Organization/<id>" reference.
            HTTPException(404): If the organization doesn't exist, or belongs to a different tenant.
        """
        await validate_reference(
            ref,
            resource_type="Organization",
            get_by_id=self._org_client.get_by_id,
            actor=actor,
            field_name="managing_organization",
        )

    async def create(
        self, dto: LocationCreateSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Create a new Location resource, validating `part_of` and
        `managing_organization` references when provided.

        Args:
            dto:    Validated creation payload from the request body.
            actor:  Authenticated user performing the creation.
            accept: Content-type preference forwarded to the fhir-server.

        Returns:
            The newly created Location resource dict (plain JSON or FHIR R4).

        Raises:
            HTTPException(422): If `part_of`/`managing_organization` are malformed.
            HTTPException(404): If either references a non-existent or cross-tenant resource.
        """
        if dto.part_of is not None:
            await self._validate_part_of(dto.part_of, actor)
        if dto.managing_organization is not None:
            await self._validate_managing_organization(dto.managing_organization, actor)

        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(
        self, location_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Fetch a single Location by its numeric ID, scoped to the caller's org.

        Always fetches plain JSON first to check tenant ownership (FHIR R4
        responses omit org_id).

        Raises:
            HTTPException(404): If not found, or found but owned by a different org.
        """
        internal = await self._client.get_by_id(location_id)
        check_tenant_ownership(internal, actor, not_found_detail="Location not found.")
        if accept is None:
            return internal
        return await self._client.get_by_id(location_id, accept=accept)

    async def list(
        self, filters: ListLocationsSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Return a paginated, optionally filtered list of Location resources.

        No ownership check here — matches OrganizationsService.list().
        """
        return await self._client.list(
            accept=accept,
            org_id=filters.org_id,
            status=filters.status,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update(
        self,
        location_id: int,
        dto: LocationPatchSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Partially update a Location resource, scoped to the caller's org.

        Re-validates `part_of` (existence + tenant + cycle) and
        `managing_organization` (existence + tenant) whenever the caller
        includes them in the patch payload — re-parenting is a supported
        operation on Location, unlike Organization's immutable `partof`.

        Raises:
            HTTPException(404): If not found, or found but owned by a different org.
            HTTPException(409): If re-parenting would create a circular hierarchy.
            HTTPException(422): If the request body contained no updateable fields.
        """
        internal = await self._client.get_by_id(location_id)
        check_tenant_ownership(internal, actor, not_found_detail="Location not found.")

        if dto.part_of is not None:
            await self._validate_part_of(dto.part_of, actor, location_id=location_id)
        if dto.managing_organization is not None:
            await self._validate_managing_organization(dto.managing_organization, actor)

        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(location_id, payload, actor, accept=accept)

    async def delete(self, location_id: int, actor: AuthUser) -> None:
        """
        Delete a Location resource, scoped to the caller's org.

        Raises:
            HTTPException(404): If not found, or found but owned by a different org.
        """
        internal = await self._client.get_by_id(location_id)
        check_tenant_ownership(internal, actor, not_found_detail="Location not found.")
        await self._client.delete(location_id)

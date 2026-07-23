"""
Business logic service for the Organization resource.

OrganizationsService sits between the router/resolvers and OrganizationClient. It owns:
  - Duplicate-name rejection on create AND on rename via update (409
    Conflict) — organizations are deduplicated by a case-insensitive exact
    match on `name`.
  - `partof` (parent organization) validation on create — the reference must
    be well-formed, point at an organization that actually exists, and
    belong to the caller's own tenant.
  - Empty-patch rejection (422 if the caller sends an empty PATCH body).
  - Tenant-ownership enforcement on by-id operations: get_by_id/update/delete
    fetch the resource first and 404 if its org_id doesn't match the caller's.
    Patient's equivalent by-id operations do NOT do this today (see
    dev-docs/06-admin-and-multitenancy.md) — Organization closes that gap
    from day one per dev-docs/10-resource-rollout-plan.md's rollout checklist,
    rather than repeating it.

This is all same-resource validation — every check here only ever needs
OrganizationClient (i.e. Organization referencing Organization). Business
rules that instead span multiple resource *domains* (e.g. an appointment
workflow needing Patient + Practitioner + Schedule) do not belong here —
see dev-docs/13-workflow-orchestration.md for where those go.

The service does NOT inject created_by/updated_by — FhirClient does that
automatically from actor.sub on every POST and PATCH.
"""

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.fhir_client.organization import OrganizationClient
from app.schemas.organization.input import (
    ListOrgsSchema,
    MeOrgsSchema,
    PatchOrgSchema,
    RegisterOrgSchema,
)
from app.services.tenant_scope import check_tenant_ownership, validate_reference


class OrganizationsService:
    """
    Application service for Organization CRUD use cases.

    Instantiated per-request by the DI container (OrganizationContainer) via
    Factory provider, so it holds no shared state between requests.
    """

    def __init__(self, client: OrganizationClient) -> None:
        """
        Args:
            client: The OrganizationClient injected by the DI container.
                    Provides fhir-server access for all Organization operations.
        """
        self._client = client

    async def _validate_partof(self, partof: str, actor: AuthUser) -> None:
        """
        Verify a `partof` parent-organization reference before allowing it to
        be set on create.

        Only ever calls back into OrganizationClient — this is a
        same-resource check (Organization referencing Organization), not
        cross-resource orchestration. Delegates the parse/fetch/ownership
        check to the shared `validate_reference` helper (also used by
        LocationService and HealthcareServiceService).

        Cycle detection (A partOf B partOf A) is deliberately not implemented
        here: `partof` is create-only (PatchOrgSchema never exposes it — only
        the free-text `partof_display` is patchable), and a brand-new
        organization has no id yet at validation time, so it cannot reference
        itself or any organization that could in turn reference it. If
        `partof` ever becomes patchable (re-parenting), this method is where
        an ancestor-chain walk would need to be added.

        Args:
            partof: Raw FHIR reference string from the request, e.g. "Organization/190001".
            actor:  Authenticated caller — the referenced parent's org_id must match.

        Raises:
            HTTPException(422): If `partof` is not a well-formed "Organization/<id>" reference.
            HTTPException(404): If the parent doesn't exist, or belongs to a different tenant.
        """
        await validate_reference(
            partof,
            resource_type="Organization",
            get_by_id=self._client.get_by_id,
            actor=actor,
            field_name="partof",
        )

    async def register(
        self, dto: RegisterOrgSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Create a new Organization resource, enforcing name uniqueness and a
        valid `partof` parent reference.

        Performs a pre-check by listing up to 10 organizations matching the
        requested name, then does a case-insensitive exact match to detect
        true duplicates (e.g. "Acme" and "acme" are the same organization).
        The pre-check always uses plain JSON (no accept) since the result is
        inspected programmatically. If `partof` is provided, `_validate_partof`
        confirms the parent exists and belongs to the caller's tenant before
        the create proceeds.

        Args:
            dto:    Validated registration payload from the request body.
            actor:  Authenticated user performing the creation.
            accept: Content-type preference forwarded to the fhir-server for
                    the created resource returned to the caller.

        Returns:
            The newly created Organization resource dict (plain JSON or FHIR R4).

        Raises:
            HTTPException(409): If an organization with the same name already exists.
            HTTPException(422): If `partof` is malformed.
            HTTPException(404): If `partof` references a non-existent or cross-tenant organization.
        """
        result = await self._client.list(name=dto.name, limit=10)
        duplicate = next(
            (
                o
                for o in result.get("data", [])
                if o.get("name", "").lower() == dto.name.lower()
            ),
            None,
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Organization with name '{dto.name}' already exists (id: {duplicate['id']}).",
            )

        if dto.partof is not None:
            await self._validate_partof(dto.partof, actor)

        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(
        self, organization_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Fetch a single Organization by its numeric ID, scoped to the caller's org.

        Always fetches plain JSON first to check tenant ownership (FHIR R4
        responses omit org_id, so the check must happen against the plain
        JSON shape regardless of what the caller ultimately wants back).

        Args:
            organization_id: The integer primary key of the Organization.
            actor:           Authenticated user — org_id is checked against the resource.
            accept:          Content-type preference forwarded to the fhir-server.

        Returns:
            The Organization resource dict in the requested format.

        Raises:
            HTTPException(404): If not found, or found but owned by a different org.
        """
        internal = await self._client.get_by_id(organization_id)
        check_tenant_ownership(
            internal, actor, not_found_detail="Organization not found."
        )
        if accept is None:
            return internal
        return await self._client.get_by_id(organization_id, accept=accept)

    async def list(
        self, filters: ListOrgsSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Return a paginated, optionally filtered list of Organization resources.

        Args:
            filters: Validated query parameters (name, active, user_id, org_id, limit, offset).
            actor:   Authenticated user (accepted for interface consistency).
            accept:  Content-type preference — FHIR R4 wraps results in a Bundle.

        Returns:
            Paginated plain JSON dict or FHIR Bundle depending on `accept`.
        """
        return await self._client.list(
            accept=accept,
            name=filters.name,
            active=filters.active,
            user_id=filters.user_id,
            org_id=filters.org_id,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get_me(
        self, filters: MeOrgsSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Return Organizations that belong to the calling user's JWT identity.

        user_id/org_id are taken from the authenticated actor and cannot be
        overridden by the caller.

        Args:
            filters: Pagination and optional active-status filter from query params.
            actor:   Authenticated user; provides user_id and org_id for scoping.
            accept:  Content-type preference forwarded to the fhir-server.

        Returns:
            Paginated plain JSON dict or FHIR Bundle depending on `accept`.
        """
        return await self._client.list(
            accept=accept,
            user_id=actor.sub,
            org_id=actor.org_id,
            active=filters.active,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update(
        self,
        organization_id: int,
        dto: PatchOrgSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Partially update an Organization resource, scoped to the caller's org.

        Fetches and checks ownership before patching, then rejects an empty
        patch payload (422) — a no-op PATCH would still bump `updated_by`
        with no real change, polluting the audit trail. If `name` is being
        changed, re-runs the same duplicate-name check `register()` does —
        `partof` needs no equivalent re-check since it isn't patchable at
        all (see `_validate_partof`'s docstring).

        Args:
            organization_id: The integer primary key of the Organization to update.
            dto:             Validated partial payload; all fields Optional.
            actor:           Authenticated user for ownership check and `updated_by` audit.
            accept:          Content-type preference forwarded to the fhir-server.

        Returns:
            The updated Organization resource dict in the requested format.

        Raises:
            HTTPException(404): If not found, or found but owned by a different org.
            HTTPException(409): If renaming to a name another organization already has.
            HTTPException(422): If the request body contained no updateable fields.
        """
        internal = await self._client.get_by_id(organization_id)
        check_tenant_ownership(
            internal, actor, not_found_detail="Organization not found."
        )

        if dto.name is not None:
            result = await self._client.list(name=dto.name, limit=10)
            duplicate = next(
                (
                    o
                    for o in result.get("data", [])
                    if o.get("name", "").lower() == dto.name.lower()
                    and o.get("id") != organization_id
                ),
                None,
            )
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Organization with name '{dto.name}' already exists (id: {duplicate['id']}).",
                )

        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(organization_id, payload, actor, accept=accept)

    async def delete(self, organization_id: int, actor: AuthUser) -> None:
        """
        Delete an Organization resource, scoped to the caller's org.

        Fetches and checks ownership before deleting — irreversible once it proceeds.

        Args:
            organization_id: The integer primary key of the Organization to delete.
            actor:           Authenticated user for the ownership check.

        Raises:
            HTTPException(404): If not found, or found but owned by a different org.
        """
        internal = await self._client.get_by_id(organization_id)
        check_tenant_ownership(
            internal, actor, not_found_detail="Organization not found."
        )
        await self._client.delete(organization_id)

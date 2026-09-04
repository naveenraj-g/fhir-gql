"""
Business logic service for the Practitioner resource and all its sub-resources.

PractitionerService sits between the router and PractitionerClient. It owns:
  - Empty-patch rejection (422 if the caller sends an empty PATCH body) for
    both the top-level Practitioner and every sub-resource PATCH endpoint.
  - JWT-scoped /me resolution: get_me() extracts user_id from the
    authenticated actor.
  - `qualification.issuer` validation — the only cross-resource reference
    anywhere on Practitioner (a reference to the Organization that issued
    the credential). Validated via the shared
    app.services.tenant_scope.validate_reference helper (also used by
    OrganizationsService/LocationService/HealthcareServiceService) from four
    call sites: add_qualification, patch_qualification (when issuer is
    set), and create_full/update_full (for each qualification entry that
    sets issuer) — centralised in _validate_qualification_issuer so the
    check isn't repeated four times.

The service does NOT inject created_by or updated_by — FhirClient does that
automatically from actor.sub on every POST and PATCH.

The service does NOT inject user_id or org_id into create payloads — both
are Optional and, when provided, come from the caller (matches
Organization/HealthcareService's convention, not Location's/Patient's
required fields). No tenant-ownership (check_tenant_ownership) enforcement
on by-id routes — this port doesn't introduce that gap-closing for
Practitioner, matching Patient's still-open gap tracked in
dev-docs/06-admin-and-multitenancy.md; this task is scoped to porting
Practitioner as-is, not revisiting Patient's tenant scoping.
"""

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.fhir_client.organization import OrganizationClient
from app.fhir_client.practitioner import PractitionerClient
from app.schemas.practitioner.input import (
    ListPractitionersSchema,
    PractitionerAddressCreateSchema,
    PractitionerAddressPatchSchema,
    PractitionerCommunicationCreateSchema,
    PractitionerCommunicationPatchSchema,
    PractitionerCreateSchema,
    PractitionerFullCreateSchema,
    PractitionerFullPatchSchema,
    PractitionerIdentifierCreateSchema,
    PractitionerIdentifierPatchSchema,
    PractitionerNameCreateSchema,
    PractitionerNamePatchSchema,
    PractitionerPatchSchema,
    PractitionerPhotoCreateSchema,
    PractitionerPhotoPatchSchema,
    PractitionerQualificationCreateSchema,
    PractitionerQualificationPatchSchema,
    PractitionerTelecomCreateSchema,
    PractitionerTelecomPatchSchema,
)
from app.services.tenant_scope import validate_reference


class PractitionerService:
    """
    Application service for Practitioner CRUD and sub-resource operations.

    Instantiated per-request by the DI container (PractitionerContainer) via
    Factory provider, so it holds no shared state between requests.
    """

    def __init__(self, client: PractitionerClient, organization_client: OrganizationClient) -> None:
        """
        Args:
            client:              The PractitionerClient injected by the DI container.
            organization_client: OrganizationClient, injected purely to validate
                                  qualification.issuer references — see class docstring.
        """
        self._client = client
        self._org_client = organization_client

    async def _validate_qualification_issuer(self, issuer: str, actor: AuthUser) -> None:
        """
        Verify a qualification's `issuer` reference before allowing it to be set.

        Args:
            issuer: Raw FHIR reference string, e.g. "Organization/190001".
            actor:  Authenticated caller — the organization's org_id must match.

        Raises:
            HTTPException(422): If `issuer` is not a well-formed "Organization/<id>" reference.
            HTTPException(404): If the organization doesn't exist, or belongs to a different tenant.
        """
        await validate_reference(
            issuer,
            resource_type="Organization",
            get_by_id=lambda org_id: self._org_client.get_by_id(org_id, actor),
            actor=actor,
            field_name="issuer",
        )

    async def _validate_qualifications_issuers(self, qualifications, actor: AuthUser) -> None:
        """Validate the `issuer` reference on every qualification entry in a list that sets one."""
        for qualification in qualifications:
            if qualification.issuer is not None:
                await self._validate_qualification_issuer(qualification.issuer, actor)

    # ── Core CRUD ─────────────────────────────────────────────────────────────

    async def create(self, dto: PractitionerCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Create a new Practitioner resource. Returns the newly created dict."""
        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create(payload, actor, accept=accept)

    async def create_full(self, dto: PractitionerFullCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """
        Create a Practitioner and any combination of sub-resources atomically.

        Validates qualification.issuer references (if any qualifications with
        issuer set are included) before creating.
        """
        if dto.qualifications is not None:
            await self._validate_qualifications_issuers(dto.qualifications, actor)

        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create_full(payload, actor, accept=accept)

    async def update_full(
        self, resource_id: int, dto: PractitionerFullPatchSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Update a Practitioner's scalar fields and/or rewrite any combination
        of sub-resource arrays atomically. Array semantics match Patient's
        update_full: omit/null leaves a sub-resource untouched, `[]` deletes
        all records of that type, a non-empty list replaces all records.

        Raises:
            HTTPException(422): If the body is empty (all fields omitted/null).
        """
        if dto.qualifications is not None:
            await self._validate_qualifications_issuers(dto.qualifications, actor)

        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field or sub-resource array must be provided.",
            )
        return await self._client.patch_full(resource_id, payload, actor, accept=accept)

    async def get_by_id(self, resource_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """Fetch a single Practitioner by integer primary key, with all sub-resource arrays."""
        return await self._client.get_by_id(resource_id, actor, accept=accept)

    async def list(self, filters: ListPractitionersSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """List Practitioners with optional filters and pagination."""
        return await self._client.list(
            actor,
            accept=accept,
            family_name=filters.family_name,
            given_name=filters.given_name,
            active=filters.active,
            user_id=filters.user_id,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update(self, resource_id: int, dto: PractitionerPatchSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """
        Partially update a Practitioner's scalar fields.

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

    async def delete(self, resource_id: int, actor: AuthUser) -> None:
        """Permanently delete a Practitioner and all its child records."""
        await self._client.delete(resource_id, actor)

    async def get_me(self, actor: AuthUser, accept: str | None = None) -> dict:
        """
        Fetch the Practitioner record belonging to the authenticated caller.

        Queries with user_id=actor.sub (always plain JSON for the pre-check),
        then re-fetches by ID honouring `accept` for the final response.

        Raises:
            HTTPException(404): If no Practitioner record is linked to this user.
        """
        result = await self._client.list(actor, user_id=actor.sub, limit=1, offset=0)
        data = result.get("data", [])
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Practitioner record found for this user.",
            )
        return await self._client.get_by_id(data[0]["id"], actor, accept=accept)

    # ── Helper: empty-patch guard ──────────────────────────────────────────────

    def _require_patch_payload(self, payload: dict, sub_resource: str) -> None:
        """Raise 422 if a sub-resource PATCH payload is empty."""
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"At least one field must be provided to update {sub_resource}.",
            )

    # ── Names ─────────────────────────────────────────────────────────────────

    async def add_name(self, practitioner_id: int, dto: PractitionerNameCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Add a HumanName to a Practitioner. Returns the full updated Practitioner."""
        return await self._client.add_name(practitioner_id, dto.model_dump(exclude_none=True, mode="json"), actor, accept=accept)

    async def list_names(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """List all HumanName entries for a Practitioner. Returns {data, total}."""
        return await self._client.list_names(practitioner_id, actor, accept=accept)

    async def patch_name(self, practitioner_id: int, name_id: int, dto: PractitionerNamePatchSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Partially update a Practitioner HumanName. Returns the full updated Practitioner."""
        payload = dto.model_dump(exclude_none=True, mode="json")
        self._require_patch_payload(payload, "name")
        return await self._client.patch_name(practitioner_id, name_id, payload, actor, accept=accept)

    async def delete_name(self, practitioner_id: int, name_id: int, actor: AuthUser) -> None:
        """Remove a specific HumanName from a Practitioner."""
        await self._client.delete_name(practitioner_id, name_id, actor)

    # ── Identifiers ───────────────────────────────────────────────────────────

    async def add_identifier(self, practitioner_id: int, dto: PractitionerIdentifierCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Add an Identifier to a Practitioner. Returns the full updated Practitioner."""
        return await self._client.add_identifier(practitioner_id, dto.model_dump(exclude_none=True, mode="json"), actor, accept=accept)

    async def list_identifiers(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """List all Identifiers for a Practitioner. Returns {data, total}."""
        return await self._client.list_identifiers(practitioner_id, actor, accept=accept)

    async def patch_identifier(self, practitioner_id: int, identifier_id: int, dto: PractitionerIdentifierPatchSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Partially update a Practitioner Identifier. Returns the full updated Practitioner."""
        payload = dto.model_dump(exclude_none=True, mode="json")
        self._require_patch_payload(payload, "identifier")
        return await self._client.patch_identifier(practitioner_id, identifier_id, payload, actor, accept=accept)

    async def delete_identifier(self, practitioner_id: int, identifier_id: int, actor: AuthUser) -> None:
        """Remove a specific Identifier from a Practitioner."""
        await self._client.delete_identifier(practitioner_id, identifier_id, actor)

    # ── Telecom ───────────────────────────────────────────────────────────────

    async def add_telecom(self, practitioner_id: int, dto: PractitionerTelecomCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Add a ContactPoint (telecom) to a Practitioner. Returns the full updated Practitioner."""
        return await self._client.add_telecom(practitioner_id, dto.model_dump(exclude_none=True, mode="json"), actor, accept=accept)

    async def list_telecom(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """List all telecom entries for a Practitioner. Returns {data, total}."""
        return await self._client.list_telecom(practitioner_id, actor, accept=accept)

    async def patch_telecom(self, practitioner_id: int, telecom_id: int, dto: PractitionerTelecomPatchSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Partially update a Practitioner ContactPoint. Returns the full updated Practitioner."""
        payload = dto.model_dump(exclude_none=True, mode="json")
        self._require_patch_payload(payload, "telecom")
        return await self._client.patch_telecom(practitioner_id, telecom_id, payload, actor, accept=accept)

    async def delete_telecom(self, practitioner_id: int, telecom_id: int, actor: AuthUser) -> None:
        """Remove a specific telecom entry from a Practitioner."""
        await self._client.delete_telecom(practitioner_id, telecom_id, actor)

    # ── Addresses ─────────────────────────────────────────────────────────────

    async def add_address(self, practitioner_id: int, dto: PractitionerAddressCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Add an Address to a Practitioner. Returns the full updated Practitioner."""
        return await self._client.add_address(practitioner_id, dto.model_dump(exclude_none=True, mode="json"), actor, accept=accept)

    async def list_addresses(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """List all Addresses for a Practitioner. Returns {data, total}."""
        return await self._client.list_addresses(practitioner_id, actor, accept=accept)

    async def patch_address(self, practitioner_id: int, address_id: int, dto: PractitionerAddressPatchSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Partially update a Practitioner Address. Returns the full updated Practitioner."""
        payload = dto.model_dump(exclude_none=True, mode="json")
        self._require_patch_payload(payload, "address")
        return await self._client.patch_address(practitioner_id, address_id, payload, actor, accept=accept)

    async def delete_address(self, practitioner_id: int, address_id: int, actor: AuthUser) -> None:
        """Remove a specific Address from a Practitioner."""
        await self._client.delete_address(practitioner_id, address_id, actor)

    # ── Photos ────────────────────────────────────────────────────────────────

    async def add_photo(self, practitioner_id: int, dto: PractitionerPhotoCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Add an Attachment (photo) to a Practitioner. Returns the full updated Practitioner."""
        return await self._client.add_photo(practitioner_id, dto.model_dump(exclude_none=True, mode="json"), actor, accept=accept)

    async def list_photos(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """List all photos for a Practitioner. Returns {data, total}."""
        return await self._client.list_photos(practitioner_id, actor, accept=accept)

    async def patch_photo(self, practitioner_id: int, photo_id: int, dto: PractitionerPhotoPatchSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Partially update a Practitioner photo Attachment. Returns the full updated Practitioner."""
        payload = dto.model_dump(exclude_none=True, mode="json")
        self._require_patch_payload(payload, "photo")
        return await self._client.patch_photo(practitioner_id, photo_id, payload, actor, accept=accept)

    async def delete_photo(self, practitioner_id: int, photo_id: int, actor: AuthUser) -> None:
        """Remove a specific photo from a Practitioner."""
        await self._client.delete_photo(practitioner_id, photo_id, actor)

    # ── Qualifications ────────────────────────────────────────────────────────

    async def add_qualification(self, practitioner_id: int, dto: PractitionerQualificationCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Add a qualification to a Practitioner, validating `issuer` if set. Returns the full updated Practitioner."""
        if dto.issuer is not None:
            await self._validate_qualification_issuer(dto.issuer, actor)
        return await self._client.add_qualification(practitioner_id, dto.model_dump(exclude_none=True, mode="json"), actor, accept=accept)

    async def list_qualifications(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """List all qualifications for a Practitioner. Returns {data, total}."""
        return await self._client.list_qualifications(practitioner_id, actor, accept=accept)

    async def patch_qualification(self, practitioner_id: int, qualification_id: int, dto: PractitionerQualificationPatchSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Partially update a Practitioner qualification, re-validating `issuer` if set. Returns the full updated Practitioner."""
        if dto.issuer is not None:
            await self._validate_qualification_issuer(dto.issuer, actor)
        payload = dto.model_dump(exclude_none=True, mode="json")
        self._require_patch_payload(payload, "qualification")
        return await self._client.patch_qualification(practitioner_id, qualification_id, payload, actor, accept=accept)

    async def delete_qualification(self, practitioner_id: int, qualification_id: int, actor: AuthUser) -> None:
        """Remove a specific qualification from a Practitioner."""
        await self._client.delete_qualification(practitioner_id, qualification_id, actor)

    # ── Communications ────────────────────────────────────────────────────────

    async def add_communication(self, practitioner_id: int, dto: PractitionerCommunicationCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Add a language/communication preference to a Practitioner. Returns the full updated Practitioner."""
        return await self._client.add_communication(practitioner_id, dto.model_dump(exclude_none=True, mode="json"), actor, accept=accept)

    async def list_communications(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """List all communication preferences for a Practitioner. Returns {data, total}."""
        return await self._client.list_communications(practitioner_id, actor, accept=accept)

    async def patch_communication(self, practitioner_id: int, communication_id: int, dto: PractitionerCommunicationPatchSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Partially update a Practitioner communication entry. Returns the full updated Practitioner."""
        payload = dto.model_dump(exclude_none=True, mode="json")
        self._require_patch_payload(payload, "communication")
        return await self._client.patch_communication(practitioner_id, communication_id, payload, actor, accept=accept)

    async def delete_communication(self, practitioner_id: int, communication_id: int, actor: AuthUser) -> None:
        """Remove a specific communication entry from a Practitioner."""
        await self._client.delete_communication(practitioner_id, communication_id, actor)

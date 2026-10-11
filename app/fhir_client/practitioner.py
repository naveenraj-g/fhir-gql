"""
FHIR client for Practitioner resources.

Thin wrapper around the shared FhirClient that knows the fhir-server paths
for the Practitioner resource and all its sub-resources. No business logic
lives here — all validation and rules belong in PractitionerService. Same
shape as app/fhir_client/patient.py.

A Practitioner is a person directly or indirectly involved in the
provisioning of healthcare. Sub-resources (names, identifiers, telecom,
addresses, photos, qualifications, communications) are managed via
dedicated sub-routes on the fhir-server.

Every method takes `actor: AuthUser` and forwards it to FhirClient so the
Authorization header reaches the fhir-server — Practitioner now validates
JWTs independently (JWT/RBAC rollout), rather than trusting the gateway
unconditionally.

All create/patch calls pass inject_audit=False: fhir-server derives
created_by/updated_by from the verified JWT's `sub` claim itself for
Practitioner, and its schemas (extra="forbid") no longer declare those
fields at all — if FhirClient injected them into the body here, fhir-server
would reject the request with 422.

Reference: https://hl7.org/fhir/R4/practitioner.html
"""

from app.auth.models import AuthUser
from app.fhir_client.client import FhirClient
from app.core.logging import trace_methods

_PATH = "/practitioners"


@trace_methods
class PractitionerClient:
    """
    Domain-specific HTTP client for Practitioner resources.

    Delegates every request to the shared FhirClient singleton, which
    handles authentication headers, base-URL resolution, and error
    propagation.
    """

    def __init__(self, fhir: FhirClient) -> None:
        """
        Args:
            fhir: The singleton FhirClient — owns the httpx session and base URL config.
        """
        self._fhir = fhir

    # ── Core CRUD ─────────────────────────────────────────────────────────────

    async def create(self, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /practitioners — create a new Practitioner resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept, inject_audit=False)

    async def create_full(self, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /practitioners/full — create a Practitioner and all sub-resources atomically."""
        return await self._fhir.post(f"{_PATH}/full", data, actor, accept=accept, inject_audit=False)

    async def patch_full(self, resource_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioners/{id}/full — update scalar fields and/or rewrite sub-resources."""
        return await self._fhir.patch(f"{_PATH}/{resource_id}/full", data, actor, accept=accept, inject_audit=False)

    async def get_by_id(self, resource_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /practitioners/{id} — fetch a single Practitioner by integer ID."""
        return await self._fhir.get(f"{_PATH}/{resource_id}", accept=accept, actor=actor)

    async def list(self, actor: AuthUser, accept: str | None = None, **params) -> dict:
        """GET /practitioners — list Practitioners with optional filters."""
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept, actor=actor)

    async def patch(self, resource_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioners/{id} — partially update a Practitioner."""
        return await self._fhir.patch(f"{_PATH}/{resource_id}", data, actor, accept=accept, inject_audit=False)

    async def delete(self, resource_id: int, actor: AuthUser) -> None:
        """DELETE /practitioners/{id} — permanently remove a Practitioner and all child records."""
        await self._fhir.delete(f"{_PATH}/{resource_id}", actor=actor)

    # ── Names ─────────────────────────────────────────────────────────────────

    async def add_name(self, practitioner_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /practitioners/{id}/names — add a HumanName to a Practitioner."""
        return await self._fhir.post(f"{_PATH}/{practitioner_id}/names", data, actor, accept=accept, inject_audit=False)

    async def list_names(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /practitioners/{id}/names — list all names for a Practitioner."""
        return await self._fhir.get(f"{_PATH}/{practitioner_id}/names", accept=accept, actor=actor)

    async def patch_name(self, practitioner_id: int, name_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioners/{id}/names/{name_id} — update a specific name."""
        return await self._fhir.patch(f"{_PATH}/{practitioner_id}/names/{name_id}", data, actor, accept=accept, inject_audit=False)

    async def delete_name(self, practitioner_id: int, name_id: int, actor: AuthUser) -> None:
        """DELETE /practitioners/{id}/names/{name_id} — remove a specific name."""
        await self._fhir.delete(f"{_PATH}/{practitioner_id}/names/{name_id}", actor=actor)

    # ── Identifiers ───────────────────────────────────────────────────────────

    async def add_identifier(self, practitioner_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /practitioners/{id}/identifiers — add an Identifier to a Practitioner."""
        return await self._fhir.post(f"{_PATH}/{practitioner_id}/identifiers", data, actor, accept=accept, inject_audit=False)

    async def list_identifiers(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /practitioners/{id}/identifiers — list all identifiers for a Practitioner."""
        return await self._fhir.get(f"{_PATH}/{practitioner_id}/identifiers", accept=accept, actor=actor)

    async def patch_identifier(self, practitioner_id: int, identifier_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioners/{id}/identifiers/{identifier_id} — update a specific identifier."""
        return await self._fhir.patch(f"{_PATH}/{practitioner_id}/identifiers/{identifier_id}", data, actor, accept=accept, inject_audit=False)

    async def delete_identifier(self, practitioner_id: int, identifier_id: int, actor: AuthUser) -> None:
        """DELETE /practitioners/{id}/identifiers/{identifier_id} — remove a specific identifier."""
        await self._fhir.delete(f"{_PATH}/{practitioner_id}/identifiers/{identifier_id}", actor=actor)

    # ── Telecom ───────────────────────────────────────────────────────────────

    async def add_telecom(self, practitioner_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /practitioners/{id}/telecom — add a ContactPoint to a Practitioner."""
        return await self._fhir.post(f"{_PATH}/{practitioner_id}/telecom", data, actor, accept=accept, inject_audit=False)

    async def list_telecom(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /practitioners/{id}/telecom — list all telecom entries for a Practitioner."""
        return await self._fhir.get(f"{_PATH}/{practitioner_id}/telecom", accept=accept, actor=actor)

    async def patch_telecom(self, practitioner_id: int, telecom_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioners/{id}/telecom/{telecom_id} — update a specific telecom entry."""
        return await self._fhir.patch(f"{_PATH}/{practitioner_id}/telecom/{telecom_id}", data, actor, accept=accept, inject_audit=False)

    async def delete_telecom(self, practitioner_id: int, telecom_id: int, actor: AuthUser) -> None:
        """DELETE /practitioners/{id}/telecom/{telecom_id} — remove a specific telecom entry."""
        await self._fhir.delete(f"{_PATH}/{practitioner_id}/telecom/{telecom_id}", actor=actor)

    # ── Addresses ─────────────────────────────────────────────────────────────

    async def add_address(self, practitioner_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /practitioners/{id}/addresses — add an Address to a Practitioner."""
        return await self._fhir.post(f"{_PATH}/{practitioner_id}/addresses", data, actor, accept=accept, inject_audit=False)

    async def list_addresses(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /practitioners/{id}/addresses — list all addresses for a Practitioner."""
        return await self._fhir.get(f"{_PATH}/{practitioner_id}/addresses", accept=accept, actor=actor)

    async def patch_address(self, practitioner_id: int, address_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioners/{id}/addresses/{address_id} — update a specific address."""
        return await self._fhir.patch(f"{_PATH}/{practitioner_id}/addresses/{address_id}", data, actor, accept=accept, inject_audit=False)

    async def delete_address(self, practitioner_id: int, address_id: int, actor: AuthUser) -> None:
        """DELETE /practitioners/{id}/addresses/{address_id} — remove a specific address."""
        await self._fhir.delete(f"{_PATH}/{practitioner_id}/addresses/{address_id}", actor=actor)

    # ── Photos ────────────────────────────────────────────────────────────────

    async def add_photo(self, practitioner_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /practitioners/{id}/photos — add an Attachment (photo) to a Practitioner."""
        return await self._fhir.post(f"{_PATH}/{practitioner_id}/photos", data, actor, accept=accept, inject_audit=False)

    async def list_photos(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /practitioners/{id}/photos — list all photos for a Practitioner."""
        return await self._fhir.get(f"{_PATH}/{practitioner_id}/photos", accept=accept, actor=actor)

    async def patch_photo(self, practitioner_id: int, photo_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioners/{id}/photos/{photo_id} — update a specific photo."""
        return await self._fhir.patch(f"{_PATH}/{practitioner_id}/photos/{photo_id}", data, actor, accept=accept, inject_audit=False)

    async def delete_photo(self, practitioner_id: int, photo_id: int, actor: AuthUser) -> None:
        """DELETE /practitioners/{id}/photos/{photo_id} — remove a specific photo."""
        await self._fhir.delete(f"{_PATH}/{practitioner_id}/photos/{photo_id}", actor=actor)

    # ── Qualifications ────────────────────────────────────────────────────────

    async def add_qualification(self, practitioner_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /practitioners/{id}/qualifications — add a qualification to a Practitioner."""
        return await self._fhir.post(f"{_PATH}/{practitioner_id}/qualifications", data, actor, accept=accept, inject_audit=False)

    async def list_qualifications(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /practitioners/{id}/qualifications — list all qualifications for a Practitioner."""
        return await self._fhir.get(f"{_PATH}/{practitioner_id}/qualifications", accept=accept, actor=actor)

    async def patch_qualification(self, practitioner_id: int, qualification_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioners/{id}/qualifications/{qualification_id} — update a specific qualification."""
        return await self._fhir.patch(f"{_PATH}/{practitioner_id}/qualifications/{qualification_id}", data, actor, accept=accept, inject_audit=False)

    async def delete_qualification(self, practitioner_id: int, qualification_id: int, actor: AuthUser) -> None:
        """DELETE /practitioners/{id}/qualifications/{qualification_id} — remove a specific qualification."""
        await self._fhir.delete(f"{_PATH}/{practitioner_id}/qualifications/{qualification_id}", actor=actor)

    # ── Communications ────────────────────────────────────────────────────────

    async def add_communication(self, practitioner_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /practitioners/{id}/communications — add a language/communication preference."""
        return await self._fhir.post(f"{_PATH}/{practitioner_id}/communications", data, actor, accept=accept, inject_audit=False)

    async def list_communications(self, practitioner_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /practitioners/{id}/communications — list all communication entries for a Practitioner."""
        return await self._fhir.get(f"{_PATH}/{practitioner_id}/communications", accept=accept, actor=actor)

    async def patch_communication(self, practitioner_id: int, communication_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioners/{id}/communications/{communication_id} — update a specific communication entry."""
        return await self._fhir.patch(f"{_PATH}/{practitioner_id}/communications/{communication_id}", data, actor, accept=accept, inject_audit=False)

    async def delete_communication(self, practitioner_id: int, communication_id: int, actor: AuthUser) -> None:
        """DELETE /practitioners/{id}/communications/{communication_id} — remove a specific communication entry."""
        await self._fhir.delete(f"{_PATH}/{practitioner_id}/communications/{communication_id}", actor=actor)

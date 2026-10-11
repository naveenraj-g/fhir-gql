"""
Business logic service for the Schedule resource.

ScheduleService sits between the router/resolvers and ScheduleClient. It
owns behavior qualitatively different from every prior port: instead of
only checking that a reference *exists*, it reads business data *off* the
referenced actors to compute Schedule's own fields.

  - Every actor is classified by its reference type prefix and, where this
    project has a client for that type (Practitioner, PractitionerRole,
    Location, HealthcareService, Patient), validated for existence + tenant
    match via the shared `validate_reference` helper. `RelatedPerson`/
    `Device` (FHIR-allowed, not implemented anywhere in this project) are
    accepted unvalidated, same treatment as `Endpoint` elsewhere. Any other
    type is rejected (422) — FHIR only allows these 7 actor types.
  - `service_category`/`service_type`/`specialty` are NOT accepted as
    input — they're derived by reading `PractitionerRole.specialty` and
    `HealthcareService.category`/`.type`/`.specialty` off whichever actors
    of those types are attached, unioned and de-duplicated by
    `(coding_system, coding_code)`.
  - A Schedule belongs to at most one provider: at most one
    Practitioner/PractitionerRole actor is allowed, and Patient actors are
    mutually exclusive with Practitioner/PractitionerRole/HealthcareService
    actors — see `_check_actor_cardinality`'s docstring for the reasoning
    (booking a Slot on a multi-provider Schedule couldn't say which
    provider became unavailable).
  - Empty-patch rejection (422) on update(); `actor` and the derived arrays
    are create-only (matches the sibling project's non-patchable shape for
    these fields), so no re-validation/re-derivation path is needed there.

This still lives directly in ScheduleService, not a separate app/workflows/
tier (see dev-docs/13-workflow-orchestration.md) — it's still one
resource's own create() flow reading a few sibling resources, the same
shape already used for Location/HealthcareService/Practitioner/
PractitionerRole, just reading business fields instead of only checking
existence.
"""

# typing.List/Tuple/Dict (not lowercase list[]/tuple[]/dict[]) are used
# deliberately in this file's own annotations: this class defines a method
# named `list`, and Python's lazy annotation evaluation resolves a bare
# `list[...]` generic used elsewhere in the class body to that method
# instead of the builtin, raising "'function' object is not subscriptable".
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.fhir_client.healthcare_service import HealthcareServiceClient
from app.fhir_client.location import LocationClient
from app.fhir_client.patient import PatientClient
from app.fhir_client.practitioner import PractitionerClient
from app.fhir_client.practitioner_role import PractitionerRoleClient
from app.fhir_client.schedule import ScheduleClient
from app.schemas.schedule.input import (
    ListSchedulesSchema,
    ScheduleActorInput,
    ScheduleCreateSchema,
    SchedulePatchSchema,
)
from app.services.tenant_scope import validate_reference
from app.core.logging import trace_methods

# Actor reference types this project has a client for, and can therefore
# existence-+-tenant-validate. FHIR also allows RelatedPerson/Device, which
# this project doesn't implement anywhere — those are accepted unvalidated
# (see _UNVALIDATED_ACTOR_TYPES), same treatment as Endpoint elsewhere.
_UNVALIDATED_ACTOR_TYPES = {"RelatedPerson", "Device"}

# Actor types that identify "who the provider is" for cardinality purposes.
_PROVIDER_ACTOR_TYPES = {"Practitioner", "PractitionerRole"}


@trace_methods
class ScheduleService:
    """
    Application service for Schedule CRUD use cases.

    Instantiated per-request by the DI container (ScheduleContainer) via
    Factory provider, so it holds no shared state between requests.
    """

    def __init__(
        self,
        client: ScheduleClient,
        practitioner_client: PractitionerClient,
        practitioner_role_client: PractitionerRoleClient,
        location_client: LocationClient,
        healthcare_service_client: HealthcareServiceClient,
        patient_client: PatientClient,
    ) -> None:
        """
        Args:
            client:                    The ScheduleClient injected by the DI container.
            practitioner_client:       Validates `Practitioner` actor references.
            practitioner_role_client:  Validates `PractitionerRole` actor references
                                       and supplies its `specialty` for derivation.
            location_client:          Validates `Location` actor references.
            healthcare_service_client: Validates `HealthcareService` actor references
                                       and supplies its `category`/`type`/`specialty`
                                       for derivation.
            patient_client:            Validates `Patient` actor references.
        """
        self._client = client
        self._actor_clients = {
            "Practitioner": practitioner_client,
            "PractitionerRole": practitioner_role_client,
            "Location": location_client,
            "HealthcareService": healthcare_service_client,
            "Patient": patient_client,
        }

    async def _classify_and_validate_actor(
        self, entry: ScheduleActorInput, actor: AuthUser
    ) -> Tuple[str, Optional[dict]]:
        """
        Parse `entry.reference`'s type prefix and validate it if this
        project has a client for that type.

        Args:
            entry: One actor entry from the create payload.
            actor: Authenticated caller — the referenced resource's org_id must match.

        Returns:
            `(resource_type, fetched_dict)` — `fetched_dict` is the plain-JSON
            resource dict for validated types, or `None` for
            `RelatedPerson`/`Device` (unvalidated).

        Raises:
            HTTPException(422): If the reference is malformed, or its type
                isn't one of FHIR's 7 allowed Schedule actor types.
            HTTPException(404): If a validated reference doesn't exist, or
                belongs to a different tenant.
        """
        resource_type = (
            entry.reference.split("/", 1)[0] if "/" in entry.reference else ""
        )

        if resource_type in self._actor_clients:
            fetched = await validate_reference(
                entry.reference,
                resource_type=resource_type,
                get_by_id=self._actor_clients[resource_type].get_by_id,
                actor=actor,
                field_name="actor",
            )
            return resource_type, fetched

        if resource_type in _UNVALIDATED_ACTOR_TYPES:
            return resource_type, None

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported actor reference type '{resource_type}' in '{entry.reference}'. "
                "Allowed: Practitioner, PractitionerRole, Location, HealthcareService, "
                "Patient, RelatedPerson, Device."
            ),
        )

    def _check_actor_cardinality(
        self, classified: List[Tuple[str, Optional[dict]]]
    ) -> None:
        """
        Enforce that a Schedule belongs to at most one provider.

        `Schedule.actor`'s FHIR 1..* cardinality exists to combine *one*
        provider-identifying actor with its supporting context (Location/
        HealthcareService describing where/what that one provider offers)
        — not to combine multiple *different* providers into a shared
        calendar. If two distinct Practitioners/PractitionerRoles were both
        actors on one Schedule, a booked Slot couldn't say which of them
        became unavailable. `Patient`-actor Schedules (e.g. a care-plan's
        own visit schedule) are a structurally separate FHIR use case and
        aren't mixed with provider-availability schedules.

        Args:
            classified: The `(resource_type, fetched_dict)` pairs from
                `_classify_and_validate_actor` for every actor entry.

        Raises:
            HTTPException(422): If more than one Practitioner/PractitionerRole
                actor is present, or a Patient actor is mixed with
                Practitioner/PractitionerRole/HealthcareService actors.
        """
        types = [resource_type for resource_type, _ in classified]

        provider_count = sum(1 for t in types if t in _PROVIDER_ACTOR_TYPES)
        if provider_count > 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A Schedule may have at most one Practitioner or PractitionerRole actor.",
            )

        has_patient = "Patient" in types
        has_provider_context = any(
            t in _PROVIDER_ACTOR_TYPES or t == "HealthcareService" for t in types
        )
        if has_patient and has_provider_context:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A Schedule cannot mix a Patient actor with Practitioner/PractitionerRole/HealthcareService actors.",
            )

    def _derive_service_fields(
        self, classified: List[Tuple[str, Optional[dict]]]
    ) -> dict:
        """
        Derive `service_category`/`service_type`/`specialty` from the
        attached PractitionerRole's `specialty` and HealthcareService's
        `category`/`type`/`specialty`, unioned and de-duplicated by
        `(coding_system, coding_code)` — not required to agree across
        actors, since these are already array fields.

        Args:
            classified: The `(resource_type, fetched_dict)` pairs from
                `_classify_and_validate_actor` for every actor entry.

        Returns:
            `{"service_category": [...], "service_type": [...], "specialty": [...]}`,
            each a list of `{coding_system, coding_code, coding_display, text}` dicts.
        """
        category_by_key: Dict[tuple, dict] = {}
        type_by_key: Dict[tuple, dict] = {}
        specialty_by_key: Dict[tuple, dict] = {}

        def _merge(target: Dict[tuple, dict], entries: Optional[List[dict]]) -> None:
            for entry in entries or []:
                key = (entry.get("coding_system"), entry.get("coding_code"))
                if key not in target:
                    target[key] = {
                        "coding_system": entry.get("coding_system"),
                        "coding_code": entry.get("coding_code"),
                        "coding_display": entry.get("coding_display"),
                        "text": entry.get("text"),
                    }

        for resource_type, data in classified:
            if data is None:
                continue
            if resource_type == "PractitionerRole":
                _merge(specialty_by_key, data.get("specialty"))
            elif resource_type == "HealthcareService":
                _merge(category_by_key, data.get("category"))
                _merge(type_by_key, data.get("type"))
                _merge(specialty_by_key, data.get("specialty"))

        return {
            "service_category": list(category_by_key.values()),
            "service_type": list(type_by_key.values()),
            "specialty": list(specialty_by_key.values()),
        }

    async def create(
        self, dto: ScheduleCreateSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Create a new Schedule, validating every actor reference, enforcing
        the one-provider-per-schedule rule, and deriving
        service_category/service_type/specialty from the PractitionerRole/
        HealthcareService actors.

        Raises:
            HTTPException(422): If an actor reference is malformed/unsupported,
                no actor is a PractitionerRole or HealthcareService, or the
                actor-cardinality rule is violated.
            HTTPException(404): If an actor reference points at a non-existent
                or cross-tenant resource.
        """
        classified = [
            await self._classify_and_validate_actor(entry, actor) for entry in dto.actor
        ]

        if not any(
            resource_type in ("PractitionerRole", "HealthcareService")
            for resource_type, _ in classified
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one actor must be a PractitionerRole or HealthcareService so serviceCategory/serviceType/specialty can be derived.",
            )

        self._check_actor_cardinality(classified)
        derived = self._derive_service_fields(classified)

        payload = dto.model_dump(exclude_none=True, mode="json")
        payload["service_category"] = derived["service_category"]
        payload["service_type"] = derived["service_type"]
        payload["specialty"] = derived["specialty"]

        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(
        self, schedule_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """Fetch a single Schedule by its numeric ID, with all sub-resource arrays."""
        return await self._client.get_by_id(schedule_id, accept=accept)

    async def list(
        self, filters: ListSchedulesSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """Return a paginated, optionally filtered list of Schedule resources."""
        return await self._client.list(
            accept=accept,
            active=filters.active,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update(
        self,
        schedule_id: int,
        dto: SchedulePatchSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Partially update a Schedule's scalar fields.

        Raises:
            HTTPException(422): If the patch body is empty.
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(schedule_id, payload, actor, accept=accept)

    async def delete(self, schedule_id: int, actor: AuthUser) -> None:
        """Permanently delete a Schedule resource."""
        await self._client.delete(schedule_id)

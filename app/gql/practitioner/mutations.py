import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.practitioner.types.input import (
    PractitionerAddressCreateInput,
    PractitionerAddressPatchInput,
    PractitionerCommunicationCreateInput,
    PractitionerCommunicationPatchInput,
    PractitionerCreateInput,
    PractitionerFullCreateInput,
    PractitionerFullPatchInput,
    PractitionerIdentifierCreateInput,
    PractitionerIdentifierPatchInput,
    PractitionerNameCreateInput,
    PractitionerNamePatchInput,
    PractitionerPatchInput,
    PractitionerPhotoCreateInput,
    PractitionerPhotoPatchInput,
    PractitionerQualificationCreateInput,
    PractitionerQualificationPatchInput,
    PractitionerTelecomCreateInput,
    PractitionerTelecomPatchInput,
)
from app.gql.practitioner.types.types import PractitionerType
from app.schemas.practitioner.response import PractitionerResponse

# Shared RBAC-permission wording reused across every sub-resource mutation's
# description= below, so the 21 near-identical mutations don't each repeat a
# slightly different phrasing of the same rule.
_UPDATE_PERM = "Requires the `practitioner:update` permission."


def _to_practitioner_type(data: dict) -> PractitionerType:
    """Shared conversion: raw fhir-server dict -> validated PractitionerResponse -> PractitionerType. Every resolver below returns through this."""
    return PractitionerType.from_pydantic(PractitionerResponse.model_validate(data))


@strawberry.type(description="Mutation fields for the Practitioner resource.")
class PractitionerMutation:
    """Mutation fields for the Practitioner resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    # ── Core CRUD ─────────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=(
            "Create a new Practitioner. `userId`/`orgId` are optional. `createdBy` is stamped "
            "automatically from the caller's JWT. Requires the `practitioner:create` permission."
        )
    )
    @translate_errors
    async def create_practitioner(self, info: strawberry.types.Info, input: PractitionerCreateInput) -> PractitionerType:
        """Create a new Practitioner — mirrors POST /practitioners/."""
        actor = require_gql_permission(info, "practitioner", "create")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.create(input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(
        description=(
            "Create a Practitioner and any combination of its sub-resources atomically in a "
            "single fhir-server transaction — if any sub-resource insert fails, the entire "
            "request rolls back and nothing is persisted. If a qualification's `issuer` is set, "
            "it must reference an existing organization in the caller's own tenant. Requires the "
            "`practitioner:create` permission."
        )
    )
    @translate_errors
    async def create_practitioner_full(self, info: strawberry.types.Info, input: PractitionerFullCreateInput) -> PractitionerType:
        """Create a Practitioner and any combination of its sub-resources atomically — mirrors POST /practitioners/full."""
        actor = require_gql_permission(info, "practitioner", "create")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.create_full(input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(
        description=(
            "Partially update a Practitioner's scalar fields (active, gender, birthDate, "
            "deceased*). Sub-resource arrays are managed via their own dedicated mutations. "
            f"`updatedBy` is stamped automatically from the caller's JWT. {_UPDATE_PERM}"
        )
    )
    @translate_errors
    async def update_practitioner(
        self, info: strawberry.types.Info, practitioner_id: int, input: PractitionerPatchInput
    ) -> PractitionerType:
        """Partially update a Practitioner — mirrors PATCH /practitioners/{id}."""
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.update(practitioner_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(
        description=(
            "Update a Practitioner's scalar fields and/or rewrite any combination of its seven "
            "sub-resource arrays atomically in one call. Array semantics: omit/null leaves a "
            "sub-resource untouched, `[]` deletes all records of that type, a non-empty list "
            f"replaces all records (not a merge). {_UPDATE_PERM}"
        )
    )
    @translate_errors
    async def update_practitioner_full(
        self, info: strawberry.types.Info, practitioner_id: int, input: PractitionerFullPatchInput
    ) -> PractitionerType:
        """Update a Practitioner's scalar fields and/or rewrite sub-resource arrays atomically — mirrors PATCH /practitioners/{id}/full."""
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.update_full(practitioner_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(
        description=(
            "Permanently delete a Practitioner and all its sub-resource records (name, "
            "identifier, telecom, address, photo, qualification, communication). Irreversible. "
            "Requires the `practitioner:delete` permission. Returns true on success."
        )
    )
    @translate_errors
    async def delete_practitioner(self, info: strawberry.types.Info, practitioner_id: int) -> bool:
        """Delete a Practitioner and its child records — mirrors DELETE /practitioners/{id}. Returns true on success."""
        actor = require_gql_permission(info, "practitioner", "delete")
        service = get_container(info).practitioner.practitioner_service()
        await service.delete(practitioner_id, actor)
        return True

    # ── Names ─────────────────────────────────────────────────────────────────

    @strawberry.mutation(description=f"Add a HumanName to a Practitioner. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def add_practitioner_name(self, info: strawberry.types.Info, practitioner_id: int, input: PractitionerNameCreateInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.add_name(practitioner_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Partially update a Practitioner HumanName. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def patch_practitioner_name(self, info: strawberry.types.Info, practitioner_id: int, name_id: int, input: PractitionerNamePatchInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.patch_name(practitioner_id, name_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Remove a HumanName from a Practitioner. Returns true on success. {_UPDATE_PERM}")
    @translate_errors
    async def delete_practitioner_name(self, info: strawberry.types.Info, practitioner_id: int, name_id: int) -> bool:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        await service.delete_name(practitioner_id, name_id, actor)
        return True

    # ── Identifiers ───────────────────────────────────────────────────────────

    @strawberry.mutation(description=f"Add an Identifier to a Practitioner. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def add_practitioner_identifier(self, info: strawberry.types.Info, practitioner_id: int, input: PractitionerIdentifierCreateInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.add_identifier(practitioner_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Partially update a Practitioner Identifier. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def patch_practitioner_identifier(self, info: strawberry.types.Info, practitioner_id: int, identifier_id: int, input: PractitionerIdentifierPatchInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.patch_identifier(practitioner_id, identifier_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Remove an Identifier from a Practitioner. Returns true on success. {_UPDATE_PERM}")
    @translate_errors
    async def delete_practitioner_identifier(self, info: strawberry.types.Info, practitioner_id: int, identifier_id: int) -> bool:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        await service.delete_identifier(practitioner_id, identifier_id, actor)
        return True

    # ── Telecom ───────────────────────────────────────────────────────────────

    @strawberry.mutation(description=f"Add a ContactPoint (telecom) to a Practitioner. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def add_practitioner_telecom(self, info: strawberry.types.Info, practitioner_id: int, input: PractitionerTelecomCreateInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.add_telecom(practitioner_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Partially update a Practitioner ContactPoint. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def patch_practitioner_telecom(self, info: strawberry.types.Info, practitioner_id: int, telecom_id: int, input: PractitionerTelecomPatchInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.patch_telecom(practitioner_id, telecom_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Remove a telecom entry from a Practitioner. Returns true on success. {_UPDATE_PERM}")
    @translate_errors
    async def delete_practitioner_telecom(self, info: strawberry.types.Info, practitioner_id: int, telecom_id: int) -> bool:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        await service.delete_telecom(practitioner_id, telecom_id, actor)
        return True

    # ── Addresses ─────────────────────────────────────────────────────────────

    @strawberry.mutation(description=f"Add an Address to a Practitioner. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def add_practitioner_address(self, info: strawberry.types.Info, practitioner_id: int, input: PractitionerAddressCreateInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.add_address(practitioner_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Partially update a Practitioner Address. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def patch_practitioner_address(self, info: strawberry.types.Info, practitioner_id: int, address_id: int, input: PractitionerAddressPatchInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.patch_address(practitioner_id, address_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Remove an Address from a Practitioner. Returns true on success. {_UPDATE_PERM}")
    @translate_errors
    async def delete_practitioner_address(self, info: strawberry.types.Info, practitioner_id: int, address_id: int) -> bool:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        await service.delete_address(practitioner_id, address_id, actor)
        return True

    # ── Photos ────────────────────────────────────────────────────────────────

    @strawberry.mutation(description=f"Add an Attachment (photo) to a Practitioner. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def add_practitioner_photo(self, info: strawberry.types.Info, practitioner_id: int, input: PractitionerPhotoCreateInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.add_photo(practitioner_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Partially update a Practitioner photo Attachment. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def patch_practitioner_photo(self, info: strawberry.types.Info, practitioner_id: int, photo_id: int, input: PractitionerPhotoPatchInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.patch_photo(practitioner_id, photo_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Remove a photo from a Practitioner. Returns true on success. {_UPDATE_PERM}")
    @translate_errors
    async def delete_practitioner_photo(self, info: strawberry.types.Info, practitioner_id: int, photo_id: int) -> bool:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        await service.delete_photo(practitioner_id, photo_id, actor)
        return True

    # ── Qualifications ────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=(
            "Add a qualification (certification, license, training) to a Practitioner. If "
            "`issuer` is set, it must reference an existing organization in the caller's own "
            f"tenant. Returns the full updated Practitioner. {_UPDATE_PERM}"
        )
    )
    @translate_errors
    async def add_practitioner_qualification(self, info: strawberry.types.Info, practitioner_id: int, input: PractitionerQualificationCreateInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.add_qualification(practitioner_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(
        description=(
            "Partially update a Practitioner qualification. When `identifier` is provided it "
            "fully replaces the existing identifier array. When `issuer` is provided it is "
            f"re-validated the same way as on create. Returns the full updated Practitioner. {_UPDATE_PERM}"
        )
    )
    @translate_errors
    async def patch_practitioner_qualification(self, info: strawberry.types.Info, practitioner_id: int, qualification_id: int, input: PractitionerQualificationPatchInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.patch_qualification(practitioner_id, qualification_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Remove a qualification from a Practitioner. Returns true on success. {_UPDATE_PERM}")
    @translate_errors
    async def delete_practitioner_qualification(self, info: strawberry.types.Info, practitioner_id: int, qualification_id: int) -> bool:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        await service.delete_qualification(practitioner_id, qualification_id, actor)
        return True

    # ── Communications ────────────────────────────────────────────────────────

    @strawberry.mutation(description=f"Add a language/communication preference to a Practitioner. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def add_practitioner_communication(self, info: strawberry.types.Info, practitioner_id: int, input: PractitionerCommunicationCreateInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.add_communication(practitioner_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Partially update a Practitioner communication entry. Returns the full updated Practitioner. {_UPDATE_PERM}")
    @translate_errors
    async def patch_practitioner_communication(self, info: strawberry.types.Info, practitioner_id: int, communication_id: int, input: PractitionerCommunicationPatchInput) -> PractitionerType:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.patch_communication(practitioner_id, communication_id, input.to_pydantic(), actor)
        return _to_practitioner_type(data)

    @strawberry.mutation(description=f"Remove a communication entry from a Practitioner. Returns true on success. {_UPDATE_PERM}")
    @translate_errors
    async def delete_practitioner_communication(self, info: strawberry.types.Info, practitioner_id: int, communication_id: int) -> bool:
        actor = require_gql_permission(info, "practitioner", "update")
        service = get_container(info).practitioner.practitioner_service()
        await service.delete_communication(practitioner_id, communication_id, actor)
        return True

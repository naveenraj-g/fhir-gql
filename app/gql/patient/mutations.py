import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.patient.types.types import (
    AddressCreateInput,
    AddressPatchInput,
    CommunicationCreateInput,
    CommunicationPatchInput,
    ContactCreateInput,
    ContactPatchInput,
    GeneralPractitionerCreateInput,
    GeneralPractitionerPatchInput,
    IdentifierCreateInput,
    IdentifierPatchInput,
    LinkCreateInput,
    LinkPatchInput,
    NameCreateInput,
    NamePatchInput,
    PatientCreateInput,
    PatientFullCreateInput,
    PatientFullPatchInput,
    PatientPatchInput,
    PatientType,
    PhotoCreateInput,
    PhotoPatchInput,
    TelecomCreateInput,
    TelecomPatchInput,
)
from app.gql.permissions import require_gql_permission
from app.schemas.patient.response import (
    PatientResponse,
)

# Shared RBAC-permission wording reused across every sub-resource mutation's
# description= below, so the 27 near-identical mutations don't each repeat a
# slightly different phrasing of the same rule.
_UPDATE_PERM = "Requires the `patient:update` permission."


def _to_patient_type(data: dict) -> PatientType:
    """Shared conversion: raw fhir-server dict -> validated PatientResponse -> PatientType. Every resolver below returns through this."""
    return PatientType.from_pydantic(PatientResponse.model_validate(data))


@strawberry.type(description="Mutation fields for the Patient resource.")
class PatientMutation:
    """Mutation fields for the Patient resource. Mixed into the root `Mutation` type in app/gql/schema.py (see PatientQuery docstring for why this is decorated)."""

    # ── Core CRUD ─────────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=(
            "Create a new Patient. `userId` and `orgId` are required for tenant scoping; "
            "`createdBy` is stamped automatically from the caller's JWT. Requires the "
            "`patient:create` permission."
        )
    )
    @translate_errors
    async def create_patient(
        self, info: strawberry.types.Info, input: PatientCreateInput
    ) -> PatientType:
        """Create a new Patient — mirrors POST /patients/."""
        actor = require_gql_permission(info, "patient", "create")
        service = get_container(info).patient.patient_service()
        data = await service.create(input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=(
            "Create a Patient and any combination of its sub-resources atomically in a single "
            "fhir-server transaction — if any sub-resource insert fails, the entire request "
            "rolls back and nothing is persisted. Requires the `patient:create` permission."
        )
    )
    @translate_errors
    async def create_patient_full(
        self, info: strawberry.types.Info, input: PatientFullCreateInput
    ) -> PatientType:
        """Create a Patient and any combination of its sub-resources atomically — mirrors POST /patients/full."""
        actor = require_gql_permission(info, "patient", "create")
        service = get_container(info).patient.patient_service()
        data = await service.create_full(input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=(
            "Partially update a Patient's scalar fields (active, gender, birthDate, "
            "deceased*, maritalStatus*, multipleBirth*, managingOrganization*). Sub-resource "
            "arrays are managed via their own dedicated mutations. `updatedBy` is stamped "
            "automatically from the caller's JWT. Requires the `patient:update` permission."
        )
    )
    @translate_errors
    async def update_patient(
        self, info: strawberry.types.Info, patient_id: int, input: PatientPatchInput
    ) -> PatientType:
        """Partially update a Patient's scalar fields — mirrors PATCH /patients/{id}."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.update(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=(
            "Update a Patient's scalar fields and/or rewrite any combination of its nine "
            "sub-resource arrays atomically in one call. Array semantics: omit/null leaves a "
            "sub-resource untouched, `[]` deletes all records of that type, a non-empty list "
            "replaces all records (not a merge). Requires the `patient:update` permission."
        )
    )
    @translate_errors
    async def update_patient_full(
        self, info: strawberry.types.Info, patient_id: int, input: PatientFullPatchInput
    ) -> PatientType:
        """Update scalar fields and/or rewrite sub-resource arrays atomically — mirrors PATCH /patients/{id}/full."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.update_full(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=(
            "Permanently delete a Patient and all its sub-resource records (name, identifier, "
            "telecom, address, photo, contact, communication, generalPractitioner, link). "
            "Irreversible. Requires the `patient:delete` permission. Returns true on success."
        )
    )
    @translate_errors
    async def delete_patient(
        self, info: strawberry.types.Info, patient_id: int
    ) -> bool:
        """Permanently delete a Patient and all its sub-resources — mirrors DELETE /patients/{id}. Returns true on success."""
        actor = require_gql_permission(info, "patient", "delete")
        service = get_container(info).patient.patient_service()
        await service.delete(patient_id, actor)
        return True

    # ── Names ─────────────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=f"Add a HumanName to a Patient. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def add_patient_name(
        self, info: strawberry.types.Info, patient_id: int, input: NameCreateInput
    ) -> PatientType:
        """Add a HumanName to a Patient. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.add_name(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Partially update a Patient HumanName. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def patch_patient_name(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        name_id: int,
        input: NamePatchInput,
    ) -> PatientType:
        """Partially update a Patient HumanName. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.patch_name(patient_id, name_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Remove a HumanName from a Patient. {_UPDATE_PERM} Returns true on success."
    )
    @translate_errors
    async def delete_patient_name(
        self, info: strawberry.types.Info, patient_id: int, name_id: int
    ) -> bool:
        """Remove a HumanName from a Patient. Returns true on success."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        await service.delete_name(patient_id, name_id, actor)
        return True

    # ── Identifiers ───────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=f"Add an Identifier to a Patient. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def add_patient_identifier(
        self, info: strawberry.types.Info, patient_id: int, input: IdentifierCreateInput
    ) -> PatientType:
        """Add an Identifier to a Patient. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.add_identifier(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Partially update a Patient Identifier. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def patch_patient_identifier(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        identifier_id: int,
        input: IdentifierPatchInput,
    ) -> PatientType:
        """Partially update a Patient Identifier. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.patch_identifier(
            patient_id, identifier_id, input.to_pydantic(), actor
        )
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Remove an Identifier from a Patient. {_UPDATE_PERM} Returns true on success."
    )
    @translate_errors
    async def delete_patient_identifier(
        self, info: strawberry.types.Info, patient_id: int, identifier_id: int
    ) -> bool:
        """Remove an Identifier from a Patient. Returns true on success."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        await service.delete_identifier(patient_id, identifier_id, actor)
        return True

    # ── Telecom ───────────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=f"Add a ContactPoint (telecom) to a Patient. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def add_patient_telecom(
        self, info: strawberry.types.Info, patient_id: int, input: TelecomCreateInput
    ) -> PatientType:
        """Add a ContactPoint (telecom) to a Patient. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.add_telecom(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Partially update a Patient ContactPoint. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def patch_patient_telecom(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        telecom_id: int,
        input: TelecomPatchInput,
    ) -> PatientType:
        """Partially update a Patient ContactPoint. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.patch_telecom(
            patient_id, telecom_id, input.to_pydantic(), actor
        )
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Remove a telecom entry from a Patient. {_UPDATE_PERM} Returns true on success."
    )
    @translate_errors
    async def delete_patient_telecom(
        self, info: strawberry.types.Info, patient_id: int, telecom_id: int
    ) -> bool:
        """Remove a telecom entry from a Patient. Returns true on success."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        await service.delete_telecom(patient_id, telecom_id, actor)
        return True

    # ── Addresses ─────────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=f"Add an Address to a Patient. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def add_patient_address(
        self, info: strawberry.types.Info, patient_id: int, input: AddressCreateInput
    ) -> PatientType:
        """Add an Address to a Patient. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.add_address(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Partially update a Patient Address. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def patch_patient_address(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        address_id: int,
        input: AddressPatchInput,
    ) -> PatientType:
        """Partially update a Patient Address. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.patch_address(
            patient_id, address_id, input.to_pydantic(), actor
        )
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Remove an Address from a Patient. {_UPDATE_PERM} Returns true on success."
    )
    @translate_errors
    async def delete_patient_address(
        self, info: strawberry.types.Info, patient_id: int, address_id: int
    ) -> bool:
        """Remove an Address from a Patient. Returns true on success."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        await service.delete_address(patient_id, address_id, actor)
        return True

    # ── Photos ────────────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=f"Add an Attachment (photo) to a Patient. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def add_patient_photo(
        self, info: strawberry.types.Info, patient_id: int, input: PhotoCreateInput
    ) -> PatientType:
        """Add an Attachment (photo) to a Patient. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.add_photo(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Partially update a Patient photo Attachment. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def patch_patient_photo(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        photo_id: int,
        input: PhotoPatchInput,
    ) -> PatientType:
        """Partially update a Patient photo Attachment. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.patch_photo(
            patient_id, photo_id, input.to_pydantic(), actor
        )
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Remove a photo from a Patient. {_UPDATE_PERM} Returns true on success."
    )
    @translate_errors
    async def delete_patient_photo(
        self, info: strawberry.types.Info, patient_id: int, photo_id: int
    ) -> bool:
        """Remove a photo from a Patient. Returns true on success."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        await service.delete_photo(patient_id, photo_id, actor)
        return True

    # ── Contacts ──────────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=(
            "Add a contact person (next-of-kin, guardian, emergency contact) to a Patient, "
            f"with nested relationship[] and telecom[] arrays. Returns the full updated Patient. {_UPDATE_PERM}"
        )
    )
    @translate_errors
    async def add_patient_contact(
        self, info: strawberry.types.Info, patient_id: int, input: ContactCreateInput
    ) -> PatientType:
        """Add a contact person (next-of-kin/guardian/emergency) to a Patient. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.add_contact(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=(
            "Partially update a Patient contact. When relationship or telecom arrays are "
            f"provided, they replace the existing array entirely. Returns the full updated Patient. {_UPDATE_PERM}"
        )
    )
    @translate_errors
    async def patch_patient_contact(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        contact_id: int,
        input: ContactPatchInput,
    ) -> PatientType:
        """Partially update a Patient contact. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.patch_contact(
            patient_id, contact_id, input.to_pydantic(), actor
        )
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Remove a contact and its child relationship/telecom records from a Patient. {_UPDATE_PERM} Returns true on success."
    )
    @translate_errors
    async def delete_patient_contact(
        self, info: strawberry.types.Info, patient_id: int, contact_id: int
    ) -> bool:
        """Remove a contact (and its child relationship/telecom records) from a Patient. Returns true on success."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        await service.delete_contact(patient_id, contact_id, actor)
        return True

    # ── Communications ────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=f"Add a language/communication preference to a Patient. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def add_patient_communication(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        input: CommunicationCreateInput,
    ) -> PatientType:
        """Add a language/communication preference to a Patient. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.add_communication(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Partially update a Patient communication entry. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def patch_patient_communication(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        comm_id: int,
        input: CommunicationPatchInput,
    ) -> PatientType:
        """Partially update a Patient communication entry. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.patch_communication(
            patient_id, comm_id, input.to_pydantic(), actor
        )
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Remove a communication entry from a Patient. {_UPDATE_PERM} Returns true on success."
    )
    @translate_errors
    async def delete_patient_communication(
        self, info: strawberry.types.Info, patient_id: int, comm_id: int
    ) -> bool:
        """Remove a communication entry from a Patient. Returns true on success."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        await service.delete_communication(patient_id, comm_id, actor)
        return True

    # ── General Practitioners ─────────────────────────────────────────────────

    @strawberry.mutation(
        description=(
            "Add a generalPractitioner reference to a Patient. `referenceType` must be "
            f"Organization, Practitioner, or PractitionerRole. Returns the full updated Patient. {_UPDATE_PERM}"
        )
    )
    @translate_errors
    async def add_patient_general_practitioner(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        input: GeneralPractitionerCreateInput,
    ) -> PatientType:
        """Add a generalPractitioner reference to a Patient. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.add_general_practitioner(
            patient_id, input.to_pydantic(), actor
        )
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Partially update a Patient generalPractitioner reference. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def patch_patient_general_practitioner(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        gp_id: int,
        input: GeneralPractitionerPatchInput,
    ) -> PatientType:
        """Partially update a Patient generalPractitioner reference. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.patch_general_practitioner(
            patient_id, gp_id, input.to_pydantic(), actor
        )
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Remove a generalPractitioner reference from a Patient. {_UPDATE_PERM} Returns true on success."
    )
    @translate_errors
    async def delete_patient_general_practitioner(
        self, info: strawberry.types.Info, patient_id: int, gp_id: int
    ) -> bool:
        """Remove a generalPractitioner reference from a Patient. Returns true on success."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        await service.delete_general_practitioner(patient_id, gp_id, actor)
        return True

    # ── Links ─────────────────────────────────────────────────────────────────

    @strawberry.mutation(
        description=f"Link this Patient to another Patient or RelatedPerson. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def add_patient_link(
        self, info: strawberry.types.Info, patient_id: int, input: LinkCreateInput
    ) -> PatientType:
        """Link this Patient to another Patient or RelatedPerson. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.add_link(patient_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Partially update a Patient link. Returns the full updated Patient. {_UPDATE_PERM}"
    )
    @translate_errors
    async def patch_patient_link(
        self,
        info: strawberry.types.Info,
        patient_id: int,
        link_id: int,
        input: LinkPatchInput,
    ) -> PatientType:
        """Partially update a Patient link. Returns the full updated Patient."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        data = await service.patch_link(patient_id, link_id, input.to_pydantic(), actor)
        return _to_patient_type(data)

    @strawberry.mutation(
        description=f"Remove a link from a Patient. {_UPDATE_PERM} Returns true on success."
    )
    @translate_errors
    async def delete_patient_link(
        self, info: strawberry.types.Info, patient_id: int, link_id: int
    ) -> bool:
        """Remove a link from a Patient. Returns true on success."""
        actor = require_gql_permission(info, "patient", "update")
        service = get_container(info).patient.patient_service()
        await service.delete_link(patient_id, link_id, actor)
        return True

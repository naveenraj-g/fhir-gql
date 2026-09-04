from __future__ import annotations

import strawberry

from app.gql.context import get_container
from app.gql.patient.loaders import (
    list_address_for_patient,
    list_communication_for_patient,
    list_contact_for_patient,
    list_general_practitioner_for_patient,
    list_identifiers_for_patient,
    list_link_for_patient,
    list_names_for_patient,
    list_photo_for_patient,
    list_telecom_for_patient,
)
from app.gql.patient.types.types import (
    PatientAddressType,
    PatientCommunicationType,
    PatientContactType,
    PatientGeneralPractitionerType,
    PatientIdentifierType,
    PatientLinkType,
    PatientNameType,
    PatientPhotoType,
    PatientTelecomType,
)
from app.gql.permissions import require_gql_permission
from app.schemas.patient.response import PatientCoreResponse

# @strawberry.type
# class GetPatient:
#     patient_id: strawberry.Private[int]

#     @strawberry.field
#     async def patient_core(self, info: strawberry.types.Info) -> PatientCoreType:
#         return await get_patient_core(patient_id=self.patient_id, info=info)

#     @strawberry.field
#     async def patient_name(self, info: strawberry.types.Info) -> List[PatientNameType]:
#         return await list_names_for_patient(patient_id=self.patient_id, info=info)

#     @strawberry.field
#     async def patient_identifier(
#         self, info: strawberry.types.Info
#     ) -> List[PatientIdentifierType]:
#         return await list_identifiers_for_patient(patient_id=self.patient_id, info=info)

"""
PatientCoreType — a Patient's scalar fields plus name/identifier as
lazily-fetched fields. Lives under types/operations/ (not types/types.py)
because it attaches resolver methods that call loaders.py, same category as
GetPatient in this same folder — see that module's docstring for the general
rule: plain `all_fields=True` data types with no extra methods live in
types.py, anything with a hand-written @strawberry.field method lives here.

Kept in its own module (not folded into types.py) specifically to avoid a
circular import: this type's field methods need functions from
app.gql.patient.loaders, and loaders.py needs the leaf types
(PatientNameType/PatientIdentifierType) from types.py. If this type lived in
types.py too, loaders.py and types.py would need to import from each other
at module load time. Keeping it here instead makes the dependency graph a
straight line: types.py (leaf types) -> loaders.py -> this module. Neither
types.py nor loaders.py imports anything from here, so nothing loops back.
"""


@strawberry.experimental.pydantic.type(
    model=PatientCoreResponse,
    all_fields=True,
    description=(
        "A Patient resource's scalar fields, plus name/identifier as lazily-fetched "
        "fields — each only calls the fhir-server if the client's query actually "
        "selects it. The other seven sub-resource arrays (telecom, address, photo, "
        "contact, communication, generalPractitioner, link) are still not present on "
        "this type at all; see PatientLazyType for the full nine-field version of "
        "this pattern. Returned by the `patientCore` query, which otherwise mirrors "
        "GET /patients/{patient_id}/core."
    ),
)
class PatientCoreType:
    """A Patient resource's scalar fields, plus name/identifier as lazily-fetched fields."""

    @strawberry.field(
        description="This Patient's HumanName entries. Lazily fetched via list_names() only if selected. Requires `patient:read`."
    )
    @staticmethod
    async def name(
        parent: strawberry.Parent[PatientCoreType], info: strawberry.types.Info
    ) -> list[PatientNameType]:
        return await list_names_for_patient(parent.id, info)

    @strawberry.field(
        description="This Patient's Identifier entries. Lazily fetched via list_identifiers() only if selected. Requires `patient:read`."
    )
    @staticmethod
    async def identifier(
        parent: strawberry.Parent[PatientCoreType], info: strawberry.types.Info
    ) -> list[PatientIdentifierType]:
        return await list_identifiers_for_patient(parent.id, info)

    @strawberry.field(
        description="This Patient's Telecom entries. Lazily fetched via list_telecom() only if selected. Requires `patient:read`."
    )
    @staticmethod
    async def telecom(
        parent: strawberry.Parent[PatientCoreType], info: strawberry.types.Info
    ) -> list[PatientTelecomType]:
        return await list_telecom_for_patient(parent.id, info)

    @strawberry.field(
        description="This Patient's Address entries (home/work/temp addresses). Lazily fetched via list_addresses() only if selected. Requires `patient:read`."
    )
    @staticmethod
    async def address(
        parent: strawberry.Parent[PatientCoreType], info: strawberry.types.Info
    ) -> list[PatientAddressType]:
        return await list_address_for_patient(parent.id, info)

    @strawberry.field(
        description="This Patient's Attachment (photo) entries. Lazily fetched via list_photos() only if selected. Requires `patient:read`."
    )
    @staticmethod
    async def photo(
        parent: strawberry.Parent[PatientCoreType], info: strawberry.types.Info
    ) -> list[PatientPhotoType]:
        return await list_photo_for_patient(parent.id, info)

    @strawberry.field(
        description="This Patient's contact entries (e.g. emergency contacts / related persons). Lazily fetched via list_contacts() only if selected. Requires `patient:read`."
    )
    @staticmethod
    async def contact(
        parent: strawberry.Parent[PatientCoreType], info: strawberry.types.Info
    ) -> list[PatientContactType]:
        return await list_contact_for_patient(parent.id, info)

    @strawberry.field(
        description="This Patient's communication entries (preferred spoken/written languages). Lazily fetched via list_communications() only if selected. Requires `patient:read`."
    )
    @staticmethod
    async def communication(
        parent: strawberry.Parent[PatientCoreType], info: strawberry.types.Info
    ) -> list[PatientCommunicationType]:
        return await list_communication_for_patient(parent.id, info)

    @strawberry.field(
        description="This Patient's generalPractitioner references (Practitioner/Organization treating this patient). Lazily fetched via list_general_practitioners() only if selected. Requires `patient:read`."
    )
    @staticmethod
    async def general_practitioner(
        parent: strawberry.Parent[PatientCoreType], info: strawberry.types.Info
    ) -> list[PatientGeneralPractitionerType]:
        return await list_general_practitioner_for_patient(parent.id, info)

    @strawberry.field(
        description="This Patient's link entries (references to other Patient/RelatedPerson resources for the same individual, e.g. merged records). Lazily fetched via list_links() only if selected. Requires `patient:read`."
    )
    @staticmethod
    async def link(
        parent: strawberry.Parent[PatientCoreType], info: strawberry.types.Info
    ) -> list[PatientLinkType]:
        return await list_link_for_patient(parent.id, info)


async def get_patient(patient_id: int, info: strawberry.types.Info) -> PatientCoreType:
    """
    Fetch + convert PatientCoreType's own data for a given patient.

    Lives here, not in loaders.py: this builds the ROOT object (the same job
    _to_patient_core_type() does in resolvers.py), not a child collection for
    an already-known parent — that distinction is what loaders.py is for.
    Keeping it here also avoids recreating the circular import loaders.py
    would have if it needed to import PatientCoreType back from this module.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.get_core_by_id(patient_id, actor)
    return PatientCoreType.from_pydantic(PatientCoreResponse.model_validate(data))

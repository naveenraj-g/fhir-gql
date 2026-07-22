"""
Lazy-loader functions for each of a Patient's nine sub-resource collections.

Each function fetches one patient's sub-resource list from the fhir-server
(via PatientService) and converts the plain-JSON items into their
corresponding strawberry GraphQL type. These are called from the
lazily-fetched `@strawberry.field` resolvers on PatientCoreType (see
app/gql/patient/types/operations/get_patient.py) — each sub-resource is only
fetched when the client's GraphQL query actually selects that field, instead
of always eagerly loading all nine like the plain PatientType/PatientResponse
shape does.

All nine functions follow the same three-step shape: check permission, call
the matching PatientService list_*() method, then map each raw dict through
`<Type>.model_validate()` + `<GraphQLType>.from_pydantic()`. Defined as plain
module-level functions rather than classmethods on the corresponding GraphQL
type, because `strawberry.experimental.pydantic.type` rebuilds the decorated
class and only keeps strawberry-recognized members (fields, from_pydantic/
to_pydantic) — any plain classmethod added in the class body would be
silently dropped. Same convention `_to_patient_type()` already uses in
app/gql/resolvers/patient.py.
"""

from typing import List

import strawberry

from app.gql.context import get_container
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
from app.schemas.patient.response import (
    PatientAddressResponse,
    PatientCommunicationResponse,
    PatientContactResponse,
    PatientGeneralPractitionerResponse,
    PatientIdentifierResponse,
    PatientLinkResponse,
    PatientNameResponse,
    PatientPhotoResponse,
    PatientTelecomResponse,
)


async def list_identifiers_for_patient(
    patient_id: int, info: strawberry.types.Info
) -> List[PatientIdentifierType]:
    """
    Fetch this patient's Identifier entries (e.g. MRN, SSN, insurance IDs)
    and convert them to PatientIdentifierType.

    Calls PatientService.list_identifiers(), which hits the fhir-server's
    GET /patients/{patient_id}/identifiers endpoint. Requires the caller to
    hold `patient:read` — enforced up front via require_gql_permission()
    before any network call is made.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.list_identifiers(patient_id, actor)
    return [
        PatientIdentifierType.from_pydantic(
            PatientIdentifierResponse.model_validate(item)
        )
        for item in data["data"]
    ]


async def list_names_for_patient(
    patient_id: int, info: strawberry.types.Info
) -> List[PatientNameType]:
    """
    Fetch + convert PatientNameType's own data for a given patient.

    A plain module-level function, not a classmethod on PatientNameType:
    `strawberry.experimental.pydantic.type` rebuilds the decorated class and
    only keeps strawberry-recognized members (fields, from_pydantic/
    to_pydantic) — any plain classmethod added in the class body is silently
    dropped. Same convention `_to_patient_type()` already uses in
    app/gql/resolvers/patient.py.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.list_names(patient_id, actor)
    return [
        PatientNameType.from_pydantic(PatientNameResponse.model_validate(item))
        for item in data["data"]
    ]


async def list_telecom_for_patient(
    patient_id: int, info: strawberry.types.Info
) -> List[PatientTelecomType]:
    """
    Fetch this patient's ContactPoint (telecom — phone/email/fax) entries
    and convert them to PatientTelecomType.

    Calls PatientService.list_telecom(), which hits the fhir-server's
    GET /patients/{patient_id}/telecom endpoint. Requires `patient:read`,
    same rationale as list_identifiers_for_patient() above.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.list_telecom(patient_id, actor)
    return [
        PatientTelecomType.from_pydantic(PatientTelecomResponse.model_validate(item))
        for item in data["data"]
    ]


async def list_address_for_patient(
    patient_id: int, info: strawberry.types.Info
) -> List[PatientAddressType]:
    """
    Fetch this patient's Address entries (home/work/temp addresses) and
    convert them to PatientAddressType.

    Calls PatientService.list_addresses(), which hits the fhir-server's
    GET /patients/{patient_id}/addresses endpoint. Requires `patient:read`,
    same rationale as list_identifiers_for_patient() above.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.list_addresses(patient_id, actor)
    return [
        PatientAddressType.from_pydantic(PatientAddressResponse.model_validate(item))
        for item in data["data"]
    ]


async def list_photo_for_patient(
    patient_id: int, info: strawberry.types.Info
) -> List[PatientPhotoType]:
    """
    Fetch this patient's Attachment (photo) entries and convert them to
    PatientPhotoType.

    Calls PatientService.list_photos(), which hits the fhir-server's
    GET /patients/{patient_id}/photos endpoint. Requires `patient:read`,
    same rationale as list_identifiers_for_patient() above.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.list_photos(patient_id, actor)
    return [
        PatientPhotoType.from_pydantic(PatientPhotoResponse.model_validate(item))
        for item in data["data"]
    ]


async def list_contact_for_patient(
    patient_id: int, info: strawberry.types.Info
) -> List[PatientContactType]:
    """
    Fetch this patient's contact entries (BackboneElement — e.g. emergency
    contacts / related persons, each with their own name/telecom/address/
    relationship) and convert them to PatientContactType.

    Calls PatientService.list_contacts(), which hits the fhir-server's
    GET /patients/{patient_id}/contacts endpoint. Requires `patient:read`,
    same rationale as list_identifiers_for_patient() above.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.list_contacts(patient_id, actor)
    return [
        PatientContactType.from_pydantic(PatientContactResponse.model_validate(item))
        for item in data["data"]
    ]


async def list_communication_for_patient(
    patient_id: int, info: strawberry.types.Info
) -> List[PatientCommunicationType]:
    """
    Fetch this patient's communication entries (preferred spoken/written
    languages) and convert them to PatientCommunicationType.

    Calls PatientService.list_communications(), which hits the fhir-server's
    GET /patients/{patient_id}/communications endpoint. Requires
    `patient:read`, same rationale as list_identifiers_for_patient() above.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.list_communications(patient_id, actor)
    return [
        PatientCommunicationType.from_pydantic(
            PatientCommunicationResponse.model_validate(item)
        )
        for item in data["data"]
    ]


async def list_general_practitioner_for_patient(
    patient_id: int, info: strawberry.types.Info
) -> List[PatientGeneralPractitionerType]:
    """
    Fetch this patient's generalPractitioner references (links to the
    Practitioner/Organization resources treating this patient) and convert
    them to PatientGeneralPractitionerType.

    Calls PatientService.list_general_practitioners(), which hits the
    fhir-server's GET /patients/{patient_id}/general-practitioners endpoint.
    Requires `patient:read`, same rationale as
    list_identifiers_for_patient() above.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.list_general_practitioners(patient_id, actor)
    return [
        PatientGeneralPractitionerType.from_pydantic(
            PatientGeneralPractitionerResponse.model_validate(item)
        )
        for item in data["data"]
    ]


async def list_link_for_patient(
    patient_id: int, info: strawberry.types.Info
) -> List[PatientLinkType]:
    """
    Fetch this patient's link entries (references to other Patient or
    RelatedPerson resources representing the same real-world individual,
    e.g. merged/duplicate records) and convert them to PatientLinkType.

    Calls PatientService.list_links(), which hits the fhir-server's
    GET /patients/{patient_id}/links endpoint. Requires `patient:read`,
    same rationale as list_identifiers_for_patient() above.
    """
    actor = require_gql_permission(info, "patient", "read")
    service = get_container(info).patient.patient_service()
    data = await service.list_links(patient_id, actor)
    return [
        PatientLinkType.from_pydantic(PatientLinkResponse.model_validate(item))
        for item in data["data"]
    ]

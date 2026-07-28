from datetime import date
from typing import Annotated

import strawberry

from app.gql.context import get_container
from app.gql.enums import (
    AdministrativeGenderEnum,
    GeneralPractitionerReferenceTypeEnum,
    TotalModeEnum,
)
from app.gql.errors import translate_errors
from app.gql.patient.types.operations.get_patient import (
    PatientCoreType,
    get_patient,
)
from app.gql.patient.types.types import PaginatedPatientType
from app.gql.permissions import require_gql_permission
from app.schemas.patient.input import ListPatientsSchema
from app.schemas.patient.response import PaginatedPatientResponse


def _to_paginated_patient_type(data: dict) -> PaginatedPatientType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedPatientResponse -> PaginatedPatientType."""
    return PaginatedPatientType.from_pydantic(
        PaginatedPatientResponse.model_validate(data)
    )


@strawberry.type
class PatientQuery:
    @strawberry.field
    @translate_errors
    async def patient(
        self,
        info: strawberry.types.Info,
        patient_id: Annotated[
            int, strawberry.argument(description="patient_id to filter patient data")
        ],
    ) -> PatientCoreType:
        return await get_patient(patient_id=patient_id, info=info)

    @strawberry.field(
        description=(
            "List Patients, optionally filtered by `familyName`/`givenName` (partial, "
            "case-insensitive), `identifier` (exact), `gender`, `active`, `deceased`, "
            "`birthDateFrom`/`birthDateTo` (inclusive range), `addressCity`/`addressState`/"
            "`addressPostalCode`, `email`/`phone` (telecom), `generalPractitionerType`/"
            "`generalPractitionerId`, `organizationId` (managingOrganization), `userId`, or "
            "`orgId`, with `sort` (e.g. `-birthDate`), `totalMode` (`accurate`|`none`), and "
            "`limit`/`offset` pagination (default limit 50, max 200). Requires the "
            "`patient:read` permission."
        )
    )
    @translate_errors
    async def patients(
        self,
        info: strawberry.types.Info,
        family_name: str | None = None,
        given_name: str | None = None,
        gender: AdministrativeGenderEnum | None = None,
        active: bool | None = None,
        user_id: str | None = None,
        org_id: str | None = None,
        identifier: str | None = None,
        birth_date_from: date | None = None,
        birth_date_to: date | None = None,
        address_city: str | None = None,
        address_state: str | None = None,
        address_postal_code: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        deceased: bool | None = None,
        general_practitioner_type: GeneralPractitionerReferenceTypeEnum | None = None,
        general_practitioner_id: int | None = None,
        organization_id: int | None = None,
        sort: str | None = None,
        total_mode: TotalModeEnum = TotalModeEnum.accurate,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedPatientType:
        """List Patients with optional filters — mirrors GET /patients/."""
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        filters = ListPatientsSchema(
            family_name=family_name,
            given_name=given_name,
            gender=gender,
            active=active,
            user_id=user_id,
            org_id=org_id,
            identifier=identifier,
            birth_date_from=birth_date_from,
            birth_date_to=birth_date_to,
            address_city=address_city,
            address_state=address_state,
            address_postal_code=address_postal_code,
            email=email,
            phone=phone,
            deceased=deceased,
            general_practitioner_type=general_practitioner_type,
            general_practitioner_id=general_practitioner_id,
            organization_id=organization_id,
            sort=sort,
            total_mode=total_mode.value,
            limit=limit,
            offset=offset,
        )
        data = await service.list(filters, actor)
        return _to_paginated_patient_type(data)

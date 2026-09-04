from typing import Annotated

import strawberry

from app.gql.context import get_container
from app.gql.enums import (
    AddressUseEnum,
    AdministrativeGenderEnum,
    TotalModeEnum,
)
from app.gql.errors import translate_errors
from app.gql.patient.types.operations.get_patient import (
    PatientCoreType,
    get_patient,
)
from app.gql.patient.types.types import PaginatedPatientType, PatientType
from app.gql.permissions import require_gql_permission
from app.schemas.patient.input import ListPatientsSchema
from app.schemas.patient.response import PaginatedPatientResponse, PatientResponse


def _to_paginated_patient_type(data: dict) -> PaginatedPatientType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedPatientResponse -> PaginatedPatientType."""
    return PaginatedPatientType.from_pydantic(
        PaginatedPatientResponse.model_validate(data)
    )


def _to_patient_type(data: dict) -> PatientType:
    """Shared conversion: raw fhir-server dict -> validated PatientResponse -> PatientType.
    Duplicated from app.gql.patient.mutations (same two-line helper) rather than
    imported, matching this codebase's existing per-module convention of not
    cross-importing private helpers between queries.py/mutations.py."""
    return PatientType.from_pydantic(PatientResponse.model_validate(data))


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
            "List Patients, optionally filtered by `family`/`given`/`name` (partial, "
            "case-insensitive), `identifier` (exact), `gender`, `active`, `userId`, "
            "`birthdate`/`deathDate` (comparator-prefixed, e.g. `ge2020-01-01`; repeat for "
            "a range), `deceased`, `address`/`addressCity`/`addressState`/"
            "`addressPostalCode`/`addressCountry`/`addressUse`, `telecom`/`email`/`phone`, "
            "`language`, `generalPractitioner`/`organization`/`link` (FHIR reference strings, "
            "e.g. `Organization/190001`), with `sort` (e.g. `-birthdate`), `totalMode` "
            "(`accurate`|`none`), and `limit`/`offset` pagination (default limit 50, max "
            "200). `orgId` is not a filter — Patient reads are always scoped to the "
            "caller's own org via their JWT. Requires the `patient:read` permission."
        )
    )
    @translate_errors
    async def patients(
        self,
        info: strawberry.types.Info,
        family: str | None = None,
        given: str | None = None,
        name: str | None = None,
        gender: AdministrativeGenderEnum | None = None,
        active: bool | None = None,
        user_id: str | None = None,
        identifier: str | None = None,
        birthdate: list[str] | None = None,
        death_date: list[str] | None = None,
        deceased: bool | None = None,
        address: str | None = None,
        address_city: str | None = None,
        address_state: str | None = None,
        address_postal_code: str | None = None,
        address_country: str | None = None,
        address_use: AddressUseEnum | None = None,
        telecom: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        language: str | None = None,
        general_practitioner: str | None = None,
        organization: str | None = None,
        link: str | None = None,
        sort: str | None = None,
        total_mode: TotalModeEnum = TotalModeEnum.accurate,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedPatientType:
        """List Patients with optional filters — mirrors GET /patients/."""
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        filters = ListPatientsSchema(
            family=family,
            given=given,
            name=name,
            gender=gender,
            active=active,
            user_id=user_id,
            identifier=identifier,
            birthdate=birthdate,
            death_date=death_date,
            deceased=deceased,
            address=address,
            address_city=address_city,
            address_state=address_state,
            address_postal_code=address_postal_code,
            address_country=address_country,
            address_use=address_use,
            telecom=telecom,
            email=email,
            phone=phone,
            language=language,
            general_practitioner=general_practitioner,
            organization=organization,
            link=link,
            sort=sort,
            total_mode=total_mode.value,
            limit=limit,
            offset=offset,
        )
        data = await service.list(filters, actor)
        return _to_paginated_patient_type(data)

    @strawberry.field(
        description=(
            "Fetch the Patient record belonging to the caller's own JWT identity "
            "(matched on `userId`). Requires the `patient:read` permission."
        )
    )
    @translate_errors
    async def my_patient(self, info: strawberry.types.Info) -> PatientType:
        """Fetch the caller's own Patient record — mirrors GET /patients/me."""
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.get_me(actor)
        return _to_patient_type(data)

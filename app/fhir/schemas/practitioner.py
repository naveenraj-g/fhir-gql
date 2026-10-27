"""
Pydantic models representing the genuine FHIR R4 Practitioner resource
shape — the canonical shape shared by every connector and by the GraphQL
boundary itself. Mirrors app.fhir.schemas.organization/location/
healthcare_service's pattern exactly — see those modules' docstrings for
the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Period, Identifier, ContactPoint, Address, HumanName, Attachment,
Reference) is imported from app.fhir.schemas.datatypes rather than
redefined here. Only `FhirPractitionerQualification` stays local: it's
Practitioner's own `qualification` BackboneElement (an anonymous nested
structure the R4 spec defines specifically for this resource), not reused
across other resources.

`FhirPractitionerInput` is the write-side counterpart, used by both
createFhirPractitioner/updateFhirPractitioner (see
app.gql.practitioner.mutations).

FHIR R4 Practitioner resource spec: https://hl7.org/fhir/R4/practitioner.html
"""

from datetime import date

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirAddress,
    FhirAttachment,
    FhirCodeableConcept,
    FhirContactPoint,
    FhirHumanName,
    FhirIdentifier,
    FhirMeta,
    FhirPeriod,
    FhirReference,
)


class FhirPractitionerQualification(BaseModel):
    """Practitioner.qualification (0..* BackboneElement) — certifications,
    licenses, or training."""

    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="Identifier(s) for this qualification"
    )
    code: FhirCodeableConcept | None = Field(
        default=None, description="Coded representation of the qualification"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Period during which the qualification is valid"
    )
    issuer: FhirReference | None = Field(
        default=None, description="Organization that regulates and issues the qualification"
    )


class FhirPractitionerResponse(BaseModel):
    resourceType: str = Field(
        default="Practitioner",
        description="Always 'Practitioner' — identifies the FHIR resource type",
    )
    id: str = Field(
        description="Logical FHIR resource ID (string representation of the DB primary key)"
    )
    meta: FhirMeta | None = Field(
        default=None,
        description=(
            "Infrastructure-maintained resource metadata — lastUpdated, plus "
            "org_id/created_by/updated_by/created_at as extensions (FHIR R4's "
            "Meta has no native field for those). Response-only: not part of "
            "FhirPractitionerInput, since this is server-derived "
            "audit/tenant data, not something a client writes."
        ),
    )
    extension: list[dict] | None = Field(
        default=None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="Identifiers for the person in this role"
    )
    active: bool | None = Field(
        default=None, description="Whether this practitioner's record is in active use"
    )
    name: list[FhirHumanName] | None = Field(
        default=None, description="Name(s) associated with the practitioner"
    )
    telecom: list[FhirContactPoint] | None = Field(
        default=None, description="Contact detail(s) applying to all roles"
    )
    address: list[FhirAddress] | None = Field(
        default=None, description="Address(es), typically home"
    )
    gender: str | None = Field(default=None, description="male | female | other | unknown")
    birthDate: date | None = Field(default=None, description="Date of birth")
    photo: list[FhirAttachment] | None = Field(
        default=None, description="Image(s) of the person"
    )
    qualification: list[FhirPractitionerQualification] | None = Field(
        default=None, description="Certification(s), license(s), or training"
    )
    communication: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="Language(s) the practitioner can use in patient communication",
    )


class FhirPractitionerBundleEntry(BaseModel):
    resource: FhirPractitionerResponse = Field(
        description="The FHIR Practitioner resource contained in this entry"
    )


class FhirPractitionerBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirPractitionerBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one Practitioner resource"
    )


class FhirPractitionerInput(BaseModel):
    """
    The write-side counterpart to FhirPractitionerResponse — same genuine
    FHIR R4 Practitioner shape, minus `resourceType`/`id`/`meta`. Used
    as-is for BOTH create and update (see module docstring).

    fhir-server's own PractitionerCreateSchema keeps a plain `user_id`
    field (unlike Organization/Location/HealthcareService) since a
    Practitioner record is scoped to an individual end-user's own account
    — but `user_id` has no FHIR R4 Practitioner field to carry it, so this
    canonical shape has no source for it either. It's optional on
    fhir-server's side (defaults to None), so this is a known, narrower gap
    rather than a blocker — same spirit as the Reference logical-identifier
    fallback gaps documented in app.connectors.internal.translators.organization.
    """

    identifier: list[FhirIdentifier] | None = Field(default=None)
    active: bool | None = Field(default=None)
    name: list[FhirHumanName] | None = Field(default=None)
    telecom: list[FhirContactPoint] | None = Field(default=None)
    address: list[FhirAddress] | None = Field(default=None)
    gender: str | None = Field(default=None)
    birthDate: date | None = Field(default=None)
    photo: list[FhirAttachment] | None = Field(default=None)
    qualification: list[FhirPractitionerQualification] | None = Field(default=None)
    communication: list[FhirCodeableConcept] | None = Field(default=None)
    extension: list[dict] | None = Field(default=None)

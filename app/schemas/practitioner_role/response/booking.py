"""
Booking-enriched response schemas for GET /practitioner-roles/booking.

NOT part of the current fhir-server API — no `/practitioner-roles/booking`
route exists in app/routers/practitioner_role/core.py on fhir-server as of
this port. These schemas predate that observation and are kept as-is here,
out of scope for the JWT-rollout/schema-restructure work applied to the
rest of this resource; calling `list_for_booking()` will 404 against a
real fhir-server instance.

Each item includes the linked Practitioner's name, gender, photo, and
qualifications alongside the role data, plus enriched Location/
HealthcareService data.
"""

from pydantic import BaseModel, ConfigDict, Field

from .healthcare_service import PractitionerRoleHealthcareServiceResponse
from .location import PractitionerRoleLocationResponse
from .core import PractitionerRoleResponse


class PractitionerRoleQualificationResponse(BaseModel):
    """A single qualification entry for a Practitioner in the booking response."""

    model_config = ConfigDict(extra="allow")

    code: str | None = None
    display: str | None = None
    text: str | None = None


class PractitionerRoleNameResponse(BaseModel):
    """Structured name for a Practitioner in the booking response."""

    model_config = ConfigDict(extra="allow")

    text: str | None = None
    family: str | None = None
    given: list[str] | None = None
    prefix: list[str] | None = None
    suffix: list[str] | None = None


class PractitionerRoleDetailTelecomResponse(BaseModel):
    """A single telecom entry within the booking response's practitioner_detail block."""

    model_config = ConfigDict(extra="allow")

    system: str | None = None
    value: str | None = None
    use: str | None = None
    rank: int | None = None


class PractitionerRoleDetailLanguageResponse(BaseModel):
    """A single language entry within the booking response's practitioner_detail block."""

    model_config = ConfigDict(extra="allow")

    code: str | None = None
    display: str | None = None
    preferred: bool | None = None


class PractitionerDetailResponse(BaseModel):
    """
    Enriched Practitioner data embedded in each booking response item — the
    fhir-server joins the linked Practitioner record onto the
    PractitionerRole so booking UIs don't need a second request.

    `telecom`/`languages` are typed (rather than left as raw dicts) so they
    translate into proper nested GraphQL object types instead of an opaque
    JSON scalar — same reasoning applied to every other resource's
    sub-arrays in this project.
    """

    model_config = ConfigDict(extra="allow")

    id: int | None = None
    gender: str | None = None
    birth_date: str | None = None
    name: PractitionerRoleNameResponse | None = None
    telecom: list[PractitionerRoleDetailTelecomResponse] | None = None
    languages: list[PractitionerRoleDetailLanguageResponse] | None = None
    qualifications: list[PractitionerRoleQualificationResponse] | None = None
    photo_url: str | None = None


class PractitionerRoleBookingLocationResponse(PractitionerRoleLocationResponse):
    """Location reference enriched with Location model data for booking UIs."""

    model_config = ConfigDict(extra="allow")

    name: str | None = None
    address_text: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_postal_code: str | None = None
    address_country: str | None = None
    phone: str | None = None


class PractitionerRoleBookingHealthcareServiceResponse(
    PractitionerRoleHealthcareServiceResponse
):
    """HealthcareService reference enriched with HealthcareService model data for booking UIs."""

    model_config = ConfigDict(extra="allow")

    name: str | None = None
    comment: str | None = None
    appointment_required: bool | None = None
    category: str | None = None
    availability_exceptions: str | None = None


class PractitionerRoleBookingResponse(PractitionerRoleResponse):
    """
    PractitionerRole enriched with the linked Practitioner's details and
    resolved Location/HealthcareService data — used by GET
    /practitioner-roles/booking.
    """

    practitioner_detail: PractitionerDetailResponse | None = None
    location: list[PractitionerRoleBookingLocationResponse] | None = None
    healthcare_service: list[PractitionerRoleBookingHealthcareServiceResponse] | None = None


class PaginatedPractitionerRoleBookingResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: list[PractitionerRoleBookingResponse]

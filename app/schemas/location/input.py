"""
Input schemas for FHIR Location resource endpoints.

Three schemas cover the full API surface:
  - LocationCreateSchema: validated body for POST /locations
  - LocationPatchSchema:  validated body for PATCH /locations/{id}
  - ListLocationsSchema:  validated query parameters for GET /locations

Design decisions:
  - user_id/org_id are required (not injected from the JWT) — matches the
    sibling project's LocationCreateSchema and this project's
    PatientCreateSchema convention. created_by/updated_by are injected by
    FhirClient from actor.sub and are never exposed here.
  - Unlike app/schemas/organization/input.py's `partof` (create-only,
    immutable), `part_of` and `managing_organization` are BOTH exposed on
    LocationPatchSchema — re-parenting a Location is a real, supported
    operation. See app/services/location_service.py for the existence/
    tenant/cycle validation this requires on every change, not just create.
  - Fixed, FHIR-defined small code sets use shared enums rather than plain
    strings, matching app/schemas/organization/input.py's convention:
    IdentifierUse/ContactPointSystem/ContactPointUse/AddressUse/AddressType/
    DayOfWeek from app.schemas.enums (DayOfWeek is shared since
    HealthcareService.availableTime also needs it), LocationStatus/
    LocationMode from app.schemas.location.enums (still Location-only).
    Open/extensible code sets (physical_type_code, operational_status_code,
    sub-resource `type` coding) stay as plain strings, same reasoning as
    OrgTypeInput.coding_code.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    AddressType,
    AddressUse,
    ContactPointSystem,
    ContactPointUse,
    DayOfWeek,
    IdentifierUse,
)
from app.schemas.location.enums import LocationMode, LocationStatus

# ── Sub-resource schemas ───────────────────────────────────────────────────────


class LocationIdentifierInput(BaseModel):
    """A single business identifier for a Location (e.g. a facility code)."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[IdentifierUse] = Field(
        None, description="usual|official|temp|secondary|old"
    )
    type_system: Optional[str] = None
    type_code: Optional[str] = None
    type_display: Optional[str] = None
    type_text: Optional[str] = None
    system: Optional[str] = Field(None, description="URI of the identifier namespace.")
    value: Optional[str] = Field(None, description="Identifier value.")
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    assigner: Optional[str] = Field(
        None, description="Display name of the assigning organization."
    )


class LocationTypeInput(BaseModel):
    """A coded concept categorising the Location (e.g. ward, building, room)."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = Field(
        None,
        description="Coding system URI e.g. 'http://terminology.hl7.org/CodeSystem/v3-RoleCode'.",
    )
    coding_code: Optional[str] = Field(
        None, description="Code value within the coding system."
    )
    coding_display: Optional[str] = Field(
        None, description="Human-readable display for the code."
    )
    text: Optional[str] = Field(
        None, description="Plain-text representation of the type."
    )


class LocationTelecomInput(BaseModel):
    """A contact detail for the Location (phone, email, fax, etc.)."""

    model_config = ConfigDict(extra="forbid")

    system: ContactPointSystem = Field(
        ..., description="phone|fax|email|pager|url|sms|other"
    )
    value: str = Field(
        ..., description="Contact value (phone number, email address, etc.)."
    )
    use: Optional[ContactPointUse] = Field(
        None, description="home|work|temp|old|mobile"
    )
    rank: Optional[int] = Field(
        None, ge=1, description="Preferred contact order (1 = most preferred)."
    )
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class LocationHoursOfOperationInput(BaseModel):
    """Specifies the hours during which the Location is open."""

    model_config = ConfigDict(extra="forbid")

    days_of_week: Optional[List[DayOfWeek]] = Field(
        None, description="Days the location is open."
    )
    all_day: Optional[bool] = Field(
        None, description="True if the location is open all day on the listed days."
    )
    opening_time: Optional[str] = Field(
        None, description="Opening time in HH:mm:ss format."
    )
    closing_time: Optional[str] = Field(
        None, description="Closing time in HH:mm:ss format."
    )


class LocationEndpointInput(BaseModel):
    """A reference to a technical endpoint providing access to services at this Location."""

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(..., description="FHIR reference string e.g. 'Endpoint/1'.")
    reference_display: Optional[str] = None


# ── Create / Patch / List schemas ─────────────────────────────────────────────


class LocationCreateSchema(BaseModel):
    """
    Schema for creating a Location.

    user_id/org_id are required for tenant scoping (the caller supplies them
    explicitly — this middleware does not infer them from the JWT, matching
    the sibling project's LocationCreateSchema and this project's
    PatientCreateSchema).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "u-test",
                "org_id": "org-test",
                "status": "active",
                "name": "Main Building",
                "description": "Primary hospital building",
                "mode": "instance",
                "address_line": ["123 Main St", "Suite 100"],
                "address_city": "Springfield",
                "address_state": "IL",
                "address_postal_code": "62701",
                "address_country": "US",
                "managing_organization": "Organization/190001",
                "position_longitude": -89.6501481,
                "position_latitude": 39.7817213,
            }
        },
    )

    # ── Tenant scoping ─────────────────────────────────────────────────────────
    user_id: str = Field(description="User identifier for tenant scoping.")
    org_id: str = Field(description="Organization identifier for tenant scoping.")

    # ── Status and operational details ─────────────────────────────────────────
    status: Optional[LocationStatus] = Field(
        None, description="active|suspended|inactive"
    )
    operational_status_system: Optional[str] = None
    operational_status_code: Optional[str] = Field(
        None, description="e.g. 'O' for occupied, 'V' for vacant."
    )
    operational_status_display: Optional[str] = None

    # ── Identification ─────────────────────────────────────────────────────────
    name: Optional[str] = Field(
        None, description="Human-readable name of the Location."
    )
    description: Optional[str] = Field(
        None, description="Additional details beyond name."
    )
    mode: Optional[LocationMode] = Field(None, description="instance|kind")

    # ── Array sub-resources ────────────────────────────────────────────────────
    identifiers: Optional[List[LocationIdentifierInput]] = None
    aliases: Optional[List[str]] = Field(
        None, description="Alternate names for this Location."
    )
    types: Optional[List[LocationTypeInput]] = None
    telecoms: Optional[List[LocationTelecomInput]] = None

    # ── Address (flattened scalars, matching Location's fhir-server shape) ─────
    address_use: Optional[AddressUse] = None
    address_type: Optional[AddressType] = None
    address_text: Optional[str] = None
    address_line: Optional[List[str]] = None
    address_city: Optional[str] = None
    address_district: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    address_period_start: Optional[datetime] = None
    address_period_end: Optional[datetime] = None

    # ── Physical type ──────────────────────────────────────────────────────────
    physical_type_system: Optional[str] = None
    physical_type_code: Optional[str] = Field(
        None, description="bu=Building, wi=Wing, wa=Ward, ro=Room, bd=Bed, etc."
    )
    physical_type_display: Optional[str] = None
    physical_type_text: Optional[str] = None

    # ── Relationships ──────────────────────────────────────────────────────────
    managing_organization: Optional[str] = Field(
        None,
        description=(
            "Reference to the managing Organization e.g. 'Organization/190001'. Validated "
            "on create/update — must reference an existing organization in the caller's tenant."
        ),
    )
    managing_organization_display: Optional[str] = None
    part_of: Optional[str] = Field(
        None,
        description=(
            "Reference to the parent Location e.g. 'Location/230001'. Validated on "
            "create/update — must exist, belong to the caller's tenant, and not introduce "
            "a circular hierarchy."
        ),
    )
    part_of_display: Optional[str] = None

    # ── Availability ───────────────────────────────────────────────────────────
    availability_exceptions: Optional[str] = None
    hours_of_operation: Optional[List[LocationHoursOfOperationInput]] = None

    # ── Geographic position ────────────────────────────────────────────────────
    position_longitude: Optional[Decimal] = None
    position_latitude: Optional[Decimal] = None
    position_altitude: Optional[Decimal] = None

    # ── Endpoints ──────────────────────────────────────────────────────────────
    endpoints: Optional[List[LocationEndpointInput]] = None


class LocationPatchSchema(BaseModel):
    """
    Schema for patching a Location. All fields optional — at least one must
    be provided (enforced in LocationService.update()).

    Unlike app/schemas/organization/input.py's PatchOrgSchema, `part_of` and
    `managing_organization` ARE patchable here — re-parenting is supported,
    with existence/tenant/cycle checks applied in LocationService. Array
    sub-resources (identifiers, types, telecoms, hours_of_operation,
    endpoints) are not patchable — delete and re-create to correct those.
    """

    model_config = ConfigDict(extra="forbid")

    status: Optional[LocationStatus] = None
    operational_status_system: Optional[str] = None
    operational_status_code: Optional[str] = None
    operational_status_display: Optional[str] = None

    name: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[LocationMode] = None

    address_use: Optional[AddressUse] = None
    address_type: Optional[AddressType] = None
    address_text: Optional[str] = None
    address_line: Optional[List[str]] = None
    address_city: Optional[str] = None
    address_district: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    address_period_start: Optional[datetime] = None
    address_period_end: Optional[datetime] = None

    physical_type_system: Optional[str] = None
    physical_type_code: Optional[str] = None
    physical_type_display: Optional[str] = None
    physical_type_text: Optional[str] = None

    managing_organization: Optional[str] = None
    managing_organization_display: Optional[str] = None
    part_of: Optional[str] = None
    part_of_display: Optional[str] = None

    availability_exceptions: Optional[str] = None

    position_longitude: Optional[Decimal] = None
    position_latitude: Optional[Decimal] = None
    position_altitude: Optional[Decimal] = None


class ListLocationsSchema(BaseModel):
    """Query parameters for listing locations."""

    model_config = ConfigDict(extra="forbid")

    org_id: Optional[str] = Field(
        None, description="Filter by organization ID (tenant scoping)."
    )
    status: Optional[LocationStatus] = Field(None, description="Filter by status.")
    limit: int = Field(
        20, ge=1, le=200, description="Maximum number of records to return."
    )
    offset: int = Field(
        0, ge=0, description="Number of records to skip for pagination."
    )

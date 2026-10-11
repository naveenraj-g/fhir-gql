"""
Create/Patch/List schemas for the Location resource, mirroring
app/schemas/location/input/core.py in the fhir-server repo field-for-field
(same class names, same fields, same required/optional split) — kept in sync
manually, same convention as app/schemas/organization/input/core.py.

org_id/created_by/updated_by are NOT exposed: fhir-server derives org_id from
the verified JWT's `activeOrganizationId` claim and created_by/updated_by from
its `sub` claim (JWT/RBAC rollout) — a client-supplied value for any of the
three would be rejected outright (extra="forbid", no such field declared).
Unlike every other resource, Location has no user_id field at all — it's a
shared tenant-level entity, not scoped to an individual end-user.

ListLocationsSchema is this gateway's own query-parameter schema
(fhir-server has no GraphQL/query-args concept, so it has no file-level
counterpart to mirror) — mirroring fhir-server's current Medplum-style
Location search parameter set (see app/routers/location/core.py's
list_locations() on fhir-server).
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.enums import AddressType, AddressUse, IdentifierUse
from app.schemas.location.enums import LocationMode, LocationStatus

from .alias import LocationAliasInput
from .endpoint import LocationEndpointInput
from .hours_of_operation import LocationHoursOfOperationInput
from .identifier import LocationIdentifierInput
from .telecom import LocationTelecomInput
from .type import LocationTypeInput


class _PositionMixin(BaseModel):
    """Location.position (0..1 BackboneElement) — the absolute geographic
    location, flattened onto the parent row.

    `longitude` and `latitude` are both 1..1 *within* position, so supplying
    one without the other is not a valid FHIR position. `altitude` stays
    optional (0..1).
    """

    @model_validator(mode="after")
    def _position_requires_lon_and_lat(self):
        has_lon = self.position_longitude is not None
        has_lat = self.position_latitude is not None
        if has_lon != has_lat:
            raise ValueError(
                "position_longitude and position_latitude must be supplied together "
                "— both are 1..1 within Location.position."
            )
        if self.position_altitude is not None and not has_lon:
            raise ValueError(
                "position_altitude requires position_longitude and position_latitude."
            )
        return self


class LocationCreateSchema(_PositionMixin):
    """Creates a Location and any combination of its sub-resources (identifier,
    type, alias, telecom, hoursOfOperation, endpoint) atomically in one
    request — same single-endpoint shape as Organization, since a Location is
    registered once rather than built up incrementally.

    org_id and created_by both come from the verified JWT (actor.org_id /
    actor.sub) — neither is a request body field. Like Organization, Location
    has no user_id at all: a physical place is a shared tenant-level entity,
    not scoped to an individual end-user.

    `address` is 0..1 in FHIR R4 (unlike Organization's 0..*), so it is
    flattened into `address_*` fields rather than a list.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "status": "active",
                "name": "South Wing, second floor",
                "description": "Second floor of the Old South Wing, formerly in use by Psychiatry",
                "mode": "instance",
                "operational_status_system": "http://terminology.hl7.org/CodeSystem/v2-0116",
                "operational_status_code": "U",
                "operational_status_display": "Unoccupied",
                "address_use": "work",
                "address_type": "both",
                "address_line": ["Galapagosweg 91, Building A"],
                "address_city": "Den Burg",
                "address_state": "NH",
                "address_postal_code": "9105 PZ",
                "address_country": "NLD",
                "physical_type_system": "http://terminology.hl7.org/CodeSystem/location-physical-type",
                "physical_type_code": "wi",
                "physical_type_display": "Wing",
                "position_longitude": "-83.6945691",
                "position_latitude": "42.25475478",
                "managing_organization": "Organization/190001",
                "managing_organization_display": "Burgers University Medical Center",
                "part_of": "Location/230001",
                "part_of_display": "Main Building",
                "availability_exceptions": "Reduced services on public holidays",
                "identifier": [
                    {
                        "value": "B1-S.F2",
                        "system": "http://example.org/location-ids",
                        "use": "official",
                    }
                ],
                "type": [
                    {
                        "coding_system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                        "coding_code": "HOSP",
                        "coding_display": "Hospital",
                    }
                ],
                "alias": [{"value": "South Wing OR"}],
                "telecom": [{"system": "phone", "value": "2328", "use": "work"}],
                "hours_of_operation": [
                    {
                        "days_of_week": ["mon", "tue", "wed", "thu", "fri"],
                        "all_day": False,
                        "opening_time": "09:00:00",
                        "closing_time": "17:30:00",
                    }
                ],
                "endpoint": [],
            }
        },
    )

    # ── status / mode ──────────────────────────────────────────────────────

    status: LocationStatus = Field(
        ...,
        description="The status of the location as normally viewed by a user — active|suspended|inactive.",
    )
    mode: LocationMode = Field(
        ...,
        description="Indicates whether this record describes a specific instance of a location, or a class of locations — instance|kind.",
    )

    # ── operationalStatus (0..1 Coding) ────────────────────────────────────
    # Coding, not CodeableConcept — no `text` sibling.

    operational_status_system: str | None = Field(
        None,
        description="Operational status — the code system that defines the meaning of the symbol in the code.",
    )
    operational_status_version: str | None = Field(
        None,
        description="Operational status — the version of the code system used when choosing this code.",
    )
    operational_status_code: str | None = Field(
        None,
        description="Operational status — a symbol in syntax defined by the code system (e.g. 'U' for Unoccupied, 'O' for Occupied).",
    )
    operational_status_display: str | None = Field(
        None,
        description="Operational status — a representation of the meaning of the code in the system.",
    )
    operational_status_user_selected: bool | None = Field(
        None,
        description="Operational status — whether this coding was chosen by a user directly.",
    )

    # ── name / description ─────────────────────────────────────────────────

    name: str = Field(
        ...,
        description="Name of the location as used by humans. Does not need to be unique.",
    )
    description: str | None = Field(
        None,
        description="Description of the Location, which helps in finding or referencing the place.",
    )

    # ── address (0..1 Address, flattened) ──────────────────────────────────

    address_use: AddressUse | None = Field(
        None, description="The purpose of this address — home|work|temp|old|billing."
    )
    address_type: AddressType = Field(
        ...,
        description="Distinguishes between physical addresses and mailing addresses — postal|physical|both.",
    )
    address_text: str | None = Field(
        None, description="A full text representation of the address."
    )
    address_line: list[str] | None = Field(
        None,
        description="Street name, number, direction, PO Box etc. — this repeating element order matters and is preserved.",
    )
    address_city: str = Field(
        ...,
        description="The name of the city, town, suburb, village or other community or delivery center.",
    )
    address_district: str | None = Field(
        None, description="The name of the administrative area (county)."
    )
    address_state: str = Field(
        ...,
        description="Sub-unit of a country with limited sovereignty in a federally organized country.",
    )
    address_postal_code: str = Field(
        ...,
        description="A postal code designating a region defined by the postal service.",
    )
    address_country: str = Field(
        ...,
        description="Country — ISO 3166 3-letter codes can be used in place of a full country name.",
    )
    address_period_start: datetime | None = Field(
        None, description="Start of the time period when this address was/is in use."
    )
    address_period_end: datetime | None = Field(
        None, description="End of the time period when this address was/is in use."
    )

    # ── physicalType (0..1 CodeableConcept) ────────────────────────────────

    physical_type_system: str | None = Field(
        None,
        description="Physical form — the code system that defines the meaning of the symbol in the code.",
    )
    physical_type_version: str | None = Field(
        None,
        description="Physical form — the version of the code system used when choosing this code.",
    )
    physical_type_code: str | None = Field(
        None,
        description="Physical form — a symbol in syntax defined by the code system (e.g. 'wi' for Wing, 'bu' for Building, 'ro' for Room).",
    )
    physical_type_display: str | None = Field(
        None,
        description="Physical form — a representation of the meaning of the code in the system.",
    )
    physical_type_text: str | None = Field(
        None,
        description="Physical form — a human language representation of the concept, as seen/selected/entered by the user.",
    )
    physical_type_user_selected: bool | None = Field(
        None,
        description="Physical form — whether this coding was chosen by a user directly.",
    )

    # ── position (0..1 BackboneElement, flattened) ─────────────────────────

    position_longitude: Decimal | None = Field(
        None,
        description="Longitude with WGS84 datum. Required together with position_latitude.",
    )
    position_latitude: Decimal | None = Field(
        None,
        description="Latitude with WGS84 datum. Required together with position_longitude.",
    )
    position_altitude: Decimal | None = Field(
        None,
        description="Altitude with WGS84 datum. Only meaningful alongside longitude and latitude.",
    )

    # ── managingOrganization (0..1 Reference(Organization)) ────────────────

    managing_organization: str | None = Field(
        None,
        description="The organization responsible for the provisioning and upkeep of the location, as a FHIR reference string (e.g. 'Organization/190001').",
    )
    managing_organization_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the managing organization in addition to the reference.",
    )
    managing_organization_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for managingOrganization (used when it isn't a resource in this system) — identifies the purpose for that identifier, if known.",
    )
    managing_organization_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    managing_organization_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    managing_organization_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    managing_organization_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    managing_organization_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    managing_organization_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    managing_organization_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    managing_organization_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    managing_organization_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    managing_organization_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )

    # ── partOf (0..1 Reference(Location)) ──────────────────────────────────

    part_of: str | None = Field(
        None,
        description="Another Location of which this Location is physically a part of, as a FHIR reference string (e.g. 'Location/230001').",
    )
    part_of_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the containing location in addition to the reference.",
    )
    part_of_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for partOf (used when the containing location isn't a resource in this system) — identifies the purpose for that identifier, if known.",
    )
    part_of_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    part_of_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    part_of_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    part_of_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    part_of_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    part_of_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    part_of_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    part_of_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    part_of_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    part_of_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )

    # ── availabilityExceptions ─────────────────────────────────────────────

    availability_exceptions: str | None = Field(
        None,
        description="A description of when the locations opening ours are different to normal, e.g. public holiday availability.",
    )

    # ── Sub-resource lists ─────────────────────────────────────────────────

    identifier: list[LocationIdentifierInput] | None = Field(
        None, description="Unique code or number identifying the location to its users."
    )
    type: list[LocationTypeInput] | None = Field(
        None, description="Indicates the type of function performed at the location."
    )
    alias: list[LocationAliasInput] | None = Field(
        None,
        description="A list of alternate names that the location is known as, or was known as, in the past.",
    )
    telecom: list[LocationTelecomInput] | None = Field(
        None,
        description="The contact details of communication devices available at the location.",
    )
    hours_of_operation: list[LocationHoursOfOperationInput] | None = Field(
        None,
        description="What days/times during a week is this location usually open.",
    )
    endpoint: list[LocationEndpointInput] | None = Field(
        None,
        description="Technical endpoints providing access to services operated for the location.",
    )


class LocationPatchSchema(_PositionMixin):
    """Partial update — only supplied fields are written. Every supplied
    sub-resource list (even `[]`) replaces the corresponding rows wholesale;
    omitted lists are left untouched. `part_of` may be set to null to clear the
    containment link. updated_by comes from the verified JWT (actor.sub), not a
    request body field.

    Every field is optional here, including the ones that are NOT NULL on the
    model — a PATCH that omits them leaves the stored value in place.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "status": "suspended",
                "name": "South Wing, second floor",
                "description": "Closed for refurbishment until further notice",
                "alias": [{"value": "South Wing OR"}],
                "telecom": [{"system": "phone", "value": "2328", "use": "work"}],
            }
        },
    )

    status: LocationStatus | None = Field(
        None,
        description="The status of the location as normally viewed by a user — active|suspended|inactive.",
    )
    mode: LocationMode | None = Field(
        None,
        description="Indicates whether this record describes a specific instance of a location, or a class of locations — instance|kind.",
    )

    operational_status_system: str | None = Field(
        None, description="Operational status — the code system for the code."
    )
    operational_status_version: str | None = Field(
        None, description="Operational status — the version of the code system."
    )
    operational_status_code: str | None = Field(
        None, description="Operational status — a symbol defined by the code system."
    )
    operational_status_display: str | None = Field(
        None, description="Operational status — the meaning of the code in the system."
    )
    operational_status_user_selected: bool | None = Field(
        None, description="Operational status — whether the coding was user-selected."
    )

    name: str | None = Field(
        None, description="Name of the location as used by humans."
    )
    description: str | None = Field(
        None,
        description="Description of the Location, which helps in finding or referencing the place.",
    )

    address_use: AddressUse | None = Field(
        None, description="The purpose of this address — home|work|temp|old|billing."
    )
    address_type: AddressType | None = Field(
        None,
        description="Distinguishes between physical addresses and mailing addresses — postal|physical|both.",
    )
    address_text: str | None = Field(
        None, description="A full text representation of the address."
    )
    address_line: list[str] | None = Field(
        None, description="Street name, number, direction, PO Box etc."
    )
    address_city: str | None = Field(
        None, description="The name of the city, town, suburb or village."
    )
    address_district: str | None = Field(
        None, description="The name of the administrative area (county)."
    )
    address_state: str | None = Field(
        None, description="Sub-unit of a country with limited sovereignty."
    )
    address_postal_code: str | None = Field(
        None, description="A postal code designating a region."
    )
    address_country: str | None = Field(
        None, description="Country — ISO 3166 3-letter codes may be used."
    )
    address_period_start: datetime | None = Field(
        None, description="Start of the time period when this address was/is in use."
    )
    address_period_end: datetime | None = Field(
        None, description="End of the time period when this address was/is in use."
    )

    physical_type_system: str | None = Field(
        None, description="Physical form — the code system for the code."
    )
    physical_type_version: str | None = Field(
        None, description="Physical form — the version of the code system."
    )
    physical_type_code: str | None = Field(
        None, description="Physical form — a symbol defined by the code system."
    )
    physical_type_display: str | None = Field(
        None, description="Physical form — the meaning of the code in the system."
    )
    physical_type_text: str | None = Field(
        None, description="Physical form — a human language representation."
    )
    physical_type_user_selected: bool | None = Field(
        None, description="Physical form — whether the coding was user-selected."
    )

    position_longitude: Decimal | None = Field(
        None, description="Longitude with WGS84 datum."
    )
    position_latitude: Decimal | None = Field(
        None, description="Latitude with WGS84 datum."
    )
    position_altitude: Decimal | None = Field(
        None, description="Altitude with WGS84 datum."
    )

    managing_organization: str | None = Field(
        None,
        description="The organization responsible for the location, as a FHIR reference string (e.g. 'Organization/190001'). Set to null to clear.",
    )
    managing_organization_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the managing organization.",
    )
    managing_organization_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for managingOrganization — its purpose, if known.",
    )
    managing_organization_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    managing_organization_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    managing_organization_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    managing_organization_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    managing_organization_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    managing_organization_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    managing_organization_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    managing_organization_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    managing_organization_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    managing_organization_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of validity period."
    )

    part_of: str | None = Field(
        None,
        description="Another Location of which this Location is physically a part of, as a FHIR reference string (e.g. 'Location/230001'). Set to null to clear.",
    )
    part_of_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the containing location.",
    )
    part_of_identifier_use: IdentifierUse | None = Field(
        None, description="Logical-identifier fallback for partOf — its purpose."
    )
    part_of_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    part_of_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    part_of_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    part_of_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    part_of_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    part_of_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    part_of_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    part_of_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    part_of_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    part_of_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of validity period."
    )

    availability_exceptions: str | None = Field(
        None,
        description="A description of when the locations opening ours are different to normal.",
    )

    identifier: list[LocationIdentifierInput] | None = Field(
        None,
        description="Unique code(s) identifying the location — replaces the full list if supplied.",
    )
    type: list[LocationTypeInput] | None = Field(
        None,
        description="Function(s) performed at the location — replaces the full list if supplied.",
    )
    alias: list[LocationAliasInput] | None = Field(
        None,
        description="Alternate name(s) for the location — replaces the full list if supplied.",
    )
    telecom: list[LocationTelecomInput] | None = Field(
        None,
        description="Contact detail(s) for the location — replaces the full list if supplied.",
    )
    hours_of_operation: list[LocationHoursOfOperationInput] | None = Field(
        None,
        description="Opening hours for the location — replaces the full list if supplied.",
    )
    endpoint: list[LocationEndpointInput] | None = Field(
        None,
        description="Technical endpoint(s) for the location — replaces the full list if supplied.",
    )


# ── Query-parameter schema (this gateway's own concept — no fhir-server equivalent) ──


class ListLocationsSchema(BaseModel):
    """Query parameters for listing locations — mirrors fhir-server's
    Medplum-mirrored Location search parameter set.

    org_id is deliberately NOT a filter here: fhir-server always scopes
    Location reads to the caller's own org via the verified JWT (JWT/RBAC
    rollout) — matches Organization's ListOrganizationsSchema.
    """

    name: str | None = Field(
        None, description="Partial match against the location name or any alias."
    )
    identifier: str | None = Field(
        None, description="Exact match on a business identifier value."
    )
    location_status: LocationStatus | None = Field(
        None, description="active|suspended|inactive."
    )
    operational_status: str | None = Field(
        None,
        description="Exact match on the operational status code (e.g. 'U' for Unoccupied).",
    )
    location_type: str | None = Field(
        None,
        description="Exact match on a coded function performed at the location (e.g. 'HOSP').",
    )
    physical_type: str | None = Field(
        None,
        description="Exact match on the physical form code (e.g. 'wi' for Wing, 'ro' for Room).",
    )
    address: str | None = Field(
        None,
        description="Partial match against any Address sub-field (line, city, district, state, country, postalCode, text).",
    )
    address_city: str | None = Field(
        None, description="Filter by address city — partial match."
    )
    address_state: str | None = Field(
        None, description="Filter by address state — partial match."
    )
    address_postal_code: str | None = Field(
        None, description="Filter by address postal code — exact match."
    )
    address_country: str | None = Field(
        None, description="Filter by address country — partial match."
    )
    address_use: AddressUse | None = Field(
        None, description="home|work|temp|old|billing."
    )
    organization: str | None = Field(
        None,
        description="Managing organization, as a FHIR reference string, e.g. 'Organization/190001'.",
    )
    partof: str | None = Field(
        None,
        description="Containing location, as a FHIR reference string, e.g. 'Location/230001'.",
    )
    endpoint: str | None = Field(
        None, description="FHIR reference string, e.g. 'Endpoint/1'."
    )
    near: str | None = Field(
        None,
        description=(
            "Radius search against Location.position, as "
            "'[latitude]|[longitude]|[distance]|[units]' — e.g. "
            "'42.25475478|-83.6945691|11.20|km'. Units default to km; km, m and mi are "
            "accepted. Locations with no recorded position never match."
        ),
    )
    sort: str | None = Field(None, description="Sort key, e.g. '-name'.")
    total_mode: Literal["accurate", "none"] = Field(
        "accurate", description="accurate|none — skip the COUNT(*) with 'none'."
    )
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)

"""
Pydantic models representing the genuine FHIR R4 Location resource shape —
the canonical shape shared by every connector and by the GraphQL boundary
itself. Mirrors app.fhir.schemas.organization's pattern exactly — see that
module's docstring for the overall rationale.

Lives at the app level (app.fhir), not under any one connector, for the
same reason Organization's canonical shape does: app.connectors.internal.translators.location
and app.connectors.medplum.translators.location both translate their
connector's own wire format to/from this same shape (see
app.connectors.base.LocationWireTranslator), and app.gql.location's
types/queries/mutations import these models directly.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Address, ContactPoint, Identifier, Reference) is imported from
app.fhir.schemas.datatypes rather than redefined here. `FhirLocationPosition`
and `FhirLocationHoursOfOperation` stay local — same reasoning as
Organization's FhirOrgContact: both are Location's own anonymous
BackboneElements (the R4 spec defines them specifically for this resource),
not general-purpose datatypes reused elsewhere.

Unlike Organization, Location.address is 0..1 (not 0..*) and Location has
no top-level `active` field at all — see FhirLocationResponse below.

`FhirLocationInput` is the write-side counterpart, used by both
createFhirLocation/updateFhirLocation (see app.gql.location.mutations) —
same one-shape-for-both-create-and-update reasoning as
FhirOrganizationInput, since Location has no required-at-this-layer fields
either (its two required fields, status and mode, are optional at this
canonical layer because a PATCH-style update must be able to omit them).

FHIR R4 Location resource spec: https://hl7.org/fhir/R4/location.html
"""

from decimal import Decimal

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirAddress,
    FhirCodeableConcept,
    FhirCoding,
    FhirContactPoint,
    FhirIdentifier,
    FhirMeta,
    FhirReference,
)


class FhirLocationPosition(BaseModel):
    """Location.position — the absolute geographic location (BackboneElement).
    longitude/latitude are 1..1 *within* position in the spec, but both stay
    optional here since position itself is 0..1 at the resource level."""

    longitude: Decimal | None = Field(
        default=None, description="Longitude with WGS84 datum"
    )
    latitude: Decimal | None = Field(
        default=None, description="Latitude with WGS84 datum"
    )
    altitude: Decimal | None = Field(
        default=None, description="Altitude with WGS84 datum"
    )


class FhirLocationHoursOfOperation(BaseModel):
    """Location.hoursOfOperation — what days/times during a week the
    location is generally open (BackboneElement)."""

    daysOfWeek: list[str] | None = Field(
        default=None,
        description="Indicates which days of the week are available between the start and end times — mon|tue|wed|thu|fri|sat|sun.",
    )
    allDay: bool | None = Field(
        default=None, description="The Location is open all day (24 hours)."
    )
    openingTime: str | None = Field(
        default=None, description="Time that the Location opens."
    )
    closingTime: str | None = Field(
        default=None, description="Time that the Location closes."
    )


class FhirLocationResponse(BaseModel):
    resourceType: str = Field(
        default="Location",
        description="Always 'Location' — identifies the FHIR resource type",
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
            "FhirLocationInput, since this is server-derived audit/tenant "
            "data, not something a client writes."
        ),
    )
    extension: list[dict] | None = Field(
        default=None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
    identifier: list[FhirIdentifier] | None = Field(
        default=None,
        description="Unique code or number identifying the location to its users",
    )
    status: str | None = Field(
        default=None,
        description="The status of the location as normally viewed by a user — active|suspended|inactive",
    )
    operationalStatus: FhirCoding | None = Field(
        default=None,
        description="The operational status of the location (typically only for a bed/room)",
    )
    name: str | None = Field(
        default=None, description="Name of the location as used by humans"
    )
    alias: list[str] | None = Field(
        default=None,
        description="A list of alternate names that the location is known as, or was known as, in the past",
    )
    description: str | None = Field(
        default=None,
        description="Additional details about the location that could be displayed as further information to identify the location beyond its name",
    )
    mode: str | None = Field(
        default=None,
        description="Indicates whether a resource instance represents a specific location or a class of locations — instance|kind",
    )
    type: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="Indicates the type of function performed at the location",
    )
    telecom: list[FhirContactPoint] | None = Field(
        default=None,
        description="The contact details of communication devices available at the location",
    )
    address: FhirAddress | None = Field(
        default=None,
        description="Physical location. Singular (0..1) in FHIR R4 — unlike Organization.address, which repeats.",
    )
    physicalType: FhirCodeableConcept | None = Field(
        default=None,
        description="Physical form of the location, e.g. building, room, vehicle",
    )
    position: FhirLocationPosition | None = Field(
        default=None,
        description="The absolute geographic location of the Location, expressed using the WGS84 datum",
    )
    managingOrganization: FhirReference | None = Field(
        default=None,
        description="The organization responsible for the provisioning and upkeep of the location",
    )
    partOf: FhirReference | None = Field(
        default=None,
        description="Another Location of which this Location is physically a part of",
    )
    hoursOfOperation: list[FhirLocationHoursOfOperation] | None = Field(
        default=None,
        description="What days/times during a week is this location usually open",
    )
    availabilityExceptions: str | None = Field(
        default=None,
        description="A description of when the locations opening hours are different to normal",
    )
    endpoint: list[FhirReference] | None = Field(
        default=None,
        description="Technical endpoints providing access to services operated for the location",
    )


class FhirLocationBundleEntry(BaseModel):
    resource: FhirLocationResponse = Field(
        description="The FHIR Location resource contained in this entry"
    )


class FhirLocationBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirLocationBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one Location resource"
    )


class FhirLocationInput(BaseModel):
    """
    The write-side counterpart to FhirLocationResponse — same genuine FHIR
    R4 Location shape, minus `resourceType`/`id`/`meta` (the id is a
    separate `id: str` mutation argument on update; create doesn't take one
    at all). Used as-is for BOTH create and update — see module docstring.

    Any field a connector's translator can't reach on write (e.g. a
    Reference's logical-identifier fallback — fhir-server's
    managing_organization_identifier_*/part_of_identifier_*/
    reference_identifier_* — since FhirReference doesn't carry one) is
    simply left unset by that translator, same gap as Organization's.
    """

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    status: str | None = Field(default=None)
    operationalStatus: FhirCoding | None = Field(default=None)
    name: str | None = Field(default=None)
    alias: list[str] | None = Field(default=None)
    description: str | None = Field(default=None)
    mode: str | None = Field(default=None)
    type: list[FhirCodeableConcept] | None = Field(default=None)
    telecom: list[FhirContactPoint] | None = Field(default=None)
    address: FhirAddress | None = Field(default=None)
    physicalType: FhirCodeableConcept | None = Field(default=None)
    position: FhirLocationPosition | None = Field(default=None)
    managingOrganization: FhirReference | None = Field(default=None)
    partOf: FhirReference | None = Field(default=None)
    hoursOfOperation: list[FhirLocationHoursOfOperation] | None = Field(default=None)
    availabilityExceptions: str | None = Field(default=None)
    endpoint: list[FhirReference] | None = Field(default=None)

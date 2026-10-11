"""Organization.contact — mirrors fhir-server's
app/schemas/organization/input/contact.py field-for-field."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    AddressType,
    AddressUse,
    ContactPointSystem,
    ContactPointUse,
    HumanNameUse,
)

from ._shared import OrganizationCodingInput


class OrganizationContactTelecomInput(BaseModel):
    """Organization.contact.telecom — a contact detail for the contact person (ContactPoint)."""

    model_config = ConfigDict(extra="forbid")
    # system/value are 0..1 on ContactPoint — not required even here.
    system: ContactPointSystem | None = Field(
        None,
        description="Telecommunications form for the contact point — what communications system is required to make use of it: phone|fax|email|pager|url|sms|other.",
    )
    value: str | None = Field(
        None,
        description="The actual contact point details, in a form meaningful to the designated communication system.",
    )
    use: ContactPointUse | None = Field(
        None,
        description="Identifies the purpose for the contact point — home|work|temp|old|mobile.",
    )
    rank: int | None = Field(
        None,
        ge=1,
        description="Specifies a preferred order in which to use a set of contacts. Lower values are more preferred than higher values.",
    )
    period_start: datetime | None = Field(
        None,
        description="Start of the time period when this contact point was/is in use.",
    )
    period_end: datetime | None = Field(
        None,
        description="End of the time period when this contact point was/is in use.",
    )


class OrganizationContactInput(BaseModel):
    """Organization.contact — contact for the organization for a certain purpose (BackboneElement)."""

    model_config = ConfigDict(extra="forbid")
    # purpose (0..1 CodeableConcept) — "Indicates a purpose for which the
    # contact can be reached." purpose_text is the CodeableConcept's own
    # field; purpose_coding is the real 0..* coding list — see
    # OrganizationCodingInput's docstring.
    purpose_coding: list[OrganizationCodingInput] | None = Field(
        None,
        description="Coding(s) for this contact's purpose — e.g. 'ADMIN', 'BILL', 'PRESS'.",
    )
    purpose_text: str | None = Field(
        None, description="A human language representation of the contact's purpose."
    )
    # name (0..1 HumanName) — "A name associated with the contact."
    name_use: HumanNameUse | None = Field(
        None, description="Identifies the purpose for this name."
    )
    name_text: str | None = Field(
        None,
        description="Specifies the entire name as it should be displayed, e.g. on an application UI.",
    )
    name_family: str | None = Field(
        None, description="The part of the name that links to the genealogy."
    )
    name_given: list[str] | None = Field(None, description="Given name(s).")
    name_prefix: list[str] | None = Field(
        None,
        description="Part(s) of the name acquired as a title due to academic, legal, employment or nobility status, etc., appearing at the start of the name.",
    )
    name_suffix: list[str] | None = Field(
        None,
        description="Part(s) of the name acquired as a title due to academic, legal, employment or nobility status, etc., appearing at the end of the name.",
    )
    name_period_start: datetime | None = Field(
        None,
        description="Start of the period during which this name was valid for the contact.",
    )
    name_period_end: datetime | None = Field(
        None,
        description="End of the period during which this name was valid for the contact.",
    )
    # address (0..1 Address) — "Visiting or postal addresses for the
    # contact." type/city/state/postal_code/country are all 0..1 on
    # Address — none of them required even here.
    address_use: AddressUse | None = Field(
        None, description="The purpose of this address — home|work|temp|old|billing."
    )
    address_type: AddressType | None = Field(
        None,
        description="Distinguishes between physical addresses (those you can visit) and mailing addresses — postal|physical|both.",
    )
    address_text: str | None = Field(
        None,
        description="Specifies the entire address as it should be displayed, e.g. on a postal label.",
    )
    address_line: list[str] | None = Field(
        None,
        description="The house number, apartment number, street name, and similar information.",
    )
    address_city: str | None = Field(
        None,
        description="The name of the city, town, suburb, village or other community or delivery center.",
    )
    address_district: str | None = Field(
        None, description="The name of the administrative area (county)."
    )
    address_state: str | None = Field(
        None,
        description="Sub-unit of a country with limited sovereignty in a federally organized country.",
    )
    address_postal_code: str | None = Field(
        None,
        description="A postal code designating a region defined by the postal service.",
    )
    address_country: str | None = Field(
        None,
        description="Country — a nation as commonly understood or generally accepted.",
    )
    address_period_start: datetime | None = Field(
        None, description="Start of the time period when this address was/is in use."
    )
    address_period_end: datetime | None = Field(
        None, description="End of the time period when this address was/is in use."
    )
    # telecom (0..*)
    telecom: list[OrganizationContactTelecomInput] | None = Field(
        None,
        description="A contact detail (e.g. a telephone number or an email address) by which the contact person may be reached.",
    )

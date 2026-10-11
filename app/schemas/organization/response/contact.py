from pydantic import Field

from ._shared import _AuditFields


class OrganizationContactTelecomResponse(_AuditFields):
    id: int = Field(..., description="Internal row ID — use for sub-resource lookups.")
    system: str | None = Field(
        None,
        description="Telecommunications form for the contact point (phone|fax|email|pager|url|sms|other).",
    )
    value: str | None = Field(None, description="The actual contact point details.")
    use: str | None = Field(
        None, description="Identifies the purpose for the contact point."
    )
    rank: int | None = Field(
        None,
        description="Preferred order among a set of contacts — lower values are more preferred.",
    )
    period_start: str | None = Field(
        None,
        description="Start of the time period when this contact point was/is in use.",
    )
    period_end: str | None = Field(
        None,
        description="End of the time period when this contact point was/is in use.",
    )


class OrganizationContactResponse(_AuditFields):
    id: int = Field(..., description="Internal row ID — use for sub-resource lookups.")
    purpose_system: str | None = Field(
        None,
        description="The code system that defines the meaning of the contact's purpose code.",
    )
    purpose_code: str | None = Field(
        None,
        description="A symbol in syntax defined by the code system (e.g. 'ADMIN', 'BILL', 'PRESS').",
    )
    purpose_display: str | None = Field(
        None, description="A representation of the meaning of the purpose code."
    )
    purpose_text: str | None = Field(
        None, description="A human language representation of the contact's purpose."
    )
    name_use: str | None = Field(
        None, description="Identifies the purpose for this name."
    )
    name_text: str | None = Field(
        None, description="The entire name as it should be displayed."
    )
    name_family: str | None = Field(
        None, description="The part of the name that links to the genealogy."
    )
    name_given: list[str] | None = Field(None, description="Given name(s).")
    name_prefix: list[str] | None = Field(
        None,
        description="Name prefix(es) (e.g. titles) appearing at the start of the name.",
    )
    name_suffix: list[str] | None = Field(
        None, description="Name suffix(es) appearing at the end of the name."
    )
    name_period_start: str | None = Field(
        None,
        description="Start of the period during which this name was valid for the contact.",
    )
    name_period_end: str | None = Field(
        None,
        description="End of the period during which this name was valid for the contact.",
    )
    address_use: str | None = Field(None, description="The purpose of this address.")
    address_type: str | None = Field(
        None, description="Distinguishes between physical and mailing addresses."
    )
    address_text: str | None = Field(
        None, description="The entire address as it should be displayed."
    )
    address_line: list[str] | None = Field(
        None,
        description="House number, apartment number, street name, and similar information.",
    )
    address_city: str | None = Field(
        None,
        description="The name of the city, town, suburb, village or other community.",
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
    address_period_start: str | None = Field(
        None, description="Start of the time period when this address was/is in use."
    )
    address_period_end: str | None = Field(
        None, description="End of the time period when this address was/is in use."
    )
    telecoms: list[OrganizationContactTelecomResponse] | None = Field(
        None,
        description="Contact detail(s) (e.g. a telephone number or an email address) by which the contact person may be reached.",
    )

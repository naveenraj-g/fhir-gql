from pydantic import Field

from ._shared import _AuditFields


class OrganizationAddressResponse(_AuditFields):
    id: int = Field(..., description="Internal row ID — use for sub-resource lookups.")
    use: str | None = Field(None, description="The purpose of this address.")
    type: str | None = Field(
        None, description="Distinguishes between physical and mailing addresses."
    )
    text: str | None = Field(
        None,
        description="The entire address as it should be displayed, e.g. on a postal label.",
    )
    line: list[str] | None = Field(
        None,
        description="House number, apartment number, street name, and similar information.",
    )
    city: str | None = Field(
        None,
        description="The name of the city, town, suburb, village or other community.",
    )
    district: str | None = Field(
        None, description="The name of the administrative area (county)."
    )
    state: str | None = Field(
        None,
        description="Sub-unit of a country with limited sovereignty in a federally organized country.",
    )
    postal_code: str | None = Field(
        None,
        description="A postal code designating a region defined by the postal service.",
    )
    country: str | None = Field(
        None,
        description="Country — a nation as commonly understood or generally accepted.",
    )
    period_start: str | None = Field(
        None, description="Start of the time period when this address was/is in use."
    )
    period_end: str | None = Field(
        None, description="End of the time period when this address was/is in use."
    )

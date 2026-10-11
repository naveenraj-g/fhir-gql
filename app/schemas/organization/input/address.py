"""Organization.address — mirrors fhir-server's
app/schemas/organization/input/address.py field-for-field."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import AddressType, AddressUse


class OrganizationAddressInput(BaseModel):
    """Organization.address — an address for the organization (Address)."""

    model_config = ConfigDict(extra="forbid")
    use: AddressUse | None = Field(
        None, description="The purpose of this address — home|work|temp|old|billing."
    )
    # type/city/state/postal_code/country are all 0..1 on Address — none of
    # them required even here.
    type: AddressType | None = Field(
        None,
        description="Distinguishes between physical addresses (those you can visit) and mailing addresses (e.g. PO Boxes and care-of addresses) — postal|physical|both.",
    )
    text: str | None = Field(
        None,
        description="Specifies the entire address as it should be displayed, e.g. on a postal label.",
    )
    line: list[str] | None = Field(
        None,
        description="The house number, apartment number, street name, street direction, P.O. Box number, delivery hints, and similar information.",
    )
    city: str | None = Field(
        None,
        description="The name of the city, town, suburb, village or other community or delivery center.",
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
    period_start: datetime | None = Field(
        None, description="Start of the time period when this address was/is in use."
    )
    period_end: datetime | None = Field(
        None, description="End of the time period when this address was/is in use."
    )

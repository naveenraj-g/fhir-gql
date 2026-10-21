"""
FHIR R4 Address datatype — a postal address for an entity.

Spec: https://hl7.org/fhir/R4/datatypes.html#Address
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes.period import FhirPeriod


class FhirAddress(BaseModel):
    use: str | None = Field(
        default=None, description="home | work | temp | old | billing"
    )
    type: str | None = Field(default=None, description="postal | physical | both")
    text: str | None = Field(
        default=None, description="Text representation of the address"
    )
    line: list[str] | None = Field(
        default=None, description="Street name, number, direction, PO Box"
    )
    city: str | None = Field(
        default=None, description="Name of city, town, suburb, village"
    )
    district: str | None = Field(
        default=None, description="District name (county, parish, etc.)"
    )
    state: str | None = Field(
        default=None, description="Sub-unit of country (abbreviation)"
    )
    postalCode: str | None = Field(default=None, description="Postal code for area")
    country: str | None = Field(
        default=None, description="Country (ISO 3166 code preferred)"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Time period when address was/is in use"
    )

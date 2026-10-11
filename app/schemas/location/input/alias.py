"""Location.alias — mirrors fhir-server's
app/schemas/location/input/alias.py field-for-field."""

from pydantic import BaseModel, ConfigDict, Field


class LocationAliasInput(BaseModel):
    """Location.alias — an alternate name the location is or was known as."""

    model_config = ConfigDict(extra="forbid")
    value: str = Field(
        ...,
        description="A list of alternate names that the location is known as, or was known as, in the past.",
    )

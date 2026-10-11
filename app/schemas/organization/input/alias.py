"""Organization.alias — mirrors fhir-server's
app/schemas/organization/input/alias.py field-for-field."""

from pydantic import BaseModel, ConfigDict, Field


class OrganizationAliasInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(
        ...,
        description="An alternate name that the organization is known as, or was known as in the past.",
    )

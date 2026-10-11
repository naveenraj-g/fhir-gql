from pydantic import Field

from ._shared import _AuditFields


class HealthcareServiceTypeResponse(_AuditFields):
    id: int = Field(..., description="Internal row ID — use for sub-resource lookups.")
    coding_system: str | None = Field(
        None, description="The code system that defines the meaning of this code."
    )
    coding_version: str | None = Field(
        None, description="The version of the code system used."
    )
    coding_code: str | None = Field(
        None, description="A symbol in syntax defined by the code system."
    )
    coding_display: str | None = Field(
        None, description="A representation of the meaning of the code."
    )
    text: str | None = Field(
        None, description="A human language representation of the type."
    )
    coding_user_selected: bool | None = Field(
        None, description="Whether this coding was chosen by a user directly."
    )

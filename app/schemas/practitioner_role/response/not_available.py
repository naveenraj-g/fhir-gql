from pydantic import Field

from ._shared import _AuditFields


class PractitionerRoleNotAvailableResponse(_AuditFields):
    id: int = Field(..., description="Internal row ID — use for sub-resource lookups.")
    description: str | None = Field(
        None,
        description="The reason presented to the user as to why this time is not available.",
    )
    during_start: str | None = Field(
        None,
        description="Start of the period of time that this role is not available.",
    )
    during_end: str | None = Field(
        None,
        description="End of the period of time that this role is not available.",
    )

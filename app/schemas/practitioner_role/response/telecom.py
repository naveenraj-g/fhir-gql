from pydantic import Field

from ._shared import _AuditFields


class PractitionerRoleTelecomResponse(_AuditFields):
    id: int = Field(..., description="Internal row ID — use for sub-resource lookups.")
    system: str | None = Field(
        None, description="Telecommunications form for this contact point."
    )
    value: str | None = Field(None, description="The actual contact point details.")
    use: str | None = Field(
        None, description="Identifies the purpose for the contact point."
    )
    rank: int | None = Field(
        None, description="Preferred order of use among a set of contacts."
    )
    period_start: str | None = Field(
        None,
        description="Start of the time period when this contact point was/is in use.",
    )
    period_end: str | None = Field(
        None,
        description="End of the time period when this contact point was/is in use.",
    )

"""
FHIR client for Slot resources.

Thin wrapper around the shared FhirClient that knows the fhir-server path
for the Slot resource. No business logic lives here — all validation and
availability-aware generation belongs in SlotService. Same shape as
app/fhir_client/schedule.py.

Reference: https://hl7.org/fhir/R4/slot.html
"""

from app.auth.models import AuthUser
from app.fhir_client.client import FhirClient
from app.core.logging import trace_methods

_PATH = "/slots"


@trace_methods
class SlotClient:
    """
    Domain-specific HTTP client for Slot resources.

    Delegates every request to the shared FhirClient singleton, which
    handles authentication headers, base-URL resolution, and error
    propagation.
    """

    def __init__(self, fhir: FhirClient) -> None:
        """
        Args:
            fhir: The singleton FhirClient — owns the httpx session and base URL config.
        """
        self._fhir = fhir

    async def create(self, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /slots — create a new Slot resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept)

    async def get_by_id(self, slot_id: int, accept: str | None = None) -> dict:
        """GET /slots/{slot_id} — fetch a single Slot by integer ID."""
        return await self._fhir.get(f"{_PATH}/{slot_id}", accept=accept)

    async def list(self, accept: str | None = None, **params) -> dict:
        """
        GET /slots — list Slots with optional filters.

        Strips None values from **params — an omitted param means "no
        filter", not a literal `?key=None` sent to the fhir-server.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept)

    async def patch(self, slot_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /slots/{slot_id} — partially update a Slot."""
        return await self._fhir.patch(f"{_PATH}/{slot_id}", data, actor, accept=accept)

    async def delete(self, slot_id: int) -> None:
        """DELETE /slots/{slot_id} — permanently remove a Slot."""
        await self._fhir.delete(f"{_PATH}/{slot_id}")
